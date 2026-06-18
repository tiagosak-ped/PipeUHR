"""Aba ``aux`` — constantes físicas e tabelas de lookup.

Reproduz as tabelas auxiliares usadas pelas fórmulas da planilha:
- Aceleração da gravidade e peso específico da água (H4/I4).
- Coeficiente K para cálculo da tomada d'água (L3/L4).
- Rugosidade ``epsilon`` e fator de cavitação K por material (B8:D9).
- Comprimentos equivalentes ``Le/Dh`` por forma de tubulação (B12:C20).
- Fator ``phi`` por tipo de bomba (B23:C25).
"""

from __future__ import annotations


class AuxData:
	"""Constantes e tabelas auxiliares (aba ``aux``)."""

	# H4 / I4
	GRAVITY = 9.81          # Aceleração da gravidade (m/s²)
	WATER_DENSITY = 1000.0  # Peso específico da água (Kgf/m³)

	# K2:L4 — Cálculo da tomada d'água (Manual Eletrobrás 2003)
	K_TOMADA_SIMETRICA = 0.545   # condições simétricas aproximadas
	K_TOMADA_ASSIMETRICA = 0.725  # condições assimétricas aproximadas

	# B7:D9 — Material da tubulação: rugosidade epsilon (m) e K de cavitação
	MATERIAL_ROUGHNESS = {
		"Aço": 0.0001,
		"Concreto": 0.0003,
	}
	MATERIAL_CAVITATION_K = {
		"Aço": 0.5,
		"Concreto": 5.0,
	}

	# B11:C20 — Forma da tubulação: comprimento equivalente Le/Dh
	# "Reto" não tem Le/Dh (o comprimento é informado diretamente).
	EQUIVALENT_LENGTH = {
		"Reto": None,
		"Curva 45": 15,
		"Curva 90": 30,
		"Red. gradual": 6,
		"Bifurcação": 65,
		"Tê fluxo direto": 20,
		"Saída de túnel ou duto": 35,
		"Aceleração na tomada d'água": 54,
		"Ampliação gradual": 12,
	}

	# B22:C25 — Tipo de bomba: fator phi
	PUMP_PHI = {
		"Centrífuga": 0.0011,
		"Helicoidal": 0.0013,
		"Axial": 0.00145,
	}

	# B2:B5 — Tipos de turbina-bomba (referência)
	TURBINE_TYPES = ("Francis", "Kaplan", "Pelton")

	@classmethod
	def roughness(cls, material: str) -> float:
		"""Rugosidade epsilon (m) por material da tubulação."""
		return cls.MATERIAL_ROUGHNESS[cls._normalize_material(material)]

	@classmethod
	def cavitation_k(cls, material: str) -> float:
		"""Fator K de cavitação por material da tubulação."""
		return cls.MATERIAL_CAVITATION_K[cls._normalize_material(material)]

	@classmethod
	def equivalent_length_factor(cls, shape: str):
		"""Fator Le/Dh por forma da tubulação (``None`` para trecho reto)."""
		return cls.EQUIVALENT_LENGTH[shape]

	@classmethod
	def pump_phi(cls, pump_type: str) -> float:
		"""Fator phi por tipo de bomba."""
		return cls.PUMP_PHI[pump_type]

	@staticmethod
	def _normalize_material(material: str) -> str:
		"""Aceita variações usadas na planilha (ex.: 'aço', 'concreto')."""
		key = material.strip().lower()
		if key.startswith("aç") or key.startswith("aco") or key == "aço":
			return "Aço"
		if key.startswith("concret"):
			return "Concreto"
		# fallback: capitaliza
		return material.capitalize()
