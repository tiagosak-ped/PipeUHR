"""Playwright browser smoke E2E test: the one full-stack, real-browser
check that the whole page (Tailwind/DaisyUI + vanilla JS + Flask template
rendering) works together, end to end.

This intentionally does NOT re-verify solver numerics (see
tests/solver/) or route-level JSON contracts (see tests/integration/) — it
only proves a real browser can load the form, submit it, and land on a
rendered results page. Marked `e2e` and skipped automatically (via
browser_page) when Playwright's Chromium isn't installed locally.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


def test_user_can_submit_default_form_and_see_results(live_server, browser_page):
	"""A user opening the app in a real browser, submitting the default
	parameter form unchanged, must land on the results page showing
	'Resultado da otimização' — the single most important user-facing
	guarantee: the whole stack (UI, form JS, Flask route, solver,
	constraint simulator, results template) works together end to end.
	"""
	# Arrange
	page = browser_page
	page.goto(live_server + "/")

	# Act
	page.get_by_role("button", name="Otimizar").click()
	page.wait_for_load_state("networkidle")

	# Assert
	assert "Resultado da otimização" in page.content()
	assert page.url == live_server + "/solve"
