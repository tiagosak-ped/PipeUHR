"""Solver property/constraint-based tests for GlobalOptimization.solve().

These tests exercise the actual SciPy SLSQP solve() pipeline end-to-end,
verifying feasibility properties of the returned solution (all constraints
satisfied, positive costs, decision variables within bounds) rather than
pinning exact numeric outputs (see test_solver_regression.py for that).
They are marked `slow` because they run real, numerically expensive
optimization passes instead of relying only on pure/fast fixtures.
"""

from __future__ import annotations

import pytest

from pipeuhr import (
	ConstraintSimulator,
	GlobalOptimization,
	HydraulicCircuit,
	PipeMaterial,
	PipeSegment,
	PipeType,
	SegmentPosition,
)

pytestmark = pytest.mark.slow


def test_default_solve_reports_success(solved_default_result):
	"""solve() on the production default circuit must converge
	successfully (SLSQP reports success=True), since a failed solve would
	mean the web UI silently serves an infeasible/non-optimal result.
	"""
	_model, result = solved_default_result
	assert result.success is True


def test_default_solve_satisfies_every_constraint(solved_default_result):
	"""The solved state must satisfy every constraint checked by
	ConstraintSimulator (velocities, head loss, pressures, NPSH, power
	ratio, dam heights, minimum power and turbine hours) — this is the
	single most important feasibility property of the whole model.
	"""
	model, result = solved_default_result

	report = ConstraintSimulator(model).simulate(result)

	assert report.all_satisfied, f"Violations: {report.violations()}"


@pytest.mark.parametrize(
	"cost_attr",
	["cost_dam_sup", "cost_dam_inf", "cost_powerhouse",
	 "cost_low_pressure", "cost_high_pressure", "cost_total"],
)
def test_default_solve_costs_are_positive(solved_default_result, cost_attr):
	"""Every individual cost component (C1..C5) and the total (CT) must be
	strictly positive — a zero or negative cost would indicate a broken
	cost model formula silently producing physically meaningless results.
	"""
	_model, result = solved_default_result

	assert getattr(result.state, cost_attr) > 0


def test_default_solve_cost_components_sum_to_total(solved_default_result):
	"""cost_total (CT) must equal the sum of its five components (C1..C5),
	the same invariant computed by GlobalOptimization.evaluate().
	"""
	_model, result = solved_default_result
	st = result.state

	component_sum = (
		st.cost_dam_sup + st.cost_dam_inf + st.cost_powerhouse
		+ st.cost_low_pressure + st.cost_high_pressure
	)

	assert st.cost_total == pytest.approx(component_sum)


def test_default_solve_power_ratio_within_bounds(solved_default_result):
	"""Pturb/Pbomb must fall within [RATIO_MIN, RATIO_MAX] (0.85-1.1), the
	same bounds enforced by the c_ratio_min/c_ratio_max constraints.
	"""
	model, result = solved_default_result

	assert model.RATIO_MIN - 1e-6 <= result.state.power_ratio <= model.RATIO_MAX + 1e-6


def test_default_solve_dam_heights_within_global_bounds(solved_default_result):
	"""Both dam heights (h1, h2) must stay within (0, DAM_HEIGHT_MAX],
	since exceeding the maximum would violate a hard engineering safety
	limit the solver is meant to respect.
	"""
	model, result = solved_default_result
	st = result.state

	assert 0 < st.h1 <= model.DAM_HEIGHT_MAX + 1e-6
	assert 0 < st.h2 <= model.DAM_HEIGHT_MAX + 1e-6


def test_default_solve_pipe_velocities_within_material_bounds(solved_default_result):
	"""Every pipe's flow velocity must respect its material's maximum
	(concrete 7 m/s, steel 8 m/s) and the global minimum (2 m/s) — violating
	either would mean the solver returned an infeasible design.
	"""
	model, result = solved_default_result

	for ps in result.state.pipe_states():
		v_max = (model.V_MAX_STEEL if ps.material == PipeMaterial.ACO.value
				  else model.V_MAX_CONCRETE)
		assert model.V_MIN - 1e-6 <= ps.velocity <= v_max + 1e-6


def test_default_solve_head_loss_within_max_fraction(solved_default_result):
	"""Total head loss must not exceed HEAD_LOSS_MAX_FRAC (4%) of gross
	turbine head, the same limit the c_head_loss constraint enforces.
	"""
	model, result = solved_default_result
	st = result.state

	frac = st.head_loss_total / st.head_gross_turb
	assert frac <= model.HEAD_LOSS_MAX_FRAC + 1e-6


def test_default_solve_npsh_ratio_meets_safety_factor(solved_default_result):
	"""The available/required NPSH ratio must meet or exceed
	NPSH_SAFETY_FACTOR (1.15) to guarantee the pump design avoids
	cavitation, matching the c_npsh constraint.
	"""
	model, result = solved_default_result

	assert result.state.npsh_ratio >= model.NPSH_SAFETY_FACTOR - 1e-6


def test_default_solve_hours_turb_meets_minimum(solved_default_result):
	"""Daily turbine operating hours must meet HOURS_TURB_MIN (6h), the
	same limit enforced by the c_hours_turb constraint.
	"""
	model, result = solved_default_result

	assert result.state.hours_turb >= model.HOURS_TURB_MIN - 1e-6


def test_solve_converges_and_is_feasible_for_a_custom_two_pipe_circuit():
	"""The solver's feasibility guarantees must generalize beyond the
	hardcoded 3-pipe default circuit: a custom, smaller 2-pipe circuit must
	also converge successfully and satisfy every constraint, proving the
	dynamic-N-segments design (not just the legacy 3-pipe path) is sound.
	"""
	# Arrange
	circuit = HydraulicCircuit([
		PipeSegment("A", 1000.0, 10.0, PipeMaterial.ACO,
					PipeType.ALTA_PRESSAO, SegmentPosition.ANTES),
		PipeSegment("B", 500.0, 10.0, PipeMaterial.CONCRETO,
					PipeType.SUCCAO, SegmentPosition.DEPOIS),
	])
	model = GlobalOptimization(circuit=circuit)

	# Act
	result = model.solve(maxiter=500)
	report = ConstraintSimulator(model).simulate(result)

	# Assert
	assert result.success is True
	assert report.all_satisfied, f"Violations: {report.violations()}"
