# PipeUHR — Testing Guide

> Audience: any human or AI coding agent making changes to this repository.
> Purpose: keep PipeUHR's test suite trustworthy, fast by default, and
> **mandatory to update whenever behavior changes** — not an afterthought.

This document is the enforcement contract for testing in PipeUHR. If you are
an AI coding agent (or a human) about to add or change code in `pipeuhr/` or
`webapp/`, read the **Rules for Changing Code** section before you start, and
follow the **Definition of Done** checklist before you consider the task
finished.

## 1. Philosophy

PipeUHR has no manual QA step and no staging environment — the test suite
*is* the safety net for an engineering optimizer whose outputs (pipe
diameters, dam heights, costs) feed real project decisions. A regression
here is not a cosmetic bug; it can silently produce an infeasible or
mis-costed design. Consequently:

- **Every behavior change must be accompanied by a test change** in the same
  turn/commit — not deferred to "later".
- Tests must be **simple** (Arrange-Act-Assert, one behavior per test) over
  clever, and **fast by default** (the default `pytest` run must stay green
  and quick; expensive tests are explicitly marked and opt-in).
- Prefer testing **through public APIs** (`GlobalOptimization`, Flask routes)
  over reaching into private internals.

## 2. Suite Layout (test pyramid)

```text
tests/
  unit/         # fast, deterministic: material_strength, aux_data, cost models, segments
  integration/  # Flask test_client: GET /, POST /solve, /templates CRUD (isolated dir)
  solver/       # [slow] property/feasibility  +  [slow] numeric regression (pytest.approx)
  e2e/          # [e2e] one Playwright browser smoke (skip-guarded, live-server fixture)
  conftest.py       # shared: app-by-path import, client, isolated TEMPLATES_DIR, sample model
  e2e/conftest.py   # e2e-only: live_server (real socket) + browser_page (Playwright, skip-guarded)
pytest.ini            # markers, testpaths, --strict-markers, coverage addopts
requirements-dev.txt  # pytest, pytest-cov, pytest-playwright
```

| Layer | What it tests | Speed | Marker |
|---|---|---|---|
| `unit/` | Pure compute: constants, lookup tables, polynomial cost models, circuit/segment ordering. No Flask, no solver. | Milliseconds | `unit` |
| `integration/` | Flask routes end-to-end via `test_client` (in-process, no real socket): form render, `/solve`, `/templates/*` JSON CRUD. | Sub-second | `integration` |
| `solver/` | Real `GlobalOptimization.solve()` (SciPy SLSQP) — feasibility properties in one module, a pinned numeric baseline in another. | ~0.1–1s per test | `slow` |
| `e2e/` | One real-browser smoke test via Playwright against a live Werkzeug server. | Seconds (browser startup dominates) | `e2e` |

Why this shape: the compute core (`pipeuhr/`) is pure Python/NumPy/SciPy and
is the cheapest, highest-value place to put most assertions (wide base of
the pyramid). The Flask layer is thin glue, so it gets fewer, focused
integration tests. The solver is correct-by-construction *if* the model is
right, so it gets targeted feasibility + regression coverage instead of
exhaustive cases. Exactly one browser test exists — it exists only to prove
the full stack wires together, not to re-verify logic already covered
below it.

## 3. Markers & Running the Suite

Declared in [pytest.ini](pytest.ini): `unit`, `integration`, `slow`, `e2e`.
`--strict-markers` is enabled, so a typo'd `@pytest.mark.*` fails loudly
instead of being silently ignored — always reuse one of these four markers.

```powershell
# Install the dev/test toolchain (once per environment)
py -m pip install -r requirements-dev.txt

# Fast default suite (unit + integration) — this is what should stay green
# on every change, and is what CI should run on every push.
py -m pytest -m "not slow and not e2e"

# Everything, including the SLSQP solver tests
py -m pytest -m "not e2e"

# Solver-only (feasibility + numeric regression)
py -m pytest tests/solver

# Browser E2E (requires `py -m playwright install chromium` once)
py -m pytest tests/e2e

# Full suite with coverage (coverage addopts are already in pytest.ini)
py -m pytest

# One file/test, verbose, no coverage noise
py -m pytest tests/unit/test_segments.py -v --no-cov
```

If Playwright's Chromium binary isn't installed locally, `tests/e2e/`
fixtures call `pytest.skip(...)` with an actionable message rather than
erroring — the default suite (`-m "not slow and not e2e"`) never depends on
a browser being present.

## 4. Fixtures Reference (`tests/conftest.py`)

| Fixture | Scope | Provides |
|---|---|---|
| `webapp_app_module` | session | `webapp/app.py` imported by file path (it's a script, not a package — see §6). |
| `isolated_templates_dir` | function | A `tmp_path` directory monkeypatched over the module-global `TEMPLATES_DIR`, so template CRUD tests never touch `webapp/data/templates/`. |
| `flask_app` | function | The real `Flask` app with `TESTING=True` and an isolated template dir. |
| `client` | function | `flask_app.test_client()` — use this for all `integration/` tests. |
| `default_model` | function | A fresh `GlobalOptimization()` on the production default circuit (cheap — construction/`evaluate()` is fast; only `.solve()` is expensive). |
| `solved_default_result` | session | `(model, result)` from one shared `GlobalOptimization().solve(maxiter=500)` call, reused by both `solver/` modules to avoid paying SLSQP's cost twice. |

`tests/e2e/conftest.py` adds two more, scoped to that layer only so other
layers never pay their cost:

| Fixture | Provides |
|---|---|
| `live_server` | The real Flask app served on a real `127.0.0.1` socket (via `werkzeug.serving.make_server`) on a background thread — required because a real browser cannot speak to the in-process `test_client`. |
| `browser_page` | A Playwright Chromium `Page`, or a graceful `pytest.skip(...)` if Playwright/Chromium isn't installed. |

## 5. Writing a New Test — Required Conventions

1. **Arrange / Act / Assert**, separated by blank lines and (for anything
   non-obvious) `# Arrange`, `# Act`, `# Assert` comments — see any file in
   `tests/unit/` for the pattern.
2. **Every test function has a docstring** explaining *why* the behavior
   matters, not just what it checks. One sentence of "what" plus one clause
   of "why" is enough. Reviewers (and future AI agents) should be able to
   understand the intent without reading the implementation.
3. **One behavior per test.** Prefer several small, obviously-named tests
   over one test with many unrelated assertions.
4. **Name tests for the behavior**, e.g.
   `test_default_solve_satisfies_every_constraint`, not `test_solve_2`.
5. **Never mutate shared/session fixtures.** `solved_default_result` and
   `webapp_app_module` are session-scoped for speed — treat their return
   values as read-only.
6. **Mark appropriately**: anything invoking `GlobalOptimization.solve()`
   gets `slow`; anything driving a real browser gets `e2e`; everything else
   should be fast enough to need no marker beyond `unit`/`integration`.
7. **Assert on behavior, not implementation.** Prefer public attributes
   (`result.state.cost_total`, `response.status_code`) over private helpers.

## 6. Project-Specific Testing Notes

- **`webapp/app.py` is a script, not a package** — there is no
  `webapp/__init__.py`, so `import app` / `from webapp import app` won't
  resolve reliably and `app` is too generic a name to safely register in
  `sys.modules`. `tests/conftest.py` loads it by file path via
  `importlib.util.spec_from_file_location`, which also preserves the
  `sys.path.insert(...)` bootstrap line at the top of `app.py` that makes
  `from pipeuhr import ...` resolve.
- **There is no database in this project.** Template persistence
  (save/load/list) is plain JSON files under `webapp/data/templates/`. Tests
  must isolate this via the `isolated_templates_dir` fixture
  (`tmp_path` + `monkeypatch.setattr(webapp_app_module, "TEMPLATES_DIR", ...)`)
  — never assert against or clean up the real project directory.
  - **Forward-looking placeholder:** if/when this project adopts a real
	database, prefer an in-memory engine for tests (e.g. SQLAlchemy with
	`sqlite:///:memory:`) with per-test transactions/rollback, mirroring the
	same isolation guarantee `isolated_templates_dir` provides today. This is
	documented here as guidance for that future migration — it is **not**
	implemented today because no database currently exists.
- **The SLSQP solver is numerically heavy but deterministic** for a fixed
  model/initial guess (`x0=None` uses the class-defined default, `maxiter`
  is explicit). Solver tests are split into two concerns:
  - `tests/solver/test_solver_properties.py` — feasibility/property
	assertions (constraints satisfied, positive costs, bounds respected).
	Prefer this style for *new* solver behavior, since it survives small,
	legitimate numeric drift.
  - `tests/solver/test_solver_regression.py` — a numeric baseline pinned
	with `pytest.approx(rel=1e-4)`. Only update the `BASELINE_*` constants
	here when a change to the physics/cost model is **intentional** — if
	these tests fail unexpectedly, treat it as a regression signal first,
	not noise to silence.
- **Brazilian-locale decimal input**: `webapp/app.py`'s `build_model()`
  replaces `,` with `.` before casting form values to `float`. Any new
  numeric form field must be covered by (or continue to pass)
  `test_solve_accepts_comma_decimal_input` in
  `tests/integration/test_app_routes.py`.

## 7. Rules for Changing Code (read this before editing `pipeuhr/` or `webapp/`)

These rules apply to **any** agent — human or AI — modifying this
repository's behavior:

1. **New public function/method in `pipeuhr/`** → add or extend a test in
   `tests/unit/` (or `tests/solver/` if it only manifests through
   `solve()`). No exceptions for "trivial" functions — trivial functions are
   exactly where regressions hide silently.
2. **New/changed Flask route in `webapp/app.py`** → add or extend a test in
   `tests/integration/test_app_routes.py` using the `client` fixture.
3. **New form field on `index.html`** → add it to `FIELD_GROUPS` handling
   coverage implicitly via existing `POST /solve` tests, and add a
   dedicated assertion if the field has special parsing/validation logic.
4. **Change to a cost formula, constraint bound, or solver configuration**
   → update `tests/solver/test_solver_regression.py`'s `BASELINE_*`
   constants **deliberately** (re-capture via a real `solve()` run) and
   explain why in the commit/PR description. Do not "fix" a regression test
   by loosening its tolerance without understanding why it moved.
5. **Change to template persistence (save/load/list)** → extend
   `tests/integration/test_app_routes.py`; always use
   `isolated_templates_dir`, never the real `webapp/data/templates/`.
6. **Any behavior reachable from the UI** should remain covered by the
   single E2E smoke test staying green; it is not the place to add new
   assertions — extend `integration/` instead and keep `e2e/` minimal.

### Definition of Done

Before considering a change complete:

- [ ] `py -m pytest -m "not slow and not e2e"` passes.
- [ ] `py -m pytest -m "not e2e"` passes (includes solver tests).
- [ ] If the change touches anything reachable from `/`, `/solve`, or
	  `/templates/*`, `py -m pytest tests/e2e` passes (or is explicitly
	  skipped with a documented reason, e.g. no browser installed).
- [ ] New/changed behavior has a corresponding new/updated test — not just
	  "existing tests still pass".
- [ ] No test was weakened (loosened tolerance, removed assertion, added a
	  marker to skip) merely to make it pass without understanding why it
	  previously failed.

## 8. Coverage

`pytest.ini` wires `--cov=pipeuhr --cov=webapp --cov-report=term-missing`
into the default `addopts`, so any `pytest` invocation reports coverage
unless `--no-cov` is passed. Treat coverage as a signal for *untested
paths to investigate*, not a target to game — 100% coverage with weak
assertions is worse than 90% coverage with meaningful ones.
