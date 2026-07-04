"""Flask integration tests for webapp/app.py, using Flask's test_client.

These tests exercise full request/response cycles in-process (no real
socket), covering the parameter form, the optimize-and-render pipeline, and
the JSON template CRUD endpoints. Persistence is isolated via the
isolated_templates_dir fixture (see conftest.py) so these tests never read
or write the real webapp/data/templates/ directory — there is no database
in this project, so the JSON template folder *is* the persistence layer
that needs isolating.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_index_renders_parameter_form(client):
	"""GET / must render the parameter entry page (HTTP 200) with its
	Portuguese heading, confirming the Jinja2 template renders successfully
	with the default FIELD_GROUPS/values context.
	"""
	# Act
	response = client.get("/")

	# Assert
	assert response.status_code == 200
	assert "Parâmetros do projeto".encode("utf-8") in response.data


def test_index_contains_optimize_button(client):
	"""GET / must include the 'Otimizar' submit control, since that is the
	only way a user triggers the /solve route from the UI.
	"""
	# Act
	response = client.get("/")

	# Assert
	assert "Otimizar".encode("utf-8") in response.data


def test_solve_with_default_parameters_renders_results_page(client):
	"""POST /solve with an empty form (all defaults, default circuit) must
	run the full solve + constraint-verification pipeline and render the
	results page, proving the route wiring between GlobalOptimization,
	ConstraintSimulator, and result.html works end-to-end.
	"""
	# Act
	response = client.post("/solve", data={})

	# Assert
	assert response.status_code == 200
	assert "Resultado da otimização".encode("utf-8") in response.data


def test_solve_accepts_comma_decimal_input(client):
	"""POST /solve must tolerate Brazilian-locale comma decimals (e.g.
	'144,0' for FLOW_TURBINE), since build_model() explicitly replaces ','
	by '.' before casting to float. A regression here would break the form
	for every pt-BR user typing decimals with a comma.
	"""
	# Arrange
	form_data = {"FLOW_TURBINE": "144,0"}

	# Act
	response = client.post("/solve", data=form_data)

	# Assert
	assert response.status_code == 200


def test_templates_list_is_empty_for_fresh_isolated_directory(client, isolated_templates_dir):
	"""GET /templates/list on a fresh, isolated template directory must
	return an empty JSON array, proving the endpoint never leaks templates
	from the real project data directory into a test run.
	"""
	# Act
	response = client.get("/templates/list")

	# Assert
	assert response.status_code == 200
	assert json.loads(response.data) == []


def test_templates_save_then_list_round_trip(client, isolated_templates_dir):
	"""A template saved via POST /templates/save must immediately appear in
	GET /templates/list, verifying the save-then-list round trip against the
	isolated directory (not the real webapp/data/templates/).
	"""
	# Arrange
	payload = {"name": "Projeto Teste", "params": {"FLOW_TURBINE": 144.0}, "segments": []}

	# Act
	save_response = client.post("/templates/save", json=payload)
	list_response = client.get("/templates/list")

	# Assert
	assert save_response.status_code == 200
	items = json.loads(list_response.data)
	assert any(item["name"] == "Projeto Teste" for item in items)


def test_templates_save_then_load_round_trip(client, isolated_templates_dir):
	"""A template saved via POST /templates/save must be retrievable with
	the same params/segments via GET /templates/load/<slug>, proving the
	JSON persistence round trip is lossless.
	"""
	# Arrange
	payload = {"name": "Projeto Redondo", "params": {"H_MED_SUP": 76.0}, "segments": []}
	save_response = client.post("/templates/save", json=payload)
	slug = json.loads(save_response.data)["file"]

	# Act
	load_response = client.get(f"/templates/load/{slug}")

	# Assert
	loaded = json.loads(load_response.data)
	assert loaded["params"] == {"H_MED_SUP": 76.0}


def test_templates_load_missing_slug_returns_404(client, isolated_templates_dir):
	"""GET /templates/load/<slug> for a slug that was never saved must
	return HTTP 404 with an explicit error payload, not a raw exception or a
	silently empty 200 response.
	"""
	# Act
	response = client.get("/templates/load/does-not-exist")

	# Assert
	assert response.status_code == 404
	assert json.loads(response.data) == {"error": "not found"}


def test_templates_save_does_not_touch_real_data_directory(client, isolated_templates_dir):
	"""Saving a template during a test must never create/modify a file
	under the real project's webapp/data/templates/ directory — this is
	the core isolation guarantee the whole test suite depends on.
	"""
	# Arrange
	real_templates_dir = Path(__file__).resolve().parents[2] / "webapp" / "data" / "templates"
	files_before = set(real_templates_dir.glob("*.json"))

	# Act
	client.post(
		"/templates/save",
		json={"name": "pytest-isolation-marker", "params": {}, "segments": []},
	)

	# Assert
	files_after = set(real_templates_dir.glob("*.json"))
	assert files_after == files_before
