"""Aba ``Potencia Custo equip BR e mundo`` — custo de equipamento × potência.

Ajusta um polinômio de grau 2 que estima o custo dos equipamentos
eletromecânicos (turbinas + estruturas metálicas) em função da potência
instalada. No Excel, os coeficientes ``a0..a2`` (C17:E17) eram obtidos pelo
Solver minimizando a soma dos quadrados (S14). Aqui usamos ``numpy.polyfit``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EquipmentSample:
	"""Projeto real (potência, custo real de equipamento eletromecânico)."""

	plant: str
	power_mw: float            # H — Potência (MW)
	equipment_cost_real: float  # K + L — turbinas/geradores + estrutura metálica


class EquipmentCostModel:
	"""Função de custo de equipamento ``C(P)`` (aba Potencia Custo equip)."""

	# C17:E17 — coeficientes originais obtidos no Solver do Excel.
	EXCEL_COEFFS = (
		407.9085625148525,      # a0
		1.0139688720590772,     # a1
		9.096198114461508e-05,  # a2
	)

	def __init__(self, refit: bool = True) -> None:
		# H2:L13 — amostras: potência e (K + L) custo real do equipamento.
		self.samples = [
			EquipmentSample("UHE P.Afonso IV", 2462.4, 3355.6415510581 + 831.678401663106),
			EquipmentSample("UHE Sinop", 400, 749.7158925136985 + 107.75659291113287),
			EquipmentSample("UHE Teles Pires", 1820, 2374.502103299013 + 499.0070409978636),
			EquipmentSample("UHE Corumbá", 375, 607.4868325191384 + 149.46104609597847),
			EquipmentSample("UHE Itaparica", 1500, 2880.741130398295 + 713.5559620066069),
			EquipmentSample("UHE Xingó", 3162, 4184.9092906873975 + 1036.584674536625),
			EquipmentSample("UHE Campos Novos", 880, 720.961248727317 + 33.99283565204156),
			EquipmentSample("Guizhou Jiakeshan PSP sup.", 1600, 2228.0171640115504 + 499.79084418761835),
			EquipmentSample("Zhejiang Jingning PSP sup.", 1200, 1403.294326213896 + 250.9839570576084),
			EquipmentSample("Anhui Mayuan'an PSP sup.", 1200, 1351.5982804078649 + 323.52194339412756),
			EquipmentSample("Tanahu / Upper Seti", 128, 127.954498188891 + 362.99617693095803),
			EquipmentSample("Roshi Nepal Inferior", 2400, 552.3766059431648),
		]

		if refit:
			powers = np.array([s.power_mw for s in self.samples], dtype=float)
			costs = np.array([s.equipment_cost_real for s in self.samples], dtype=float)
			poly_high_to_low = np.polyfit(powers, costs, deg=2)
			self.coeffs = tuple(poly_high_to_low[::-1])
		else:
			self.coeffs = self.EXCEL_COEFFS

	def cost(self, power_mw: float) -> float:
		"""Custo estimado do equipamento (milhões R$) por máquina, potência ``P`` (MW)."""
		a0, a1, a2 = self.coeffs
		p = power_mw
		return a0 + a1 * p + a2 * p**2

	def sum_squared_error(self) -> float:
		"""Soma dos quadrados das diferenças (S14, função objetivo)."""
		return float(sum((s.equipment_cost_real - self.cost(s.power_mw)) ** 2
						 for s in self.samples))
