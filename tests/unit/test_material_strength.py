"""Unit tests for pipeuhr.material_strength — pure, constant-valued lookups.

These tests pin the MPa -> Kgf/m2 conversion factor and the specific
material grades (concrete Class K shotcrete, steel NBR 5590) feeding the
pressure constraint checks in ConstraintSimulator. A silent change to any of
these values would quietly loosen or tighten every pipe-pressure safety
margin computed by the optimizer, without any other test catching it.
"""

from __future__ import annotations

import pytest

from pipeuhr.material_strength import MPA_TO_KGF_M2, MaterialStrength

pytestmark = pytest.mark.unit


def test_concrete_strength_uses_shotcrete_class_k_28mpa():
	"""Concrete strength (point C) must derive from the Class K shotcrete
	record (21 MPa), matching the 'Eletrobras 2003' reference table used by
	the original spreadsheet's pressure constraint on concrete pipes.
	"""
	# Arrange
	strength = MaterialStrength()

	# Act
	value = strength.concrete_strength_kgf_m2

	# Assert
	assert value == pytest.approx(21.0 * MPA_TO_KGF_M2)


def test_steel_strength_uses_205mpa_grade():
	"""Steel strength (point D) must derive from the 205 MPa NBR 5590 / ASTM
	A53 record, matching the spreadsheet's pressure constraint on steel
	pipes.
	"""
	# Arrange
	strength = MaterialStrength()

	# Act
	value = strength.steel_strength_kgf_m2

	# Assert
	assert value == pytest.approx(205.0 * MPA_TO_KGF_M2)


def test_steel_strength_greater_than_concrete_strength():
	"""Property check: steel must always be the stronger material. This
	guards against an accidental swap of the two MaterialRecord instances,
	which would invert every material-based pressure constraint.
	"""
	# Arrange
	strength = MaterialStrength()

	# Act / Assert
	assert strength.steel_strength_kgf_m2 > strength.concrete_strength_kgf_m2


def test_mpa_to_kgf_m2_conversion_factor_is_pinned():
	"""The MPa -> Kgf/m2 factor is a physical constant (1 MPa = 101,971.6
	Kgf/m2). Pin its exact value since every strength value derives from it.
	"""
	# Arrange / Act / Assert
	assert MPA_TO_KGF_M2 == 101971.6
