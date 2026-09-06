"""Lifecycle manager for Playwright MCP server stdio connection."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from normanjr.config import BrowserSettings
from normanjr.exceptions import McpUnavailable, ToolContractError
from normanjr.mcp.tool_contract import validate_tool_contract


class PlaywrightMcpClient:
    """Manages the lifecycle of a Playwright MCP server process via stdio transport."""

    def __init__(
        self,
        browser_settings: BrowserSettings,
        output_dir: Path | str | None = None,
        caps: list[str] | None = None,
        init_script: Path | str | None = None,
    ) -> None:
        self.settings = browser_settings
        self.output_dir = Path(output_dir) if output_dir else None
        self.caps = caps or []
        self.init_script = Path(init_script) if init_script else None

    def _build_server_parameters(self) -> StdioServerParameters:
        cli_path = Path("node_modules/@playwright/mcp/cli.js")
        if not cli_path.exists():
            # Try alternate path
            bin_path = Path("node_modules/.bin/playwright-mcp")
            if bin_path.exists():
                cli_path = bin_path
            else:
                raise McpUnavailable(
                    "Playwright MCP CLI script not found in node_modules. Run `npm install`."
                )

        args = [str(cli_path.resolve()), "--no-sandbox"]

        if self.settings.headless:
            args.append("--headless")
        if self.settings.isolated:
            args.append("--isolated")
        if self.caps:
            args.extend(["--caps", ",".join(self.caps)])
        if self.output_dir:
            args.extend(["--output-dir", str(self.output_dir.resolve())])
        if self.init_script and self.init_script.exists():
            args.extend(["--init-script", str(self.init_script.resolve())])

        args.extend([
            "--timeout-action", str(self.settings.action_timeout_ms),
            "--timeout-navigation", str(self.settings.navigation_timeout_ms),
            "--viewport-size", f"{self.settings.viewport_width}x{self.settings.viewport_height}",
        ])

        if self.settings.browser_name and self.settings.browser_name in ("firefox", "webkit", "chromium"):
            args.extend(["--browser", self.settings.browser_name])

        if self.settings.user_agent:
            args.extend(["--user-agent", self.settings.user_agent])

        if self.settings.device_scale_factor and self.settings.device_scale_factor != 1.0:
            args.extend(["--device-scale-factor", str(self.settings.device_scale_factor)])

        if self.settings.storage_state_path and Path(self.settings.storage_state_path).exists():
            args.extend(["--storage-state", str(Path(self.settings.storage_state_path).resolve())])

        if self.settings.save_storage_state_path:
            args.extend(["--save-storage-state", str(Path(self.settings.save_storage_state_path).resolve())])

        env = os.environ.copy()

        return StdioServerParameters(
            command="node",
            args=args,
            env=env,
        )

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[ClientSession]:
        """Connect to the Playwright MCP server, validate tool contract, and yield ClientSession."""
        params = self._build_server_parameters()

        try:
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # Verify tool contract
                    tools_result = await session.list_tools()
                    validation = validate_tool_contract(tools_result.tools)
                    if not validation.is_valid:
                        raise ToolContractError(validation.diagnostics)

                    yield session
        except (ToolContractError, McpUnavailable):
            raise
        except Exception as e:
            raise McpUnavailable(f"Failed to communicate with Playwright MCP server: {e}") from e
