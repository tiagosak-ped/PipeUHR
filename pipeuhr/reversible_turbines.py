"""Aba ``Turbinas Reversíveis`` — base de turbinas-bomba reais.

Contém projetos reais de UHR (potência de turbinamento/bombeamento) e
calcula a relação média Pturb/Pbomb (F16 = AVERAGE), usada como referência
nas restrições da otimização global.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReversibleTurbine:
	"""Projeto de UHR com turbina reversível."""

	plant: str
	manufacturer: str
	model: str
	power_turbine_mw: float
	power_pump_mw: float
	source: str = ""

	@property
	def ratio(self) -> float:
		"""Relação Pturb/Pbomb (coluna F)."""
		return self.power_turbine_mw / self.power_pump_mw


@dataclass(frozen=True)
class PumpedStorageEfficiency:
	"""Eficiência reportada de usinas de armazenamento bombeado."""

	plant: str
	country: str
	project: str
	equipment: str
	power_per_unit: str
	units: int
	efficiency: str
	source: str


class ReversibleTurbines:
	"""Base de dados da aba ``Turbinas Reversíveis``."""

	def __init__(self) -> None:
		# A2:F12 — projetos com relação Pturb/Pbomb
		self.turbines = [
			ReversibleTurbine("Frades II (Portugal)", "Voith",
							  "Francis reversível, velocidade variável (DFIM)", 380, 440),
			ReversibleTurbine("Limmern/Linthal 2016 (Suíça)", "Andritz Hydro",
							  "8 × 150 MW Francis reversível", 150, 160),
			ReversibleTurbine("Goldisthal (Alemanha)", "Voith",
							  "Francis reversível 4 × 265 MW", 265, 299),
			ReversibleTurbine("Talegaon PHES (Índia)", "GE Renewable Energy",
							  "GE Francis reversível ~300 MW", 300, 330),
			ReversibleTurbine("Okawachi (Japão)", "Hitachi / Voith",
							  "Francis reversível 250 MW", 250, 275),
			ReversibleTurbine("Kopswerk II", "", "Turbinas Pelton", 525, 480),
			ReversibleTurbine("Rodundwerk I", "", "Francis", 49.5, 41),
			ReversibleTurbine("Rodundwerk II", "", "Francis", 295, 286),
			ReversibleTurbine("Kuhtai", "", "Francis", 150, 125),
			ReversibleTurbine("Kaprun", "", "Francis", 57, 65),
			ReversibleTurbine("Limberg II", "", "Francis", 240, 240),
		]

		# A25:H29 — eficiências reportadas (referência)
		self.efficiencies = [
			PumpedStorageEfficiency("Bath County Pumped Storage Station", "EUA",
									"Voith / GE", "Turbina-bomba reversível",
									"480–500 MW", 6, "ciclo ≈ 79%", "Wikipedia"),
			PumpedStorageEfficiency("Goldisthal Pumped Storage", "Alemanha",
									"Voith Hydro", "Francis reversível",
									"265 MW", 4, "sistema ~80–85%", "hydroprojekt.de"),
			PumpedStorageEfficiency("Avče Pumped Storage", "Eslovênia",
									"Litostroj Power", "Turbina-bomba reversível",
									"185 MW", 1, "ciclo ≈77%", "Wikipedia"),
			PumpedStorageEfficiency("Ludington Pumped Storage", "EUA",
									"Toshiba / Voith", "Francis",
									"362 MW", 6, "ciclo ≈70%", "Wikipedia"),
			PumpedStorageEfficiency("Dinorwig Power Station", "Reino Unido",
									"GEC-Alsthom", "Francis",
									"288 MW", 6, "ciclo 75–80%", "oftrb"),
		]

	@property
	def average_ratio(self) -> float:
		"""Relação média Pturb/Pbomb (F16 = AVERAGE(F2:F12))."""
		return sum(t.ratio for t in self.turbines) / len(self.turbines)
