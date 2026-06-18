"""Pacote PipeUHR — migração da planilha 'Planilha Chris.xlsm'.

Cada módulo corresponde, no mínimo, a uma aba da planilha original:

- ``aux_data``           -> aba ``aux`` (constantes e tabelas de lookup)
- ``material_strength``  -> aba ``resistencia materiais``
- ``reversible_turbines``-> aba ``Turbinas Reversíveis``
- ``dam_cost``           -> aba ``Hbarragem Custo Brasil e Mundo``
- ``equipment_cost``     -> aba ``Potencia Custo equip BR e mundo``
- ``turbine_selection``  -> aba ``Seleção de turbina``
- ``segments``           -> segmentos do circuito hidráulico
- ``global_optimization``-> aba ``otimiz global`` (modelo + Solver)
- ``drawing``            -> aba ``desenho``
- ``constraint_simulator``-> simulador de verificação das restrições
"""

from .aux_data import AuxData
from .material_strength import MaterialStrength
from .reversible_turbines import ReversibleTurbines
from .dam_cost import DamCostModel
from .equipment_cost import EquipmentCostModel
from .turbine_selection import TurbineSelection
from .segments import (
	DiverseSegment,
	DiverseSegmentKind,
	HydraulicCircuit,
	PipeMaterial,
	PipeSegment,
	PipeType,
	SegmentPosition,
	SegmentState,
)
from .global_optimization import GlobalOptimization, OptimizationResult, StationState
from .drawing import Drawing
from .constraint_simulator import (
	ConstraintSimulator,
	ConstraintCheck,
	SimulationReport,
)

__all__ = [
	"AuxData",
	"MaterialStrength",
	"ReversibleTurbines",
	"DamCostModel",
	"EquipmentCostModel",
	"TurbineSelection",
	"SegmentPosition",
	"PipeMaterial",
	"PipeType",
	"DiverseSegmentKind",
	"PipeSegment",
	"DiverseSegment",
	"SegmentState",
	"HydraulicCircuit",
	"GlobalOptimization",
	"OptimizationResult",
	"StationState",
	"Drawing",
	"ConstraintSimulator",
	"ConstraintCheck",
	"SimulationReport",
]
