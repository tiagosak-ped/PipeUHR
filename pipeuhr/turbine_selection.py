"""Aba ``Seleção de turbina`` — escolha do tipo de turbina.

Reproduz a lógica de seleção (Pelton / Francis / Kaplan) em função da
vazão por máquina e do desnível médio (queda). A planilha calcula a vazão
por máquina (Q3) e o desnível médio (Q4) e usa o gráfico H × Q para
indicar a faixa. Para UHRs, a referência é Francis reversível.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TurbineSelectionResult:
	"""Resultado da seleção de turbina."""

	flow_per_machine: float   # m³/s
	average_head: float       # m
	turbine_type: str
	note: str


class TurbineSelection:
	"""Seleção de turbina por queda (H) e vazão (Q) — aba Seleção de turbina."""

	# Limiares aproximados das regiões do gráfico H × Q.
	HIGH_HEAD = 350.0   # acima disso, tende a Pelton
	LOW_HEAD = 50.0     # abaixo disso, tende a Kaplan/hélice

	@classmethod
	def select(cls, total_flow: float, n_machines: int,
			   average_head: float) -> TurbineSelectionResult:
		"""Seleciona o tipo de turbina.

		- Alta queda / baixa vazão  -> Pelton (região vermelha).
		- Baixa queda / alta vazão  -> Kaplan/hélice (região verde).
		- Faixa intermediária       -> Francis (região amarela, mais comum).
		Para UHRs, adota-se Francis reversível.
		"""
		flow_per_machine = total_flow / n_machines

		if average_head >= cls.HIGH_HEAD:
			turbine = "Pelton"
			note = "Alta queda / baixa vazão (região vermelha)."
		elif average_head <= cls.LOW_HEAD:
			turbine = "Kaplan"
			note = "Baixa queda / alta vazão (região verde)."
		else:
			turbine = "Francis"
			note = "Faixa intermediária (região amarela) — UHR: Francis reversível."

		return TurbineSelectionResult(
			flow_per_machine=flow_per_machine,
			average_head=average_head,
			turbine_type=turbine,
			note=note,
		)
