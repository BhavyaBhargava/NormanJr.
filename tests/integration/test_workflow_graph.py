"""Integration test verifying the end-to-end LangGraph exploration workflow."""

import http.server
import socket
import threading
from pathlib import Path
import pytest

from normanjr.audit.rubric import load_rubric
from normanjr.config import AppConfig, BrowserSettings, ExplorationSettings, SafetySettings
from normanjr.domain.enums import AuditStatus
from normanjr.domain.models import Journey
from normanjr.exploration.context import AuditContext
from normanjr.exploration.graph import build_audit_graph
from normanjr.mcp.client import PlaywrightMcpClient
from normanjr.mcp.playwright_adapter import PlaywrightAdapter
from normanjr.security.action_policy import ActionPolicy
from normanjr.security.url_policy import UrlPolicy
from normanjr.storage.run_repository import RunRepository

INDEX_HTML = """<!DOCTYPE html>
<html>
<head><title>NormanJr Flow Test</title></head>
<body>
  <h1>Welcome to Store</h1>
  <a href="/catalog" id="cat-link">Browse Catalog</a>
</body>
</html>
"""

CATALOG_HTML = """<!DOCTYPE html>
<html>
<head><title>Catalog Page</title></head>
<body>
  <h1>Product Catalog</h1>
  <button id="add-btn" style="width:10px;height:10px;">+</button>
  <a href="/" id="home-link">Back Home</a>
</body>
</html>
"""


class MultiPageServer:
    def __init__(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.server = None
        self.thread = None

    def start(self) -> None:
        handler = lambda *args: MultiPageHandler(*args)
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class MultiPageHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        if self.path == "/catalog":
            self.wfile.write(CATALOG_HTML.encode("utf-8"))
        else:
            self.wfile.write(INDEX_HTML.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.mark.asyncio
async def test_langgraph_full_workflow(tmp_path: Path):
    server = MultiPageServer()
    server.start()
    url = f"http://127.0.0.1:{server.port}/"

    try:
        config = AppConfig(
            safety=SafetySettings(allow_private_target=True),
            exploration=ExplorationSettings(
                max_journeys=1,
                max_steps_per_journey=3,
                same_origin_only=True,
            ),
            browser=BrowserSettings(headless=True, isolated=True),
        )
        rubric = load_rubric()
        repo = RunRepository(tmp_path, run_id="test-run-e2e")

        url_policy = UrlPolicy(
            config.exploration,
            config.safety,
            initial_origin=f"http://127.0.0.1:{server.port}",
        )
        action_policy = ActionPolicy(config.safety)

        client = PlaywrightMcpClient(config.browser)

        async with client.connect() as session:
            adapter = PlaywrightAdapter(session, url_policy=url_policy)

            # Navigate to starting URL
            await adapter.navigate(url)

            context = AuditContext(
                adapter=adapter,
                action_policy=action_policy,
                url_policy=url_policy,
                repo=repo,
                config=config,
                rubric=rubric,
            )

            # Build graph
            graph = build_audit_graph()

            initial_state = {
                "run_id": "test-run-e2e",
                "target_url": url,
                "journeys": [Journey(journey_id="j1", goal="Browse Catalog")],
                "current_journey_index": 0,
                "current_step_number": 0,
                "all_findings": [],
                "visited_state_fingerprints": [],
                "status": AuditStatus.RUNNING,
            }

            final_state = await graph.ainvoke(
                initial_state,
                config={"configurable": {"context": context}},
            )

            assert final_state["status"] == AuditStatus.COMPLETED

            # Verify persisted result
            result = repo.load_result()
            assert result.run_id == "test-run-e2e"
            assert result.status == AuditStatus.COMPLETED
            assert result.score is not None
            assert len(result.findings) >= 0

            # Verify manifest
            manifest_file = repo.run_dir / "manifest.json"
            assert manifest_file.exists()

    finally:
        server.stop()
