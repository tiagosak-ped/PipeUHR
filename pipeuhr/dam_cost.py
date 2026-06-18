"""Aba ``Hbarragem Custo Brasil e Mundo`` — custo da barragem × altura.

Ajusta um polinômio de grau 4 que estima o custo da barragem (e adutoras)
em função da altura da barragem ``Hbarragem``. No Excel, os coeficientes
``a0..a4`` (C24:G24) eram obtidos pelo Solver minimizando a soma dos
quadrados das diferenças (R17). Aqui usamos ``numpy.polyfit`` para o mesmo
ajuste de mínimos quadrados.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DamSample:
	"""Projeto real usado no ajuste (altura, custo real da barragem)."""

	plant: str
	dam_height: float          # E — Hbarragem (m)
	dam_cost_real: float       # J — Barragens e adutoras, custo real (milhões R$)


class DamCostModel:
	"""Função de custo de barragem ``C(H)`` (aba Hbarragem Custo)."""

	# C24:G24 — coeficientes originais obtidos no Solver do Excel.
	EXCEL_COEFFS = (
		12626.689742853076,   # a0
		-549.6527431825076,   # a1
		8.415169857227895,    # a2
		-0.049313958572576706,  # a3
		9.827448568312736e-05,  # a4
	)

	def __init__(self, refit: bool = True) -> None:
		# E2:J16 — amostras reais (altura, custo real da barragem)
		self.samples = [
			DamSample("UHE P.Afonso IV", 35, 2863.866496161652),
			DamSample("UHE Sinop", 50, 853.374359967361),
			DamSample("UHE Teles Pires", 80, 2345.5741588933397),
			DamSample("UHE Corumbá", 90, 1164.3497623283483),
			DamSample("UHE Itaparica", 105, 4785.164137105117),
			DamSample("UHE Xingó", 140, 4794.806785240342),
			DamSample("UHE Campos Novos", 196, 1881.5626525959901),
			DamSample("Guizhou Jiakeshan PSP sup.", 39, 28.961511750398586),
			DamSample("Guizhou Jiakeshan PSP inf.", 117, 2345.8824517822904),
			DamSample("Zhejiang Jingning PSP sup.", 86.5, 565.1045286743558),
			DamSample("Zhejiang Jingning PSP inf.", 105.5, 1250.4726470292371),
			DamSample("Anhui Mayuan'an PSP sup.", 69, 1100.652018993449),
			DamSample("Anhui Mayuan'an PSP inf.", 66, 921.3601272198479),
			DamSample("Tanahu / Upper Seti", 140, 1487.354330442648),
			DamSample("Roshi Nepal Inferior", 44.5, 414.28245445737366),
		]

		if refit:
			heights = np.array([s.dam_height for s in self.samples], dtype=float)
			costs = np.array([s.dam_cost_real for s in self.samples], dtype=float)
			# polyfit retorna [a4, a3, a2, a1, a0]; invertemos para [a0..a4].
			poly_high_to_low = np.polyfit(heights, costs, deg=4)
			self.coeffs = tuple(poly_high_to_low[::-1])
		else:
			self.coeffs = self.EXCEL_COEFFS

	def cost(self, dam_height: float) -> float:
		"""Custo estimado da barragem (milhões R$) para a altura ``H`` (m)."""
		a0, a1, a2, a3, a4 = self.coeffs
		h = dam_height
		return a0 + a1 * h + a2 * h**2 + a3 * h**3 + a4 * h**4

	def sum_squared_error(self) -> float:
		"""Soma dos quadrados das diferenças (R17, função objetivo)."""
		return float(sum((s.dam_cost_real - self.cost(s.dam_height)) ** 2
						 for s in self.samples))
