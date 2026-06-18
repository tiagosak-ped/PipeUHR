"""Aba ``otimiz global`` — modelo hidráulico e otimização do custo da UHR.

Esta é a classe central que reproduz a aba ``otimiz global`` da planilha,
incluindo:

- Geometria e velocidade nos trechos da tubulação (dinâmico, N segmentos).
- Cálculo da perda de carga (Swamee-Jain) por segmento do circuito.
- Cotas dos reservatórios superior e inferior e alturas bruta/líquida.
- Ciclo diário (horas de turbinamento/bombeamento) e vazões.
- Potências de turbinamento e bombeamento.
- Verificação de cavitação (NPSH disponível × requerido).
- Funções de custo (C1..C5) e custo total CT.
- O problema de otimização (Solver -> ``scipy.optimize.minimize`` SLSQP):
  minimizar CT sujeito às restrições de velocidade, perda de carga, pressão
  nos materiais, cavitação, relação Pturb/Pbomb, alturas e potência mínima.

Variáveis de decisão (vetor ``x``):
		[h1, h2, D_pipe_0, D_pipe_1, …, D_pipe_(n-1), hours_pump]
onde ``h1``/``h2`` são as alturas das barragens superior/inferior (m),
``D_pipe_*`` os diâmetros das tubulações (m) e ``hours_pump`` as horas de
bombeamento por dia.  O número de diâmetros é igual ao número de
``PipeSegment`` no ``HydraulicCircuit``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

from .aux_data import AuxData
from .dam_cost import DamCostModel
from .equipment_cost import EquipmentCostModel
from .material_strength import MaterialStrength
from .segments import (
	HydraulicCircuit,
	PipeMaterial,
	PipeType,
	SegmentPosition,
	SegmentState,
)


@dataclass
class StationState:
	"""Estado completo da UHR para um dado vetor de decisão."""

	# Variáveis de decisão
	h1: float
	h2: float
	pipe_diameters: list[float] = field(default_factory=list)
	hours_pump: float = 0.0

	# Resultados por segmento
	segment_states: list[SegmentState] = field(default_factory=list)

	# Perda de carga
	head_loss_recalque: float = 0.0
	head_loss_suction: float = 0.0
	head_loss_total: float = 0.0

	# Cotas e alturas
	cota_max_sup: float = 0.0
	cota_min_sup: float = 0.0
	cota_tomada: float = 0.0
	cota_max_inf: float = 0.0
	cota_min_inf: float = 0.0
	cota_e: float = 0.0
	head_gross_turb: float = 0.0  # HBt
	head_gross_pump: float = 0.0  # HBb
	head_net_turb: float = 0.0  # HLt
	head_net_pump: float = 0.0  # HLb

	# Ciclo diário e vazões
	hours_turb: float = 0.0
	vol_turbined: float = 0.0
	flow_pump: float = 0.0
	delta_sup: float = 0.0
	delta_inf: float = 0.0

	# Potências
	power_turbine: float = 0.0  # MW por máquina
	power_pump: float = 0.0  # MW por máquina
	power_ratio: float = 0.0  # Pturb/Pbomb

	# Cavitação
	npsh_available: float = 0.0
	npsh_required: float = 0.0
	npsh_ratio: float = 0.0

	# Custos (milhões R$)
	cost_dam_sup: float = 0.0  # C1
	cost_dam_inf: float = 0.0  # C2
	cost_powerhouse: float = 0.0  # C3
	cost_low_pressure: float = 0.0  # C4
	cost_high_pressure: float = 0.0  # C5
	cost_total: float = 0.0  # CT

	# -- helpers de acesso rápido --

	def pipe_states(self) -> list[SegmentState]:
		"""Retorna apenas os ``SegmentState`` de tubulações (is_pipe)."""
		return [ss for ss in self.segment_states if ss.is_pipe]

	def pipe_states_by_position(
		self, pos: SegmentPosition
	) -> list[SegmentState]:
		return [ss for ss in self.segment_states
				if ss.is_pipe and ss.position == pos]


@dataclass
class OptimizationResult:
	"""Resultado da otimização global."""

	success: bool
	message: str
	x: np.ndarray
	state: StationState
	iterations: int


class GlobalOptimization:
	"""Modelo + otimização da aba ``otimiz global``."""

	# --- Dados fixos da planilha (B/C/D/G/H e cotas dadas) ---
	VOL_SUP_HM3 = 84.9  # B2
	VOL_INF_HM3 = 81.2  # C2
	H_MED_SUP = 2036 - 1960  # B3 (= 76 m)
	H_MED_INF = 1672 - 1590  # C3 (= 82 m)
	FLOW_TURBINE = 144.0  # D3 (m³/s)
	EFF_PUMP = 0.82  # G3
	EFF_TURBINE = 0.95  # H3
	N_MACHINES = 2  # H14

	HOURS_OFF = 2.0  # K9
	BORDA_LIVRE = 1.0  # D21

	COTA_TERRENO_SUP = 1930.0  # D13 (Nt1)
	COTA_POWERHOUSE = 1530.0  # D25 (cota casa de força)
	COTA_TERRENO_INF = 1561.0  # D26 (Nt2)

	COST_LOW_PRESSURE = 3.043992722199214  # R16 (milhões R$/km·m²)
	COST_HIGH_PRESSURE = 6.545741267696708  # R17 (milhões R$/km·m²)

	VISCOSITY = 1e-6  # viscosidade cinemática (m²/s)

	# Cavitação (AM/AN)
	PATM_MCA = 10.0  # AN3
	HVAPOR_MCA = 0.433  # AN5
	PUMP_SPEED_RPM = 428.58  # AN16 (n)
	PUMP_TYPE = "Centrífuga"  # AN13

	# Restrições (F22:I37)
	DAM_HEIGHT_MAX = 150.0  # I23
	POWER_MIN_PER_MACHINE = 200.0  # I26 (MW)
	RATIO_MAX = 1.1  # I27 (Pturb/Pbomb <=)
	RATIO_MIN = 0.85  # I28 (Pturb/Pbomb >=)
	HOURS_TURB_MIN = 6.0  # I29
	V_MAX_CONCRETE = 7.0  # I33
	V_MAX_STEEL = 8.0  # I34
	V_MIN = 2.0  # I35
	HEAD_LOSS_MAX_FRAC = 0.04  # I36 (4%)
	NPSH_SAFETY_FACTOR = 1.15  # I37

	# x0 legado para o circuito padrão de 3 tubos
	_LEGACY_X0 = [
		150.0,
		85.72592905776965,
		5.51598405971158,
		4.787306585660682,
		5.117846846950154,
		14.88275746455099,
	]

	def __init__(
		self,
		dam_cost: DamCostModel | None = None,
		equipment_cost: EquipmentCostModel | None = None,
		material_strength: MaterialStrength | None = None,
		circuit: HydraulicCircuit | None = None,
	) -> None:
		self.dam_cost = dam_cost or DamCostModel()
		self.equipment_cost = equipment_cost or EquipmentCostModel()
		self.material_strength = material_strength or MaterialStrength()
		self.circuit = circuit or HydraulicCircuit.default_circuit()

		# Cache de dados do circuito (imutáveis durante a otimização)
		self._eval_order = self.circuit.evaluation_order()
		self._pipe_configs = self.circuit.pipe_segments
		self._n_pipes = self.circuit.n_pipe_segments

		# Áreas dos reservatórios (B4/C4)
		self.area_sup = self.VOL_SUP_HM3 * 1e6 / self.H_MED_SUP
		self.area_inf = self.VOL_INF_HM3 * 1e6 / self.H_MED_INF

	# ------------------------------------------------------------------
	# Núcleo: avalia o estado completo da usina para um vetor de decisão.
	# ------------------------------------------------------------------
	def evaluate(self, x) -> StationState:
		h1 = float(x[0])
		h2 = float(x[1])
		n = self._n_pipes
		pipe_diameters = [float(x[2 + i]) for i in range(n)]
		hours_pump = float(x[2 + n])

		g = AuxData.GRAVITY
		gamma = AuxData.WATER_DENSITY
		q = self.FLOW_TURBINE

		st = StationState(h1=h1, h2=h2, pipe_diameters=pipe_diameters,
						  hours_pump=hours_pump)

		# Resolução do diâmetro pelo "diameter_key" do circuito
		def _diam(key: str) -> float:
			if key.startswith("pipe:"):
				return pipe_diameters[int(key.split(":")[1])]
			if key.startswith("fixed:"):
				return float(key.split(":")[1])
			return pipe_diameters[0]

		# --- Perda de carga (Swamee-Jain) por segmento ---
		loss_recalque = 0.0
		loss_suction = 0.0
		pipe_state_data: list[tuple[SegmentState, object]] = []

		for entry in self._eval_order:
			d = _diam(entry["diameter_key"])
			area = math.pi * d**2 / 4
			v = q / area
			eps = AuxData.roughness(entry["material"])
			re = (4 * q) / (math.pi * d * self.VISCOSITY)
			f = 0.25 / (
				math.log10(0.27 * (eps / d) + 5.74 / re**0.9)
			) ** 2
			shape = entry["shape"]
			if shape == "Reto":
				length = entry["straight_length"]
			else:
				length = AuxData.equivalent_length_factor(shape) * d
			hl = f * (length / d) * (v**2 / (2 * g))

			if entry["position"] == SegmentPosition.ANTES:
				loss_recalque += hl
			else:
				loss_suction += hl

			is_pipe = entry["type"] == "pipe"
			ss = SegmentState(
				name=entry["name"],
				segment_type=entry["type"],
				position=entry["position"],
				material=entry["material"],
				diameter=d, area=area, velocity=v,
				head_loss=hl, is_pipe=is_pipe,
				pipe_type=(entry["pipe_type"].value if is_pipe else ""),
			)
			st.segment_states.append(ss)
			if is_pipe:
				pipe_state_data.append((ss, entry["segment"]))

		st.head_loss_recalque = loss_recalque
		st.head_loss_suction = loss_suction
		st.head_loss_total = loss_recalque + loss_suction

		# --- Dados do primeiro tubo de cada grupo (para submergência) ---
		antes_data = [(ss, cfg) for ss, cfg in pipe_state_data
					  if cfg.position == SegmentPosition.ANTES]
		depois_data = [(ss, cfg) for ss, cfg in pipe_state_data
					   if cfg.position == SegmentPosition.DEPOIS]

		d1a = antes_data[0][0].diameter
		v1a = antes_data[0][0].velocity
		d1d = depois_data[0][0].diameter
		v1d = depois_data[0][0].velocity

		# --- Submergência / cotas reservatório superior ---
		k = AuxData.K_TOMADA_SIMETRICA
		s1 = k * v1a * math.sqrt(d1a)  # D19
		hm1 = 2 * s1  # D20
		st.cota_max_sup = (self.COTA_TERRENO_SUP + h1) - self.BORDA_LIVRE
		st.cota_min_sup = self.COTA_TERRENO_SUP + hm1 + d1a + s1  # D16
		st.cota_tomada = st.cota_min_sup - s1 - d1a / 2  # D17

		# Cadeia de cotas ANTES (cada tubo: cota = cota_anterior - L·i/100)
		prev_cota = st.cota_tomada
		for ss, cfg in antes_data:
			ss.cota = prev_cota - (cfg.length * cfg.slope / 100)
			prev_cota = ss.cota

		# --- Submergência / cotas reservatório inferior ---
		s2 = k * v1d * math.sqrt(d1d)  # D32
		hm2 = 2 * s2  # D33
		st.cota_max_inf = (self.COTA_TERRENO_INF + h2) - self.BORDA_LIVRE
		st.cota_min_inf = self.COTA_TERRENO_INF + hm2 + s2 + d1d  # D29
		st.cota_e = st.cota_min_inf - s2 - d1d / 2  # D30

		# Cadeia de cotas DEPOIS
		prev_cota = st.cota_e
		for ss, cfg in depois_data:
			ss.cota = prev_cota - (cfg.length * cfg.slope / 100)
			prev_cota = ss.cota

		# --- Alturas bruta/líquida ---
		st.head_gross_turb = st.cota_min_sup - st.cota_max_inf  # HBt
		st.head_gross_pump = st.cota_max_sup - st.cota_min_inf  # HBb
		st.head_net_turb = st.head_gross_turb - st.head_loss_total
		st.head_net_pump = st.head_gross_pump - st.head_loss_total

		# --- Ciclo diário e vazões ---
		st.hours_turb = 24 - hours_pump - self.HOURS_OFF
		st.vol_turbined = (q * (st.hours_turb * 3600)) / 1e6
		st.flow_pump = (st.vol_turbined * 1e6) / (hours_pump * 3600)
		st.delta_sup = (st.vol_turbined * 1e6) / self.area_sup
		st.delta_inf = (st.vol_turbined * 1e6) / self.area_inf

		# --- Potências (MW por máquina) ---
		st.power_turbine = (
			gamma * g * (q / self.N_MACHINES)
			* st.head_gross_turb * self.EFF_TURBINE
		) / 1e6
		st.power_pump = (
			g * gamma * (st.flow_pump / self.N_MACHINES)
			* st.head_net_pump / self.EFF_PUMP
		) / 1e6
		st.power_ratio = (
			st.power_turbine / st.power_pump if st.power_pump else float("inf")
		)

		# --- Cavitação (NPSH) ---
		ha = st.cota_min_inf - self.COTA_POWERHOUSE
		st.npsh_available = (
			self.PATM_MCA + ha - st.head_loss_suction - self.HVAPOR_MCA
		)
		phi = AuxData.pump_phi(self.PUMP_TYPE)
		if ha > 0 and st.flow_pump > 0:
			nq = self.PUMP_SPEED_RPM * math.sqrt(st.flow_pump) / (ha**0.75)
			sigma = phi * nq ** (4 / 3)
			st.npsh_required = ha * sigma
		else:
			st.npsh_required = float("inf")
		st.npsh_ratio = (
			st.npsh_available / st.npsh_required
			if st.npsh_required else float("inf")
		)

		# --- Pressões nos pipe segments ---
		for ss, _cfg in antes_data:
			ss.pressure = (
				st.cota_max_sup - st.head_loss_recalque
				- ss.cota - (v1a**2 / (2 * g))
			) * gamma
		for ss, _cfg in depois_data:
			ss.pressure = (
				st.cota_max_inf - st.head_loss_suction
				- ss.cota - (v1d**2 / (2 * g))
			) * gamma

		# --- Custos ---
		st.cost_dam_sup = self.dam_cost.cost(h1)
		st.cost_dam_inf = self.dam_cost.cost(h2)
		st.cost_powerhouse = (
			self.equipment_cost.cost(st.power_turbine) * self.N_MACHINES
		)

		cost_lp = 0.0
		cost_hp = 0.0
		for ss, cfg in pipe_state_data:
			if cfg.pipe_type == PipeType.ALTA_PRESSAO:
				cost_hp += (cfg.length / 1000) * ss.area * self.COST_HIGH_PRESSURE
			else:  # BAIXA_PRESSAO ou SUCCAO
				cost_lp += (cfg.length / 1000) * ss.area * self.COST_LOW_PRESSURE
		st.cost_low_pressure = cost_lp
		st.cost_high_pressure = cost_hp
		st.cost_total = (
			st.cost_dam_sup + st.cost_dam_inf + st.cost_powerhouse
			+ st.cost_low_pressure + st.cost_high_pressure
		)
		return st

	# ------------------------------------------------------------------
	# Função objetivo e restrições.
	# ------------------------------------------------------------------
	def objective(self, x) -> float:
		"""Custo total CT (milhões R$) — a ser minimizado."""
		return self.evaluate(x).cost_total

	def _constraints(self) -> list[dict]:
		"""Restrições de desigualdade no formato SLSQP (g(x) >= 0)."""
		ms = self.material_strength
		funcs: list = []

		# --- Velocidades máximas/mínimas por tubo ---
		for i, pipe in enumerate(self._pipe_configs):
			v_max = (self.V_MAX_CONCRETE
					 if pipe.material == PipeMaterial.CONCRETO
					 else self.V_MAX_STEEL)

			def c_vmax(x, _i=i, _vm=v_max):
				return _vm - self.evaluate(x).pipe_states()[_i].velocity

			def c_vmin(x, _i=i):
				return self.evaluate(x).pipe_states()[_i].velocity - self.V_MIN

			funcs.extend([c_vmax, c_vmin])

		# --- Perda de carga máxima (I36) ---
		def c_head_loss(x):
			st = self.evaluate(x)
			if st.head_gross_turb <= 0:
				return -1.0
			return self.HEAD_LOSS_MAX_FRAC - (
				st.head_loss_total / st.head_gross_turb
			)
		funcs.append(c_head_loss)

		# --- Pressão por tubo vs. resistência do material ---
		for i, pipe in enumerate(self._pipe_configs):
			strength = (ms.concrete_strength_kgf_m2
						if pipe.material == PipeMaterial.CONCRETO
						else ms.steel_strength_kgf_m2)

			def c_pressure(x, _i=i, _s=strength):
				return _s - self.evaluate(x).pipe_states()[_i].pressure

			funcs.append(c_pressure)

		# --- Demais restrições (invariantes ao número de tubos) ---
		def c_npsh(x):
			return self.evaluate(x).npsh_ratio - self.NPSH_SAFETY_FACTOR

		def c_ratio_max(x):
			return self.RATIO_MAX - self.evaluate(x).power_ratio

		def c_ratio_min(x):
			return self.evaluate(x).power_ratio - self.RATIO_MIN

		def c_h1_max(x):
			return self.DAM_HEIGHT_MAX - x[0]

		def c_h2_max(x):
			return self.DAM_HEIGHT_MAX - x[1]

		def c_h1_min(x):
			st = self.evaluate(x)
			return x[0] - (self.H_MED_SUP + st.delta_sup)

		def c_h2_min(x):
			st = self.evaluate(x)
			return x[1] - (self.H_MED_INF + st.delta_inf)

		def c_power_min(x):
			return self.evaluate(x).power_turbine - self.POWER_MIN_PER_MACHINE

		def c_hours_turb(x):
			return self.evaluate(x).hours_turb - self.HOURS_TURB_MIN

		funcs.extend([
			c_npsh, c_ratio_max, c_ratio_min,
			c_h1_max, c_h2_max, c_h1_min, c_h2_min,
			c_power_min, c_hours_turb,
		])
		return [{"type": "ineq", "fun": f} for f in funcs]

	# ------------------------------------------------------------------
	# Otimização (substitui o Solver do Excel).
	# ------------------------------------------------------------------
	def solve(self, x0=None, maxiter: int = 500) -> OptimizationResult:
		"""Minimiza o custo total CT sujeito às restrições (SLSQP)."""
		n = self._n_pipes
		if x0 is None:
			if n == 3:
				x0 = list(self._LEGACY_X0)
			else:
				x0 = ([150.0, self.H_MED_INF + 10]
					   + [8.0] * n
					   + [14.0])
		x0 = np.asarray(x0, dtype=float)

		# Limites: [h1, h2, D_0 … D_(n-1), hours_pump]
		bounds = [
			(self.H_MED_SUP, self.DAM_HEIGHT_MAX),  # h1
			(self.H_MED_INF, self.DAM_HEIGHT_MAX),  # h2
		]
		bounds.extend([(1.0, 15.0)] * n)             # diâmetros
		bounds.append((1.0, 22.0 - self.HOURS_OFF))  # hours_pump

		res = minimize(
			self.objective,
			x0,
			method="SLSQP",
			bounds=bounds,
			constraints=self._constraints(),
			options={"maxiter": maxiter, "ftol": 1e-6},
		)
		return OptimizationResult(
			success=bool(res.success),
			message=str(res.message),
			x=res.x,
			state=self.evaluate(res.x),
			iterations=int(res.get("nit", 0)),
		)
