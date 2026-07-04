"""Shared pytest fixtures for the PipeUHR test suite.

Centralizes three cross-cutting concerns so individual test modules stay
simple (Arrange/Act/Assert only, no fixture plumbing):

1. Importing ``webapp/app.py`` by file path. It is a script (no
   ``webapp/__init__.py``) that bootstraps its own ``sys.path`` to make the
   ``pipeuhr`` package importable. Loading it via :mod:`importlib.util` lets
   us reuse that bootstrap without registering a clashing, generically named
   top-level ``app`` module in ``sys.modules``.
2. Isolating the on-disk JSON "template" store (``webapp/data/templates/``)
   behind a per-test temporary directory, so tests never read or write the
   real project data. There is no database in this project — this directory
   *is* the persistence layer that needs isolation (see TESTING_GUIDE.md for
   the forward-looking SQLite ``:memory:`` note).
3. Providing fast, reusable ``pipeuhr`` model fixtures shared across the
   unit, integration, and solver test layers.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEBAPP_APP_PATH = REPO_ROOT / "webapp" / "app.py"

_WEBAPP_MODULE_NAME = "pipeuhr_webapp_app_under_test"


def _load_webapp_app_module() -> types.ModuleType:
	"""Import ``webapp/app.py`` by file path as a standalone module.

	Why not ``import app`` or ``from webapp import app``: ``webapp`` has no
	``__init__.py`` (it's a script folder, not a package), and ``app`` is too
	generic a name to safely add to ``sys.path``/``sys.modules`` without
	risking collisions. ``importlib.util`` lets us execute the file exactly
	as Python would, under a unique module name, while still honoring the
	``sys.path.insert(...)`` bootstrap line at the top of ``app.py`` that
	makes ``from pipeuhr import ...`` resolve correctly.
	"""
	if _WEBAPP_MODULE_NAME in sys.modules:
		return sys.modules[_WEBAPP_MODULE_NAME]
	spec = importlib.util.spec_from_file_location(_WEBAPP_MODULE_NAME, WEBAPP_APP_PATH)
	module = importlib.util.module_from_spec(spec)
	sys.modules[_WEBAPP_MODULE_NAME] = module
	assert spec.loader is not None
	spec.loader.exec_module(module)
	return module


@pytest.fixture(scope="session")
def webapp_app_module() -> types.ModuleType:
	"""Session-scoped import of ``webapp/app.py``.

	Session-scoped because importing it triggers relatively expensive
	imports (Flask, NumPy, SciPy via ``pipeuhr``) that only need to happen
	once for the whole test run.
	"""
	return _load_webapp_app_module()


@pytest.fixture()
def isolated_templates_dir(webapp_app_module, tmp_path, monkeypatch) -> Path:
	"""Redirect the module-global ``TEMPLATES_DIR`` to a per-test temp dir.

	Why this matters: the ``/templates/save|load|list`` routes read and
	write real files under ``webapp/data/templates/``. Without this fixture,
	tests would depend on (and pollute) that shared, real project directory,
	breaking determinism and isolation between test runs.
	"""
	isolated_dir = tmp_path / "templates"
	isolated_dir.mkdir(parents=True, exist_ok=True)
	monkeypatch.setattr(webapp_app_module, "TEMPLATES_DIR", isolated_dir)
	return isolated_dir


@pytest.fixture()
def flask_app(webapp_app_module, isolated_templates_dir):
	"""The Flask application, configured for testing with an isolated
	template directory so template CRUD tests never touch real project data.
	"""
	webapp_app_module.app.config.update(TESTING=True)
	return webapp_app_module.app


@pytest.fixture()
def client(flask_app):
	"""Flask test client for fast, in-process HTTP-style integration tests
	(no real socket/server involved)."""
	return flask_app.test_client()


@pytest.fixture()
def default_model():
	"""A fresh ``GlobalOptimization`` model using the production default
	circuit (3 pipes: AB, BC, EF). Cheap to construct — only ``.solve()`` is
	computationally expensive, not instantiation or ``.evaluate()``.
	"""
	from pipeuhr import GlobalOptimization

	return GlobalOptimization()


@pytest.fixture(scope="session")
def solved_default_result():
	"""Solve the default-circuit model once per test session.

	Why session-scoped: SLSQP optimization is comparatively expensive
	(multiple constraint re-evaluations per iteration). Both the solver
	property-based tests and the solver numeric-regression tests need a
	solved result for the same default configuration, so sharing one solve
	avoids paying that cost twice.
	"""
	from pipeuhr import GlobalOptimization

	model = GlobalOptimization()
	result = model.solve(maxiter=500)
	return model, result
