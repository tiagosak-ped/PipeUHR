# PipeUHR — Product Definition

## Vision

PipeUHR is an engineering optimization tool for **Reversible Hydroelectric Power Plants** (Usinas Hidrelétricas Reversíveis). It migrates a legacy spreadsheet-based workflow into a modern, reproducible Python stack (NumPy, SciPy, Flask), enabling researchers and engineers to iterate on design parameters with immediate solver feedback and constraint verification.

## Core Functionalities

| Feature | Description |
|---------|-------------|
| **Parameter Input** | Structured form with grouped engineering parameters (reservoirs, operations, piping, elevations, unit costs, cavitation, constraints). |
| **Constrained Optimization** | SciPy SLSQP solver minimizes total cost (CT) subject to physical and regulatory constraints. |
| **Constraint Verification** | Post-solve simulation validates all inequality constraints and reports slack values, operator compliance, and violation counts. |
| **Results Dashboard** | Displays optimized decision variables, cost composition breakdown, and constraint satisfaction status with numeric precision. |

## How to Use

1. Launch the Flask server: `py webapp/app.py`
2. Open `http://127.0.0.1:5000` in a browser.
3. Review or adjust the engineering parameters organized by category (Reservatórios, Operação, Tubulação, Cotas, Custos unitários, Cavitação, Restrições).
4. Click **Otimizar** to execute the solver.
5. Analyze the results: total cost, decision variables, cost breakdown, and constraint verification table.

## Target Users

- **Hydraulic Engineers** designing pump-turbine systems for reversible hydroelectric plants.
- **R&D Researchers** evaluating cost sensitivity across design parameter variations.
- **Project Managers** reviewing optimization feasibility and constraint compliance for formal deliverables.

## Technical Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Solver | SciPy (SLSQP), NumPy |
| Frontend | Tailwind CSS, DaisyUI, Jinja2 templates |
| Deployment | Local development server (expandable) |

## Testing

PipeUHR ships with a full `pytest` suite (unit, Flask integration, solver
property/regression, and one Playwright browser E2E). Rules for *writing*
tests live in [TESTING_GUIDE.md](TESTING_GUIDE.md); this section is a
step-by-step **execution walkthrough** — follow it verbatim the first time
you set up the project, or whenever you need to run a specific layer.

### 0. One-time environment setup

Open a PowerShell terminal at the repository root (`C:\PipeUHR\`) and
install the development/test dependencies. This single file also pulls in
the runtime requirements (`numpy`, `scipy`, `openpyxl`, `flask`), so a fresh
virtual environment only needs this one command:

```powershell
cd C:\PipeUHR
py -m pip install -r requirements-dev.txt
```

Expected output ends with a line similar to:

```text
Successfully installed flask-3.x ... pytest-9.x pytest-cov-7.x pytest-playwright-0.x ...
```

The E2E layer additionally needs a real browser binary (only Chromium is
used). Install it once per machine:

```powershell
py -m playwright install chromium
```

This downloads Chrome for Testing, a headless-shell build, and small
support tools (FFmpeg, Winldd) into
`C:\Users\<you>\AppData\Local\ms-playwright\`. It only needs to be repeated
if that cache is cleared or you switch machines. If you skip this step, the
E2E tests do **not** fail — they self-skip with a clear message (see
Section 5).

### 1. Run the unit tests (`tests/unit/`)

These are the fastest, most numerous tests — pure Python/NumPy checks
against `pipeuhr/material_strength.py`, `pipeuhr/aux_data.py`,
`pipeuhr/dam_cost.py`, `pipeuhr/equipment_cost.py`, and
`pipeuhr/segments.py`. No Flask, no solver, no filesystem I/O.

```powershell
py -m pytest tests/unit -v --no-cov
```

- `-v` prints one line per test (readable pass/fail list).
- `--no-cov` skips the coverage report for a quicker, less noisy run — use
  this flag whenever you only care about pass/fail, not coverage.

Expected output (illustrative — exact timing varies by machine):

```text
tests/unit/test_material_strength.py::test_concrete_strength_returns_expected_kgf_m2 PASSED
tests/unit/test_material_strength.py::test_steel_strength_returns_expected_kgf_m2 PASSED
...
tests/unit/test_segments.py::test_diverse_segment_without_explicit_diameter_inherits_from_pipe PASSED
======================== 25 passed in 12.87s ========================
```

If a test fails here, the bug is almost certainly in a pure calculation
(a constant, a lookup table, a polynomial fit, or circuit/segment ordering
logic) — start by reading the failing test's docstring, which states *why*
the behavior matters.

### 2. Run the Flask integration tests (`tests/integration/`)

These drive the real `webapp/app.py` routes through Flask's in-process
`test_client` (no real network socket): the parameter form (`GET /`), the
solve pipeline (`POST /solve`), and the JSON template CRUD endpoints
(`/templates/list|save|load`). Persistence is isolated to a temporary
directory automatically (see `isolated_templates_dir` in
`tests/conftest.py`) — these tests never touch the real
`webapp/data/templates/` folder.

```powershell
py -m pytest tests/integration -v --no-cov --durations=10
```

- `--durations=10` prints the 10 slowest test setup/call phases at the end
  — useful for spotting an accidentally slow test in this layer, which
  should otherwise be sub-second.

Expected output:

```text
tests/integration/test_app_routes.py::test_index_renders_parameter_form PASSED
tests/integration/test_app_routes.py::test_index_contains_optimize_button PASSED
tests/integration/test_app_routes.py::test_solve_with_default_parameters_renders_results_page PASSED
tests/integration/test_app_routes.py::test_solve_accepts_comma_decimal_input PASSED
tests/integration/test_app_routes.py::test_templates_list_is_empty_for_fresh_isolated_directory PASSED
tests/integration/test_app_routes.py::test_templates_save_then_list_round_trip PASSED
tests/integration/test_app_routes.py::test_templates_save_then_load_round_trip PASSED
tests/integration/test_app_routes.py::test_templates_load_missing_slug_returns_404 PASSED
tests/integration/test_app_routes.py::test_templates_save_does_not_touch_real_data_directory PASSED
======================== 9 passed in 1.73s ========================
```

If a test fails here, check whether a Flask route signature, a template's
rendered text (e.g. the Portuguese headings asserted against), or the
`TEMPLATES_DIR` JSON contract changed.

### 3. Run the solver tests (`tests/solver/`) — marked `slow`

This layer invokes the real SciPy SLSQP solver
(`GlobalOptimization.solve()`) — numerically heavier than the layers above,
so it is marked `slow` and excluded from the default fast loop (see
Section 6). It has two files with different jobs:

- `test_solver_properties.py` — feasibility/property assertions (the
  solution converges, every constraint is satisfied, all costs are
  positive, velocities/heights/ratios stay within bounds). Robust to minor,
  legitimate numeric drift.
- `test_solver_regression.py` — a numeric baseline (decision vector, cost
  breakdown, power/hydraulic metrics) pinned with `pytest.approx(rel=1e-4)`,
  plus a determinism check (two `solve()` calls on the same model produce
  identical results).

```powershell
py -m pytest tests/solver -v --no-cov --durations=10
```

Expected output:

```text
tests/solver/test_solver_properties.py::test_default_solve_reports_success PASSED
tests/solver/test_solver_properties.py::test_default_solve_satisfies_every_constraint PASSED
tests/solver/test_solver_properties.py::test_default_solve_costs_are_positive[cost_dam_sup] PASSED
...
tests/solver/test_solver_regression.py::test_default_solve_is_deterministic_across_repeated_runs PASSED
======================== 22 passed in 1.48s ========================
```

If `test_solver_regression.py` fails unexpectedly, treat it as a
**regression signal first** — something in a cost formula, a constraint
bound, or the solver's configuration changed. Only update the `BASELINE_*`
constants in that file when the change is intentional, and explain why (see
`TESTING_GUIDE.md` §7, rule 4).

### 4. Run the browser E2E smoke test (`tests/e2e/`) — marked `e2e`

This is the single test that proves the *entire* stack works together in a
real browser: it starts the real Flask app on a real local socket
(`live_server` fixture), opens it with Playwright Chromium, clicks
**Otimizar** with the default form values, and asserts the results page
("Resultado da otimização") renders.

```powershell
py -m pytest tests/e2e -v --no-cov
```

Expected output (dominated by real browser + solver + page-render time):

```text
tests/e2e/test_smoke_playwright.py::test_user_can_submit_default_form_and_see_results PASSED
======================== 1 passed in ~9-31s ========================
```

If Chromium was never installed (Section 0 skipped), you will instead see:

```text
tests/e2e/test_smoke_playwright.py::test_user_can_submit_default_form_and_see_results SKIPPED
(playwright package not installed; ...)  # or: Playwright Chromium browser not installed (...)
```

This is expected, graceful behavior — it is **not** a failure, and it never
blocks the default fast suite (Section 6) from being green.

### 5. Run everything at once, with coverage

The full suite (all four layers, with the terminal coverage report that
`pytest.ini` enables by default) is a single command:

```powershell
py -m pytest
```

This targets both `pipeuhr` and `webapp` for coverage
(`--cov=pipeuhr --cov=webapp --cov-report=term-missing`, configured in
[pytest.ini](pytest.ini)) and prints a per-module breakdown at the end,
e.g.:

```text
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
pipeuhr\material_strength.py         23      0   100%
pipeuhr\dam_cost.py                  24      0   100%
pipeuhr\global_optimization.py      262      7    97%   110, 220-222, ...
webapp\app.py                       127     14    89%   67, 77, 170-190, ...
---------------------------------------------------------------
TOTAL                               811     67    92%
======================== 57 passed in ~9s ========================
```

Use the `Missing` column to find untested line ranges — but treat it as a
prompt to investigate, not a score to chase (see `TESTING_GUIDE.md` §8).

### 6. Day-to-day: the fast default loop

While actively developing, you rarely want to pay for the solver or a
browser on every save. Run only the fast, deterministic layers (unit +
integration) using the `slow`/`e2e` markers declared in `pytest.ini`:

```powershell
py -m pytest -m "not slow and not e2e"
```

Expected output:

```text
======================== 34 passed, 23 deselected in ~13s ========================
```

Before committing or opening a PR, additionally run the solver layer (still
excluding the browser, which only needs to pass when UI-reachable behavior
changed — see `TESTING_GUIDE.md` §7):

```powershell
py -m pytest -m "not e2e"
```

Expected output:

```text
======================== 56 passed, 1 deselected in ~2s ========================
```

### 7. Running a single file, test, or marker directly

```powershell
# One file
py -m pytest tests/unit/test_segments.py -v --no-cov

# One test by name (substring match)
py -m pytest -k test_default_solve_satisfies_every_constraint -v --no-cov

# Everything tagged with a given marker
py -m pytest -m unit -v --no-cov
```

### Quick reference

| Goal | Command |
|---|---|
| Install test toolchain (once) | `py -m pip install -r requirements-dev.txt` |
| Install E2E browser (once) | `py -m playwright install chromium` |
| Fast loop while coding | `py -m pytest -m "not slow and not e2e"` |
| Include solver, exclude browser | `py -m pytest -m "not e2e"` |
| Browser smoke only | `py -m pytest tests/e2e` |
| Everything + coverage | `py -m pytest` |
| One file, no coverage noise | `py -m pytest <path> -v --no-cov` |

## Project Context

This software is a formal deliverable of an R&D project (P&D ANEEL). The interface must reflect institutional quality: professional, understated, and optimized for data readability by technical reviewers.
