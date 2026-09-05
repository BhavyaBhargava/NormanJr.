"""Contract tests verifying the live Playwright MCP server and adapter."""

import asyncio
import http.server
import socket
import threading
from pathlib import Path
import pytest

from normanjr.config import BrowserSettings, ExplorationSettings, SafetySettings
from normanjr.mcp.client import PlaywrightMcpClient
from normanjr.mcp.playwright_adapter import PlaywrightAdapter
from normanjr.security.url_policy import UrlPolicy

HTML_FIXTURE = """<!DOCTYPE html>
<html>
<head><title>NormanJr MCP Test</title></head>
<body>
  <h1>Interactive Test Page</h1>
  <button id="btn" onclick="document.getElementById('result').textContent = 'Clicked!'">Submit Button</button>
  <input id="input" type="text" placeholder="Enter name" />
  <p id="result">Initial</p>
</body>
</html>
"""


class FixtureServer:
    """Tiny local HTTP server for contract testing."""

    def __init__(self) -> None:
        self.port = self._find_free_port()
        self.server = None
        self.thread = None

    def _find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def start(self) -> None:
        handler = lambda *args: FixtureHandler(*args)
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_FIXTURE.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress server logs during test


@pytest.mark.asyncio
async def test_mcp_connection_and_interaction():
    fixture_server = FixtureServer()
    fixture_server.start()
    url = f"http://127.0.0.1:{fixture_server.port}/"

    try:
        browser_settings = BrowserSettings(headless=True, isolated=True)
        url_policy = UrlPolicy(
            ExplorationSettings(same_origin_only=True),
            SafetySettings(allow_private_target=True),
            initial_origin=f"http://127.0.0.1:{fixture_server.port}",
        )

        client = PlaywrightMcpClient(browser_settings)

        async with client.connect() as session:
            adapter = PlaywrightAdapter(session, url_policy=url_policy)

            # 1. Navigate
            nav_result = await adapter.navigate(url)
            assert not nav_result.is_error

            # 2. Take Snapshot
            snapshot = await adapter.take_snapshot()
            assert "Interactive Test Page" in snapshot
            assert "Submit Button" in snapshot

            # 3. Take Screenshot
            screenshot_bytes = await adapter.take_screenshot()
            assert len(screenshot_bytes) > 0

            # 4. Evaluate Script
            title = await adapter.evaluate_script("document.title")
            assert "NormanJr MCP Test" in title

    finally:
        fixture_server.stop()
