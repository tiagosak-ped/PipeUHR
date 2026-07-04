"""Unit tests for the dam and equipment cost regression models.

Both DamCostModel and EquipmentCostModel refit a polynomial (via
numpy.polyfit) against a fixed, hardcoded set of real reference plants at
construction time. Because the sample data never changes, these models are
fully deterministic and make fast, reliable unit-test targets even though
they involve a least-squares fit.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeuhr.dam_cost import DamCostModel
from pipeuhr.equipment_cost import EquipmentCostModel

pytestmark = pytest.mark.unit


def test_dam_cost_model_refit_is_deterministic():
	"""Refitting twice from the same hardcoded samples must produce
	identical coefficients — otherwise the optimizer would receive a
	different cost landscape on every process restart, breaking
	reproducibility of optimization results.
	"""
	# Arrange
	first = DamCostModel(refit=True)
	second = DamCostModel(refit=True)

	# Act
	coeffs_first, coeffs_second = first.coeffs, second.coeffs

	# Assert
	assert coeffs_first == pytest.approx(coeffs_second)


def test_dam_cost_model_no_refit_uses_excel_coefficients():
	"""With refit=False, the model must fall back exactly to the original
	Excel Solver coefficients, preserving backward compatibility with the
	legacy spreadsheet results.
	"""
	# Arrange
	model = DamCostModel(refit=False)

	# Act / Assert
	assert model.coeffs == DamCostModel.EXCEL_COEFFS


def test_dam_cost_increases_with_dam_height_in_sample_range():
	"""Cost must increase with dam height over the observed sample range
	(35m-196m) — a basic monotonicity property the optimizer relies on when
	trading dam height off against other decision variables.
	"""
	# Arrange
	model = DamCostModel(refit=True)

	# Act
	cost_low = model.cost(50.0)
	cost_high = model.cost(150.0)

	# Assert
	assert cost_high > cost_low


def test_dam_cost_sum_squared_error_is_finite_and_nonnegative():
	"""The fit's residual sum-of-squares must be a finite, non-negative
	number; a NaN/inf here would indicate a broken polyfit silently
	corrupting every downstream dam-cost calculation.
	"""
	# Arrange
	model = DamCostModel(refit=True)

	# Act
	sse = model.sum_squared_error()

	# Assert
	assert np.isfinite(sse) and sse >= 0


def test_equipment_cost_model_no_refit_uses_excel_coefficients():
	"""With refit=False, EquipmentCostModel must fall back exactly to the
	original Excel Solver coefficients.
	"""
	# Arrange
	model = EquipmentCostModel(refit=False)

	# Act / Assert
	assert model.coeffs == EquipmentCostModel.EXCEL_COEFFS


def test_equipment_cost_increases_with_power_in_sample_range():
	"""Equipment cost must increase with installed power over the observed
	sample range (128MW-3162MW), matching the physical/economic expectation
	that bigger machines cost more.
	"""
	# Arrange
	model = EquipmentCostModel(refit=True)

	# Act
	cost_low = model.cost(200.0)
	cost_high = model.cost(2000.0)

	# Assert
	assert cost_high > cost_low
