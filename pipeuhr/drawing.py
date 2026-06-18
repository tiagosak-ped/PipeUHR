"""Aba ``desenho`` — cotas para o desenho esquemático da UHR.

Na planilha, a aba ``desenho`` apenas consolida (via VLOOKUP no modelo
``otimiz global``) as cotas relevantes para montar o desenho da usina.
Aqui, a classe coleta essas cotas a partir de um ``StationState`` já
calculado pela otimização global.
"""

from __future__ import annotations

from dataclasses import dataclass

from .global_optimization import StationState
from .segments import SegmentPosition


@dataclass(frozen=True)
class DrawingLevels:
	"""Cotas usadas no desenho esquemático (m)."""

	cota_topo_barragem_sup: float
	cota_max_reserv_sup: float
	cota_min_reserv_sup: float
	cota_tomada_dagua: float
	cota_terreno_sup: float
	cota_b: float
	cota_c: float
	cota_topo_barragem_inf: float
	cota_max_reserv_inf: float
	cota_min_reserv_inf: float
	cota_e: float
	cota_d: float
	cota_terreno_inf: float
	cota_casa_forca: float
	altura_bruta_turb: float
	altura_liquida_turb: float
	altura_bruta_bomb: float
	altura_liquida_bomb: float


class Drawing:
	"""Consolida cotas do modelo para o desenho (aba ``desenho``)."""

	PLANT_NAME = "Limberg II"

	def __init__(self, station: StationState,
				 cota_terreno_sup: float, cota_terreno_inf: float,
				 cota_casa_forca: float) -> None:
		self.station = station
		self._cota_terreno_sup = cota_terreno_sup
		self._cota_terreno_inf = cota_terreno_inf
		self._cota_casa_forca = cota_casa_forca

	def levels(self) -> DrawingLevels:
		st = self.station

		# Cotas dos pipe segments por grupo posicional
		pipes_antes = st.pipe_states_by_position(SegmentPosition.ANTES)
		pipes_depois = st.pipe_states_by_position(SegmentPosition.DEPOIS)

		# cota_b = primeiro tubo ANTES (end cota)
		# cota_c = último tubo ANTES (end cota)
		cota_b = pipes_antes[0].cota if pipes_antes else 0.0
		cota_c = pipes_antes[-1].cota if pipes_antes else 0.0

		# cota_d = último tubo DEPOIS (end cota)
		cota_d = pipes_depois[-1].cota if pipes_depois else 0.0

		return DrawingLevels(
			cota_topo_barragem_sup=self._cota_terreno_sup + st.h1,
			cota_max_reserv_sup=st.cota_max_sup,
			cota_min_reserv_sup=st.cota_min_sup,
			cota_tomada_dagua=st.cota_tomada,
			cota_terreno_sup=self._cota_terreno_sup,
			cota_b=cota_b,
			cota_c=cota_c,
			cota_topo_barragem_inf=self._cota_terreno_inf + st.h2,
			cota_max_reserv_inf=st.cota_max_inf,
			cota_min_reserv_inf=st.cota_min_inf,
			cota_e=st.cota_e,
			cota_d=cota_d,
			cota_terreno_inf=self._cota_terreno_inf,
			cota_casa_forca=self._cota_casa_forca,
			altura_bruta_turb=st.head_gross_turb,
			altura_liquida_turb=st.head_net_turb,
			altura_bruta_bomb=st.head_gross_pump,
			altura_liquida_bomb=st.head_net_pump,
		)
