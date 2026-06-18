"""Simulador de verificação de restrições da UHR.

Dado um resultado da otimização (vetor de decisão ou ``StationState``),
verifica **uma a uma** todas as restrições do modelo ``otimiz global`` e
informa se foram atendidas (aprovado/reprovado), com o valor calculado,
o limite e a folga (margem).

Reproduz as restrições da aba ``otimiz global`` (F22:I37) e as verificações
de pressão por segmento e de cavitação (AP5:AR5).
"""

from __future__ import annotations

from dataclasses import dataclass

from .global_optimization import GlobalOptimization, StationState
from .segments import PipeMaterial, SegmentPosition


@dataclass(frozen=True)
class ConstraintCheck:
	"""Resultado da verificação de uma restrição."""

	name: str
	value: float
	operator: str       # "<=", ">=", "entre"
	limit: float
	satisfied: bool
	slack: float        # margem (positiva = folga, negativa = violação)
	unit: str = ""

	def __str__(self) -> str:
		status = "OK    " if self.satisfied else "FALHOU"
		unit = f" {self.unit}" if self.unit else ""
		return (f"[{status}] {self.name:<42} "
				f"valor={self.value:12.4f}{unit}  "
				f"{self.operator} {self.limit:.4f}  "
				f"(folga={self.slack:+.4f})")


@dataclass
class SimulationReport:
	"""Relatório completo do simulador."""

	checks: list[ConstraintCheck]
	state: StationState

	@property
	def all_satisfied(self) -> bool:
		return all(c.satisfied for c in self.checks)

	@property
	def n_violations(self) -> int:
		return sum(1 for c in self.checks if not c.satisfied)

	def violations(self) -> list[ConstraintCheck]:
		return [c for c in self.checks if not c.satisfied]

	def __str__(self) -> str:
		lines = [str(c) for c in self.checks]
		summary = ("TODAS AS RESTRIÇÕES ATENDIDAS"
				   if self.all_satisfied
				   else f"{self.n_violations} RESTRIÇÃO(ÕES) VIOLADA(S)")
		lines.append("-" * 64)
		lines.append(summary)
		return "\n".join(lines)


class ConstraintSimulator:
	"""Verifica se um resultado atende a todas as restrições do modelo."""

	def __init__(self, model: GlobalOptimization | None = None,
				 tolerance: float = 1e-6) -> None:
		self.model = model or GlobalOptimization()
		self.tolerance = tolerance

	# ------------------------------------------------------------------
	def simulate(self, result_or_state) -> SimulationReport:
		"""Verifica todas as restrições para um resultado/estado/vetor."""
		st = self._coerce_state(result_or_state)
		m = self.model
		ms = m.material_strength
		checks: list[ConstraintCheck] = []

		def add_max(name, value, limit, unit=""):
			slack = limit - value
			checks.append(ConstraintCheck(
				name, value, "<=", limit,
				satisfied=slack >= -self.tolerance, slack=slack, unit=unit))

		def add_min(name, value, limit, unit=""):
			slack = value - limit
			checks.append(ConstraintCheck(
				name, value, ">=", limit,
				satisfied=slack >= -self.tolerance, slack=slack, unit=unit))

		def add_between(name, value, low, high, unit=""):
			slack = min(value - low, high - value)
			checks.append(ConstraintCheck(
				name, value, "entre", high,
				satisfied=slack >= -self.tolerance, slack=slack, unit=unit))

		# --- Velocidades máximas e mínimas por tubo ---
		for ss in st.pipe_states():
			mat_label = ss.material
			if ss.material == PipeMaterial.ACO.value:
				v_max = m.V_MAX_STEEL
				mat_tag = "aço"
			else:
				v_max = m.V_MAX_CONCRETE
				mat_tag = "concreto"
			add_max(f"Velocidade máx {ss.name} ({mat_tag})",
					ss.velocity, v_max, "m/s")
			add_min(f"Velocidade mín {ss.name}",
					ss.velocity, m.V_MIN, "m/s")

		# --- Perda de carga máxima (I36) ---
		head_loss_frac = (st.head_loss_total / st.head_gross_turb
						  if st.head_gross_turb > 0 else float("inf"))
		add_max("Perda de carga relativa", head_loss_frac,
				m.HEAD_LOSS_MAX_FRAC, "frac")

		# --- Pressão nos materiais por tubo ---
		for ss in st.pipe_states():
			if ss.material == PipeMaterial.ACO.value:
				strength = ms.steel_strength_kgf_m2
				mat_tag = "aço"
			else:
				strength = ms.concrete_strength_kgf_m2
				mat_tag = "concreto"
			add_max(f"Pressão {ss.name} ({mat_tag})",
					ss.pressure, strength, "Kgf/m²")

		# --- Cavitação / NPSH (I37 / AR5) ---
		add_min("Relação NPSH disp/req", st.npsh_ratio,
				m.NPSH_SAFETY_FACTOR, "")

		# --- Relação Pturb/Pbomb (I27/I28) ---
		add_between("Relação Pturb/Pbomb", st.power_ratio,
					m.RATIO_MIN, m.RATIO_MAX, "")

		# --- Alturas das barragens (I23/I24/I25) ---
		add_max("Altura máx barragem superior", st.h1,
				m.DAM_HEIGHT_MAX, "m")
		add_max("Altura máx barragem inferior", st.h2,
				m.DAM_HEIGHT_MAX, "m")
		add_min("Altura mín barragem superior", st.h1,
				m.H_MED_SUP + st.delta_sup, "m")
		add_min("Altura mín barragem inferior", st.h2,
				m.H_MED_INF + st.delta_inf, "m")

		# --- Potência mínima por máquina (I26) ---
		add_min("Potência mín turbina/máquina", st.power_turbine,
				m.POWER_MIN_PER_MACHINE, "MW")

		# --- Horas mínimas de turbinamento (I29) ---
		add_min("Horas mín turbinamento/dia", st.hours_turb,
				m.HOURS_TURB_MIN, "h")

		return SimulationReport(checks=checks, state=st)

	# ------------------------------------------------------------------
	def _coerce_state(self, obj) -> StationState:
		"""Converte resultado/estado/vetor em ``StationState``."""
		if isinstance(obj, StationState):
			return obj
		# OptimizationResult tem atributo ``state``.
		state = getattr(obj, "state", None)
		if isinstance(state, StationState):
			return state
		# Caso contrário, assume vetor de decisão x.
		return self.model.evaluate(obj)
