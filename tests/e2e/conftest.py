"""E2E-only fixtures: a real Werkzeug live server + a raw Playwright browser
page, with a graceful skip when Chromium isn't installed locally.

Kept separate from the top-level tests/conftest.py because only this layer
needs a real TCP server and a real browser process — costs the other
layers (unit/integration/solver) should never pay just to collect tests.
"""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterator

import pytest
from werkzeug.serving import BaseWSGIServer, make_server


def _free_port() -> int:
	"""Ask the OS for an ephemeral free TCP port on localhost."""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.bind(("127.0.0.1", 0))
		return sock.getsockname()[1]


@pytest.fixture()
def live_server(webapp_app_module, isolated_templates_dir) -> Iterator[str]:
	"""Run the real Flask app on a background thread bound to a real socket.

	Why not the Flask ``test_client``: Playwright drives an actual browser
	process, which can only speak real HTTP over a real TCP connection, not
	Werkzeug's in-process WSGI test client. ``isolated_templates_dir`` is
	still required so this smoke test cannot read/write the real project's
	``webapp/data/templates/`` directory.
	"""
	app = webapp_app_module.app
	app.config.update(TESTING=True)
	port = _free_port()
	server: BaseWSGIServer = make_server("127.0.0.1", port, app)
	thread = threading.Thread(target=server.serve_forever, daemon=True)
	thread.start()
	try:
		yield f"http://127.0.0.1:{port}"
	finally:
		server.shutdown()
		thread.join(timeout=5)


@pytest.fixture()
def browser_page(request):
	"""A Playwright Chromium page, or a graceful ``pytest.skip``.

	Launches its own Playwright instance directly (independent of the
	pytest-playwright plugin's fixtures) so contributors who haven't run
	``playwright install chromium`` get a clean skip with an actionable
	message instead of an opaque fixture-setup error.
	"""
	try:
		from playwright.sync_api import sync_playwright
	except ImportError:
		pytest.skip("playwright package not installed; see requirements-dev.txt")

	playwright_ctx = sync_playwright().start()
	try:
		browser = playwright_ctx.chromium.launch()
	except Exception as exc:  # pragma: no cover - depends on local environment
		playwright_ctx.stop()
		pytest.skip(f"Playwright Chromium browser not installed ({exc}); "
					f"run: py -m playwright install chromium")
		return

	page = browser.new_page()
	try:
		yield page
	finally:
		page.close()
		browser.close()
		playwright_ctx.stop()
