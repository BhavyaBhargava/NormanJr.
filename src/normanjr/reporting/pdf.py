"""PDF report generation using isolated Playwright MCP with pdf capability."""

from __future__ import annotations

import http.server
import socket
import threading
from pathlib import Path

from normanjr.config import BrowserSettings, ExplorationSettings, SafetySettings
from normanjr.mcp.client import PlaywrightMcpClient
from normanjr.mcp.playwright_adapter import PlaywrightAdapter
from normanjr.security.url_policy import UrlPolicy


class ReportServer:
    """Ephemeral loopback HTTP server serving static report directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.server = None
        self.thread = None

    def start(self) -> None:
        dir_str = str(self.directory)
        handler = lambda *args: http.server.SimpleHTTPRequestHandler(*args, directory=dir_str)
        self.server = http.server.HTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()


async def render_pdf_report(output_dir: Path) -> Path | None:
    """Render report.html to report.pdf using a dedicated isolated Playwright MCP session."""
    html_path = output_dir / "report.html"
    if not html_path.exists():
        return None

    target_pdf = output_dir / "report.pdf"
    server = ReportServer(output_dir)
    server.start()

    try:
        report_url = f"http://127.0.0.1:{server.port}/report.html"

        browser_settings = BrowserSettings(headless=True, isolated=True)
        url_policy = UrlPolicy(
            ExplorationSettings(same_origin_only=True),
            SafetySettings(allow_private_target=True),
            initial_origin=f"http://127.0.0.1:{server.port}",
        )

        client = PlaywrightMcpClient(browser_settings, output_dir=output_dir, caps=["pdf"])
        async with client.connect() as session:
            adapter = PlaywrightAdapter(session, url_policy=url_policy)
            await adapter.navigate(report_url)
            await adapter._call_tool("browser_pdf_save", {"filename": "report.pdf"})

        if target_pdf.exists() and target_pdf.stat().st_size > 0:
            return target_pdf
    except Exception:
        pass
    finally:
        server.stop()

    return None if not (target_pdf.exists() and target_pdf.stat().st_size > 0) else target_pdf
