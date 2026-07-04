"""Unit tests for pipeuhr.segments — HydraulicCircuit configuration and
evaluation ordering.

evaluation_order() is the backbone that GlobalOptimization.evaluate() walks
to compute velocities, head losses, and pressures segment-by-segment, so an
ordering or auto-generation bug here would silently corrupt every
downstream physical quantity in the optimizer.
"""

from __future__ import annotations

import pytest

from pipeuhr.segments import (
    HydraulicCircuit,
    PipeMaterial,
    PipeSegment,
    PipeType,
    SegmentPosition,
)

pytestmark = pytest.mark.unit


def test_default_circuit_has_three_pipe_segments():
    """The production default circuit (AB, BC, EF) must expose exactly 3
    PipeSegment instances, since GlobalOptimization sizes its decision
    vector (one diameter per pipe) directly from this count.
    """
    # Arrange
    circuit = HydraulicCircuit.default_circuit()

    # Act
    n_pipes = circuit.n_pipe_segments

    # Assert
    assert n_pipes == 3


def test_default_circuit_starts_and_ends_with_auto_tomada_dagua():
    """evaluation_order() must synthesize an automatic water-intake entry at
    the start of the 'Antes' group and another at the end of the 'Depois'
    group, matching the reservoir submergence formulas in
    GlobalOptimization.evaluate().
    """
    # Arrange
    circuit = HydraulicCircuit.default_circuit()

    # Act
    order = circuit.evaluation_order()

    # Assert
    assert order[0]["type"] == "auto"
    assert order[-1]["type"] == "auto"


def test_evaluation_order_preserves_user_segment_sequence_within_group():
    """Within the 'Antes' group, user-configured pipe/diverse segments must
    appear in the exact order they were declared, since head-loss and
    elevation chains are computed cumulatively along that sequence.
    """
    # Arrange
    circuit = HydraulicCircuit.default_circuit()

    # Act
    order = circuit.evaluation_order()
    antes_names = [
        entry["name"]
        for entry in order
        if entry["position"] == SegmentPosition.ANTES and entry["type"] != "auto"
    ]

    # Assert
    assert antes_names == ["AB", "Curva 45", "BC", "Bifurcação casa de força"]


def test_circuit_requires_at_least_one_pipe_before_powerhouse():
    """A circuit with no 'Antes' (discharge-side) pipe is physically
    invalid and must raise ValueError at construction time rather than
    failing obscurely later inside the solver.
    """
    # Arrange
    segments = [
        PipeSegment(
            "EF",
            512.0,
            19.0,
            PipeMaterial.CONCRETO,
            PipeType.SUCCAO,
            SegmentPosition.DEPOIS,
        ),
    ]

    # Act / Assert
    with pytest.raises(ValueError):
        HydraulicCircuit(segments)


def test_circuit_requires_at_least_one_pipe_after_powerhouse():
    """Symmetric to the 'Antes' check: a circuit with no 'Depois'
    (suction-side) pipe must also raise ValueError at construction time.
    """
    # Arrange
    segments = [
        PipeSegment(
            "AB",
            4029.0,
            0.45,
            PipeMaterial.CONCRETO,
            PipeType.BAIXA_PRESSAO,
            SegmentPosition.ANTES,
        ),
    ]

    # Act / Assert
    with pytest.raises(ValueError):
        HydraulicCircuit(segments)


def test_diverse_segment_without_explicit_diameter_inherits_from_pipe():
    """A DiverseSegment with diameter=None (e.g. 'Curva 45') must resolve
    its diameter_key to the adjacent upstream pipe's index, so it inherits
    that pipe's computed diameter during evaluate() instead of needing its
    own decision variable.
    """
    # Arrange
    circuit = HydraulicCircuit.default_circuit()

    # Act
    order = circuit.evaluation_order()
    curva = next(entry for entry in order if entry["name"] == "Curva 45")

    # Assert
    assert curva["diameter_key"] == "pipe:0"
