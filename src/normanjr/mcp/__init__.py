"""MCP package for NormanJr."""

from normanjr.mcp.client import PlaywrightMcpClient
from normanjr.mcp.content import NormalizedContent, normalize_tool_result
from normanjr.mcp.playwright_adapter import PlaywrightAdapter
from normanjr.mcp.tool_contract import REQUIRED_TOOLS, validate_tool_contract

__all__ = [
    "NormalizedContent",
    "PlaywrightAdapter",
    "PlaywrightMcpClient",
    "REQUIRED_TOOLS",
    "normalize_tool_result",
    "validate_tool_contract",
]
