# PipeUHR Automated Testing Suite — Strategy & Scaffold

> Implementation plan for a complete, runnable `pytest` test suite covering the
> compute core, the Flask HTTP layer, and a browser smoke E2E, plus a
> `TESTING_GUIDE.md` that enforces a strict test-accompanying workflow in future
> AI sessions.

## Understanding

Design and scaffold a complete, runnable `pytest` test suite for PipeUHR (a
Flask + SciPy engineering optimizer), covering the pure compute core, the Flask
HTTP layer, and a browser smoke E2E, plus a `TESTING_GUIDE.md` that forces future
AI sessions into a strict test-accompanying workflow.

## Assumptions

- **No database exists**; persistence is filesystem JSON under
  `webapp/data/templates/`. Tests isolate this via `tmp_path` + `monkeypatch` of
  the module global `TEMPLATES_DIR`. SQLite `:memory:` is documented only as a
  forward-looking placeholder.
- `webapp/app.py` is a script (no app factory, no `webapp/__init__.py`). Tests
  import it by file path via `importlib.util` to avoid the generic module-name
  clash and to reuse its existing `sys.path` bootstrap.
- The compute core (`pipeuhr/`) is pure Python/NumPy/SciPy and is the
  highest-value, fastest unit-test target.
- SLSQP `solve()` is slow/heavy → those tests are marked `slow`; the browser E2E
  is marked `e2e` and skipped gracefully when Playwright/browsers are absent, so
  the default suite stays green.
- We do **not** refactor `app.py`; testability is achieved through
  fixtures/monkeypatching only (minimal change).

## Approach

Adopt a layered pyramid.

- **Backend unit (broad base):** target deterministic core classes in
  [pipeuhr/material_strength.py](pipeuhr/material_strength.py),
  [pipeuhr/aux_data.py](pipeuhr/aux_data.py),
  [pipeuhr/dam_cost.py](pipeuhr/dam_cost.py),
  [pipeuhr/equipment_cost.py](pipeuhr/equipment_cost.py), and
  [pipeuhr/segments.py](pipeuhr/segments.py) with fast exact/property assertions.
- **Integration (middle):** drive [webapp/app.py](webapp/app.py) through Flask
  `test_client` — `GET /` renders the form, `POST /solve` returns a results page,
  and the `/templates/*` JSON CRUD round-trips against an isolated temp directory.
- **Solver (focused, marked `slow`):** one module asserts feasibility/constraint
  properties of `GlobalOptimization.solve()` + `ConstraintSimulator.simulate()`;
  a separate module pins a numeric regression baseline with `pytest.approx`.
- **E2E (tip, marked `e2e`):** a single Playwright smoke test loads `/`, submits
  the form, and verifies the results page renders, run against a live server
  started in a fixture.

Shared fixtures live in `tests/conftest.py`; markers (`unit`, `integration`,
`slow`, `e2e`) and `testpaths`/coverage `addopts` live in `pytest.ini`. Dev
dependencies are pinned in `requirements-dev.txt`.

## Alternatives Considered (recommendation before scaffolding)

| Area | Options | Recommendation | Why |
|------|---------|----------------|-----|
| **Test runner / coverage** | pytest + pytest-cov · unittest · nose2 | **pytest + pytest-cov** | Fixtures, parametrization, minimal boilerplate, native coverage integration. unittest is verbose with no native fixtures; nose2 is largely legacy. |
| **Flask layer** | `test_client` · live-server + requests · pytest-flask | **`test_client`** | In-process, fast, deterministic, full request context — no sockets/flakiness. live-server is realistic but slow/flaky; pytest-flask adds a dep for little gain here. |
| **Frontend E2E** | Playwright · Selenium · Cypress | **Playwright** (1 smoke) | Auto-waiting, Python-native, easy CI install. Selenium is flakier with manual waits; Cypress is JS-only and off-stack. |
| **Persistence isolation** | `tmp_path` + monkeypatch · SQLite `:memory:` | **`tmp_path` + monkeypatch** | Matches the *real* JSON store; `:memory:` documented as a forward-looking placeholder for future DB work. |
| **Solver assertions** | property/constraint · numeric regression | **Both, separate modules** | Property tests robustly catch infeasibility; regression pins numeric drift with `pytest.approx`. |

## Recommended Suite Layout (test pyramid)

```text
tests/
  unit/         # fast, deterministic core: material_strength, aux_data, cost models, segments
  integration/  # Flask test_client: GET /, POST /solve, /templates CRUD (isolated dir)
  solver/       # [slow] property/feasibility  +  [slow] numeric regression (pytest.approx)
  e2e/          # [e2e] one Playwright browser smoke (skip-guarded, live-server fixture)
  conftest.py   # app-by-path import, client, isolated TEMPLATES_DIR, sample model
pytest.ini · requirements-dev.txt · TESTING_GUIDE.md
```

## Key Files

- `tests/conftest.py` — shared fixtures: import app by path, `client`, isolated
  `TEMPLATES_DIR`, fast sample model.
- `pytest.ini` — markers, `testpaths`, `--strict-markers`, coverage `addopts`.
- `requirements-dev.txt` — pytest, pytest-cov, pytest-playwright.
- `tests/unit/*` — fast deterministic core tests (material strength, aux data,
  cost models, segments).
- `tests/integration/test_app_routes.py` — `test_client` route + template-CRUD
  tests.
- `tests/solver/test_solver_properties.py` + `tests/solver/test_solver_regression.py`
  — `slow` solver feasibility + numeric baseline.
- `tests/e2e/test_smoke_playwright.py` — `e2e` browser smoke with live-server
  fixture + skip guard.
- `TESTING_GUIDE.md` — AI test-accompanying enforcement doc (AAA, docstrings,
  markers, commands, SQLite `:memory:` placeholder).

## Risks & Open Questions

- Importing `webapp/app.py` (generic name, no package): mitigated via
  `importlib.util.spec_from_file_location`.
- SLSQP runtime/determinism could make regression brittle: use `pytest.approx`
  with sensible rel tolerance and fixed `x0`/`maxiter`; isolate in a `slow`
  module.
- Playwright browser binaries may be absent in CI/local: skip-guard the E2E so
  default runs stay green; document `playwright install`.
- `app.py` module-global `TEMPLATES_DIR` must be patched on the imported module
  object (not a copy) for isolation to take effect.

## Deliverables Produced on Execution

1. **Strategy plan** — encoded in the steps below + the rationale above.
2. **Code blueprints** — real, passing tests per layer (unit, `test_client`
   integration, Playwright E2E) with AAA structure and explanatory docstrings.
3. **`TESTING_GUIDE.md`** — strict test-accompanying AI enforcement doc (markers,
   AAA, docstrings, run commands, SQLite `:memory:` placeholder for future DB
   work).

## Steps

> Status legend: ✅ Completed · 🔄 In progress · ⬜ Pending

1. ✅ **Inventory core and Flask APIs to ground assertions** — read
   `global_optimization.py`, `constraint_simulator.py`, `segments.py`,
   `dam_cost.py`, `equipment_cost.py`, `material_strength.py`, `aux_data.py` for
   exact attributes/return types.
2. ✅ **Create the `tests/` package tree** (`unit/`, `integration/`, `solver/`,
   `e2e/` with `__init__.py`) and add `pytest.ini` with markers (`unit`,
   `integration`, `slow`, `e2e`), `testpaths`, `--strict-markers`, and coverage
   `addopts`.
3. ✅ **Create `requirements-dev.txt`** pinning `pytest`, `pytest-cov`, and
   `pytest-playwright`.
4. ✅ **Write `tests/conftest.py`** with shared fixtures: import `webapp/app.py` by
   file path, `app`/`client` fixtures, isolated `TEMPLATES_DIR` via `tmp_path` +
   `monkeypatch`, and a fast sample-model factory.
5. ✅ **Implement unit tests** for the pure compute modules (material strength, aux
   data, dam/equipment cost models, segments/circuit) using AAA + explanatory
   docstrings.
6. ✅ **Implement Flask integration tests** via `test_client` — `GET /` form render,
   `POST /solve` results render, and `/templates/save|load|list` round-trip
   against the isolated directory.
7. ✅ **Implement solver property/constraint-based tests** (feasibility, positive
   costs, ratio bounds, constraint slack) marked `slow`.
8. ✅ **Implement solver numeric-regression tests** pinning a captured baseline with
   `pytest.approx` tolerances, marked `slow`.
9. ✅ **Implement the Playwright browser smoke E2E** (live-server fixture + graceful
   skip guard) marked `e2e`.
10. ✅ **Author `TESTING_GUIDE.md`** (test-accompanying AI rules, AAA, docstrings,
	marker/run commands, SQLite `:memory:` forward-looking placeholder), then
	install dev deps and run the fast suite with coverage to confirm green.
