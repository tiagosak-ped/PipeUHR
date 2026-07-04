"""Numeric-regression tests for GlobalOptimization.solve() against a pinned
baseline captured from the current, correct implementation.

Unlike test_solver_properties.py (which checks generic feasibility
properties), these tests pin *specific* numeric outputs of the default
circuit solve. Their purpose is to catch silent, unintended changes to the
physics/cost formulas or to the solver configuration (x0, bounds, maxiter)
that a property-based test could miss because the new numbers might still
happen to remain feasible.

Baseline captured with: GlobalOptimization().solve(maxiter=500), on the
production default circuit
(pipeuhr.segments.HydraulicCircuit.default_circuit(), i.e. pipes AB/BC/EF).
Tolerances use pytest.approx with a small relative tolerance to absorb
negligible floating-point/platform differences in SciPy's SLSQP without
masking real regressions.
"""

from __future__ import annotations

import pytest

from pipeuhr import GlobalOptimization

pytestmark = pytest.mark.slow

# Captured baseline — see module docstring for how/when this was produced.
# Decision vector x = [h1, h2, D_AB, D_BC, D_EF, hours_pump].
BASELINE_X = [
	149.9999999999903,
	85.62693167530905,
	6.216813383398514,
	5.707216829607364,
	5.619965013729266,
	15.071861543173084,
]
BASELINE_COST_TOTAL = 6176.666789958524
BASELINE_COST_DAM_SUP = 2838.9844042262994
BASELINE_COST_DAM_INF = 1584.7222903415322
BASELINE_COST_POWERHOUSE = 1245.4007369106578
BASELINE_COST_LOW_PRESSURE = 410.93796983906134
BASELINE_COST_HIGH_PRESSURE = 96.62138864097365
BASELINE_POWER_TURBINE = 207.9636570271843
BASELINE_POWER_RATIO = 1.1000000000000523
BASELINE_HOURS_TURB = 6.928138456826916
BASELINE_NPSH_RATIO = 1.1499999999998538
BASELINE_HEAD_LOSS_TOTAL = 12.397163476084181

REL_TOLERANCE = 1e-4


def test_default_solve_decision_vector_matches_baseline(solved_default_result):
	"""The full decision vector [h1, h2, D_AB, D_BC, D_EF, hours_pump] must
	match the pinned baseline within a tight relative tolerance — the most
	direct signal of a silent change anywhere in the model.
	"""
	_model, result = solved_default_result

	assert list(result.x) == pytest.approx(BASELINE_X, rel=REL_TOLERANCE)


def test_default_solve_cost_total_matches_baseline(solved_default_result):
	"""The total cost (CT) must match the pinned baseline (~6176.67 million
	R$) within tolerance — the single headline number the optimizer exists
	to minimize.
	"""
	_model, result = solved_default_result

	assert result.state.cost_total == pytest.approx(BASELINE_COST_TOTAL, rel=REL_TOLERANCE)


def test_default_solve_cost_breakdown_matches_baseline(solved_default_result):
	"""Every individual cost component (C1..C5) must match its pinned
	baseline value, catching regressions localized to a single cost
	formula that a total-only check could mask (e.g. C1 up, C2 down by a
	compensating amount).
	"""
	_model, result = solved_default_result
	st = result.state

	assert st.cost_dam_sup == pytest.approx(BASELINE_COST_DAM_SUP, rel=REL_TOLERANCE)
	assert st.cost_dam_inf == pytest.approx(BASELINE_COST_DAM_INF, rel=REL_TOLERANCE)
	assert st.cost_powerhouse == pytest.approx(BASELINE_COST_POWERHOUSE, rel=REL_TOLERANCE)
	assert st.cost_low_pressure == pytest.approx(BASELINE_COST_LOW_PRESSURE, rel=REL_TOLERANCE)
	assert st.cost_high_pressure == pytest.approx(BASELINE_COST_HIGH_PRESSURE, rel=REL_TOLERANCE)


def test_default_solve_power_and_operation_metrics_match_baseline(solved_default_result):
	"""Turbine power, power ratio, and daily turbine hours must match their
	pinned baselines, since these drive the equipment-cost and
	power-ratio/turbine-hours constraint calculations.
	"""
	_model, result = solved_default_result
	st = result.state

	assert st.power_turbine == pytest.approx(BASELINE_POWER_TURBINE, rel=REL_TOLERANCE)
	assert st.power_ratio == pytest.approx(BASELINE_POWER_RATIO, rel=REL_TOLERANCE)
	assert st.hours_turb == pytest.approx(BASELINE_HOURS_TURB, rel=REL_TOLERANCE)


def test_default_solve_hydraulic_metrics_match_baseline(solved_default_result):
	"""NPSH ratio and total head loss must match their pinned baselines,
	since these drive the cavitation and head-loss safety constraints.
	"""
	_model, result = solved_default_result
	st = result.state

	assert st.npsh_ratio == pytest.approx(BASELINE_NPSH_RATIO, rel=REL_TOLERANCE)
	assert st.head_loss_total == pytest.approx(BASELINE_HEAD_LOSS_TOTAL, rel=REL_TOLERANCE)


def test_default_solve_is_deterministic_across_repeated_runs():
	"""Re-solving the exact same default-circuit model from scratch must
	reproduce the identical decision vector, proving solve() has no hidden
	randomness/non-determinism (e.g. an unseeded random x0) that would make
	the numeric-regression baselines above inherently unreliable.
	"""
	# Arrange
	model = GlobalOptimization()

	# Act
	first = model.solve(maxiter=500)
	second = model.solve(maxiter=500)

	# Assert
	assert list(first.x) == pytest.approx(list(second.x), rel=1e-9)
