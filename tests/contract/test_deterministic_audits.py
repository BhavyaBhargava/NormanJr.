"""Contract test verifying deterministic audits, DOM metrics, and axe-core scans."""

import http.server
import socket
import threading
import pytest

from normanjr.audit.accessibility import parse_snapshot_elements
from normanjr.audit.deterministic import run_deterministic_audits
from normanjr.config import BrowserSettings, ExplorationSettings, SafetySettings
from normanjr.mcp.client import PlaywrightMcpClient
from normanjr.mcp.playwright_adapter import PlaywrightAdapter
from normanjr.security.url_policy import UrlPolicy

# Page with seeded accessibility and UX defects
DEFECTIVE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Defective UX Page</title>
  <style>
    .tiny-btn { width: 12px; height: 12px; padding: 0; font-size: 8px; }
  </style>
</head>
<body>
  <h1>Main Page Heading</h1>
  <h3>Skipped to H3</h3>

  <!-- Tiny target size (<24x24px) -->
  <button id="tiny" class="tiny-btn">x</button>

  <!-- Form input missing programmatic label -->
  <input type="text" id="orphan-input" placeholder="No label here" />

  <!-- Image missing alt attribute -->
  <img src="test.jpg" id="unlabelled-img" width="100" height="50" />
</body>
</html>
"""


class DefectiveServer:
    def __init__(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.server = None
        self.thread = None

    def start(self) -> None:
        handler = lambda *args: DefectiveHandler(*args)
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class DefectiveHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(DEFECTIVE_HTML.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        pass


def test_parse_snapshot_elements():
    sample_snapshot = """
- heading "Welcome" [level=1]
- button "Submit Order" [ref=e2]
- textbox "Search" [ref=e5] [disabled]
- link "Privacy Policy" [ref=e8]
"""
    elements = parse_snapshot_elements(sample_snapshot)
    assert len(elements) == 3  # button, textbox, link
    btn = next(e for e in elements if e.role == "button")
    assert btn.ref == "e2"
    assert btn.name == "Submit Order"
    assert btn.is_enabled is True

    txt = next(e for e in elements if e.role == "textbox")
    assert txt.ref == "e5"
    assert txt.is_enabled is False


@pytest.mark.asyncio
async def test_deterministic_audits_on_defective_page():
    server = DefectiveServer()
    server.start()
    url = f"http://127.0.0.1:{server.port}/"

    try:
        browser_settings = BrowserSettings(headless=True, isolated=True)
        url_policy = UrlPolicy(
            ExplorationSettings(same_origin_only=True),
            SafetySettings(allow_private_target=True),
            initial_origin=f"http://127.0.0.1:{server.port}",
        )

        client = PlaywrightMcpClient(browser_settings)
        async with client.connect() as session:
            adapter = PlaywrightAdapter(session, url_policy=url_policy)
            await adapter.navigate(url)

            # Run deterministic audits
            findings, metrics = await run_deterministic_audits(adapter, journey_id="j1", state_id="s1")

            criterion_ids = [f.criterion_id for f in findings]

            # 1. Undersized button (<24x24px) should be detected
            assert "WCAG-2.5.8-TARGET-SIZE" in criterion_ids

            # 2. Input missing label should be detected
            assert "WCAG-3.3.2-LABELS-INSTRUCTIONS" in criterion_ids

            # 3. Image missing alt should be detected
            assert "WCAG-4.1.2-NAME-ROLE-VALUE" in criterion_ids

            # Metrics should contain counts
            assert metrics["undersized_targets_count"] >= 1
            assert metrics["unlabelled_inputs_count"] >= 1
            assert metrics["missing_alt_images_count"] >= 1

    finally:
        server.stop()
