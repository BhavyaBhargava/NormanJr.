"""End-to-end audit scenarios verifying safety boundaries and fixture auditing."""

import functools
import http.server
import socket
import threading
from pathlib import Path
import pytest

from normanjr.cli import _run_audit_pipeline
from normanjr.config import AppConfig, BrowserSettings, ExplorationSettings, SafetySettings
from normanjr.domain.enums import TerminationReason
from normanjr.storage.run_repository import RunRepository

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sites"


class StaticSiteServer:
    """Serves a specific fixture directory on an ephemeral localhost port."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.server = None
        self.thread = None

    def start(self) -> None:
        dir_str = str(self.directory)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=dir_str)
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


@pytest.mark.asyncio
async def test_e2e_multi_step_form_halts_at_final_submit(tmp_path: Path):
    """Verify that multi-step wizard exploration stops at the final submission boundary."""
    server = StaticSiteServer(FIXTURES_DIR / "multi_step_form")
    server.start()
    url = f"http://127.0.0.1:{server.port}/index.html"

    try:
        config = AppConfig(
            safety=SafetySettings(
                allow_private_target=True,
                allow_final_submit=False,  # Blocked by default
            ),
            exploration=ExplorationSettings(
                max_journeys=1,
                max_steps_per_journey=5,
                same_origin_only=True,
            ),
            browser=BrowserSettings(headless=True, isolated=True),
        )

        exit_code = await _run_audit_pipeline(
            url=url,
            goals=["Proceed through checkout steps"],
            config=config,
            headed=False,
            output_dir=tmp_path,
        )

        assert exit_code == 0

        # Find generated run folder
        run_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("run-")]
        assert len(run_dirs) == 1
        repo = RunRepository(tmp_path, run_dirs[0].name)
        result = repo.load_result()

        # Should have generated reports
        assert (repo.run_dir / "report.html").exists()

    finally:
        server.stop()


@pytest.mark.asyncio
async def test_e2e_accessibility_issues_scoring(tmp_path: Path):
    """Verify that seeded defects on accessibility_issues site are recorded and scored."""
    server = StaticSiteServer(FIXTURES_DIR / "accessibility_issues")
    server.start()
    url = f"http://127.0.0.1:{server.port}/index.html"

    try:
        config = AppConfig(
            safety=SafetySettings(allow_private_target=True),
            exploration=ExplorationSettings(
                max_journeys=1,
                max_steps_per_journey=2,
                same_origin_only=True,
            ),
            browser=BrowserSettings(headless=True, isolated=True),
        )

        exit_code = await _run_audit_pipeline(
            url=url,
            goals=["Inspect accessibility issues"],
            config=config,
            headed=False,
            output_dir=tmp_path,
        )

        assert exit_code == 0

        run_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("run-")]
        repo = RunRepository(tmp_path, run_dirs[0].name)
        result = repo.load_result()

        # Score should reflect deductions
        assert result.score is not None
        assert result.score.overall_score < 100.0
        assert len(result.findings) >= 2

    finally:
        server.stop()
