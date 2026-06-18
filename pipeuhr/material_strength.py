"""Aba ``resistencia materiais`` — resistência admissível dos materiais.

Converte o fck/limite de escoamento (MPa) para Kgf/m² usando o fator
1 MPa = 101.971,6 Kgf/m² e expõe a resistência usada na verificação de
pressão nos pontos C (concreto) e D (aço) da otimização global.
"""

from __future__ import annotations

from dataclasses import dataclass


# J1 — fator de conversão
MPA_TO_KGF_M2 = 101971.6


@dataclass(frozen=True)
class MaterialRecord:
	"""Linha da tabela de resistência de materiais."""

	source: str
	classe: str
	denomination: str
	fck_mpa: float

	@property
	def strength_kgf_m2(self) -> float:
		"""Resistência em Kgf/m² (H = G * F)."""
		return MPA_TO_KGF_M2 * self.fck_mpa


class MaterialStrength:
	"""Resistências admissíveis de concreto e aço (aba resistencia materiais)."""

	def __init__(self) -> None:
		# F2: concreto classe F (28 MPa) — usado no ponto C
		self.concrete = MaterialRecord(
			source="Eletrobrás 2003 - tabela 4.1 - Classe F",
			classe="F",
			denomination="Concreto estrutural (estruturas hidráulicas)",
			fck_mpa=28.0,
		)
		# F3: concreto projetado classe K (21 MPa)
		self.shotcrete = MaterialRecord(
			source="Eletrobrás 2003 - tabela 4.1 - Classe K",
			classe="K",
			denomination="Concreto projetado",
			fck_mpa=21.0,
		)
		# F4: aço NBR 5590 / ASTM A53 (205 MPa) — usado no ponto D
		self.steel = MaterialRecord(
			source="NBR 5590 (ASTM A53)",
			classe="A",
			denomination="Aço",
			fck_mpa=205.0,
		)

	@property
	def concrete_strength_kgf_m2(self) -> float:
		"""Resistência do concreto (H3 na planilha = ponto C)."""
		return self.shotcrete.strength_kgf_m2

	@property
	def steel_strength_kgf_m2(self) -> float:
		"""Resistência do aço (H4 na planilha = ponto D)."""
		return self.steel.strength_kgf_m2
