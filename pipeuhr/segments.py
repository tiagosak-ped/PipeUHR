"""Segmentos do circuito hidráulico da UHR.

Define os tipos de segmento (tubulação e peças diversas), suas
propriedades, e o ``HydraulicCircuit`` que os organiza em ordem de
avaliação com geração automática das tomadas d'água.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Union


# ── Enums ─────────────────────────────────────────────────────────────

class SegmentPosition(Enum):
	ANTES = "Antes"    # Before powerhouse (discharge/recalque)
	DEPOIS = "Depois"  # After powerhouse (suction)


class PipeMaterial(Enum):
	CONCRETO = "Concreto"
	ACO = "Aço"


class PipeType(Enum):
	BAIXA_PRESSAO = "Baixa Pressão"
	ALTA_PRESSAO = "Alta Pressão"
	SUCCAO = "Sucção"


class DiverseSegmentKind(Enum):
	CURVA = "Curva"
	BIFURCACAO = "Bifurcação"
	TOMADA_DAGUA = "Tomada d'água"


# ── Segment configuration dataclasses ─────────────────────────────────

@dataclass
class PipeSegment:
	"""Trecho de tubulação reta (adiciona 1 variável de diâmetro ao solver)."""

	name: str
	length: float          # metros
	slope: float           # %
	material: PipeMaterial
	pipe_type: PipeType
	position: SegmentPosition


@dataclass
class DiverseSegment:
	"""Peça diversa (curva, bifurcação, etc.) — diâmetro fixo ou herdado."""

	name: str
	kind: DiverseSegmentKind
	position: SegmentPosition
	diameter: float | None = None   # None → herda do tubo adjacente
	angle: float | None = None      # graus (apenas para CURVA)


Segment = Union[PipeSegment, DiverseSegment]


# ── Segment evaluation result ─────────────────────────────────────────

@dataclass
class SegmentState:
	"""Resultado calculado para um segmento durante a avaliação."""

	name: str
	segment_type: str          # "pipe", "diverse", "auto"
	position: SegmentPosition
	material: str              # "Concreto" ou "Aço"
	diameter: float = 0.0
	area: float = 0.0
	velocity: float = 0.0
	head_loss: float = 0.0
	cota: float = 0.0          # somente pipe segments
	pressure: float = 0.0      # somente pipe segments
	is_pipe: bool = False
	pipe_type: str = ""        # PipeType.value (somente pipe)


# ── HydraulicCircuit ──────────────────────────────────────────────────

class HydraulicCircuit:
	"""Circuito hidráulico parametrizado.

	Mantém a lista ordenada de segmentos (pipe + diverse) e gera
	automaticamente as tomadas d'água no início do grupo ANTES e no
	final do grupo DEPOIS.
	"""

	def __init__(self, segments: list[Segment] | None = None) -> None:
		self._segments: list[Segment] = list(segments) if segments else []
		self._validate()

	# ── Propriedades ──────────────────────────────────────────────────

	@property
	def segments(self) -> list[Segment]:
		return list(self._segments)

	@property
	def pipe_segments(self) -> list[PipeSegment]:
		return [s for s in self._segments if isinstance(s, PipeSegment)]

	@property
	def n_pipe_segments(self) -> int:
		return len(self.pipe_segments)

	def pipes_by_position(self, pos: SegmentPosition) -> list[PipeSegment]:
		return [s for s in self._segments
				if isinstance(s, PipeSegment) and s.position == pos]

	# ── Avaliação ordenada (inclui tomadas d'água automáticas) ────────

	def evaluation_order(self) -> list[dict]:
		"""Retorna a sequência de avaliação completa.

		Cada item é um dict com chaves:
		  - ``"segment"``: o PipeSegment, DiverseSegment ou None (auto)
		  - ``"type"``: ``"pipe"``, ``"diverse"`` ou ``"auto"``
		  - ``"name"``: nome do segmento
		  - ``"position"``: SegmentPosition
		  - ``"material"``: str do material
		  - ``"shape"``: forma para cálculo do comprimento equivalente
		  - ``"straight_length"``: comprimento reto (somente "Reto")
		  - ``"diameter_key"``: ``"pipe:<idx>"`` ou ``"auto:<pos>"``
		"""
		antes = [s for s in self._segments
				 if s.position == SegmentPosition.ANTES]
		depois = [s for s in self._segments
				  if s.position == SegmentPosition.DEPOIS]

		order: list[dict] = []

		# ── ANTES: tomada d'água no início ────────────────────────────
		pipes_antes = self.pipes_by_position(SegmentPosition.ANTES)
		if pipes_antes:
			order.append(self._make_auto_tomada(
				SegmentPosition.ANTES, pipes_antes[0]))

		# ── ANTES: segmentos na ordem do usuário ──────────────────────
		pipe_idx_antes = 0
		last_pipe_idx_antes = -1
		for seg in antes:
			if isinstance(seg, PipeSegment):
				idx = self._pipe_index(seg)
				order.append(self._make_pipe_entry(seg, idx))
				last_pipe_idx_antes = idx
				pipe_idx_antes += 1
			else:
				order.append(self._make_diverse_entry(
					seg, last_pipe_idx_antes))

		# ── DEPOIS: segmentos na ordem do usuário ─────────────────────
		pipes_depois = self.pipes_by_position(SegmentPosition.DEPOIS)
		last_pipe_idx_depois = -1
		for seg in depois:
			if isinstance(seg, PipeSegment):
				idx = self._pipe_index(seg)
				order.append(self._make_pipe_entry(seg, idx))
				last_pipe_idx_depois = idx
			else:
				order.append(self._make_diverse_entry(
					seg, last_pipe_idx_depois))

		# ── DEPOIS: tomada d'água no final ────────────────────────────
		if pipes_depois:
			order.append(self._make_auto_tomada(
				SegmentPosition.DEPOIS, pipes_depois[0]))

		return order

	# ── Fábrica do circuito padrão (backward compatible) ──────────────

	@classmethod
	def default_circuit(cls) -> "HydraulicCircuit":
		"""Circuito padrão com 3 tubos + 2 peças diversas (legado)."""
		return cls([
			PipeSegment("AB", 4029.0, 0.45, PipeMaterial.CONCRETO,
						PipeType.BAIXA_PRESSAO, SegmentPosition.ANTES),
			DiverseSegment("Curva 45", DiverseSegmentKind.CURVA,
						   SegmentPosition.ANTES, angle=45),
			PipeSegment("BC", 577.0, 45.0, PipeMaterial.ACO,
						PipeType.ALTA_PRESSAO, SegmentPosition.ANTES),
			DiverseSegment("Bifurcação casa de força",
						   DiverseSegmentKind.BIFURCACAO,
						   SegmentPosition.ANTES),
			PipeSegment("EF", 512.0, 19.0, PipeMaterial.CONCRETO,
						PipeType.SUCCAO, SegmentPosition.DEPOIS),
		])

	# ── Helpers internos ──────────────────────────────────────────────

	def _validate(self) -> None:
		pipes_antes = self.pipes_by_position(SegmentPosition.ANTES)
		pipes_depois = self.pipes_by_position(SegmentPosition.DEPOIS)
		if not pipes_antes:
			raise ValueError("Circuito precisa de ≥1 tubo ANTES.")
		if not pipes_depois:
			raise ValueError("Circuito precisa de ≥1 tubo DEPOIS.")

	def _pipe_index(self, pipe: PipeSegment) -> int:
		return self.pipe_segments.index(pipe)

	def _make_pipe_entry(self, seg: PipeSegment, idx: int) -> dict:
		return {
			"segment": seg,
			"type": "pipe",
			"name": seg.name,
			"position": seg.position,
			"material": seg.material.value,
			"shape": "Reto",
			"straight_length": seg.length,
			"diameter_key": f"pipe:{idx}",
			"pipe_type": seg.pipe_type,
			"slope": seg.slope,
		}

	def _make_diverse_entry(self, seg: DiverseSegment,
							prev_pipe_idx: int) -> dict:
		shape = self._diverse_shape(seg)
		mat = self._diverse_material(seg, prev_pipe_idx)
		return {
			"segment": seg,
			"type": "diverse",
			"name": seg.name,
			"position": seg.position,
			"material": mat,
			"shape": shape,
			"straight_length": None,
			"diameter_key": (f"fixed:{seg.diameter}"
							 if seg.diameter is not None
							 else f"pipe:{prev_pipe_idx}"),
		}

	def _make_auto_tomada(self, pos: SegmentPosition,
						  first_pipe: PipeSegment) -> dict:
		label = ("recalque" if pos == SegmentPosition.ANTES
				 else "sucção")
		idx = self._pipe_index(first_pipe)
		return {
			"segment": None,
			"type": "auto",
			"name": f"tomada d'água ({label})",
			"position": pos,
			"material": first_pipe.material.value,
			"shape": "Red. gradual",
			"straight_length": None,
			"diameter_key": f"pipe:{idx}",
		}

	@staticmethod
	def _diverse_shape(seg: DiverseSegment) -> str:
		if seg.kind == DiverseSegmentKind.CURVA:
			angle = int(seg.angle) if seg.angle else 45
			return f"Curva {angle}"
		if seg.kind == DiverseSegmentKind.BIFURCACAO:
			return "Bifurcação"
		if seg.kind == DiverseSegmentKind.TOMADA_DAGUA:
			return "Red. gradual"
		return "Reto"

	def _diverse_material(self, seg: DiverseSegment,
						  prev_pipe_idx: int) -> str:
		pipes = self.pipe_segments
		if 0 <= prev_pipe_idx < len(pipes):
			return pipes[prev_pipe_idx].material.value
		pipes_in_group = self.pipes_by_position(seg.position)
		if pipes_in_group:
			return pipes_in_group[0].material.value
		return PipeMaterial.CONCRETO.value
