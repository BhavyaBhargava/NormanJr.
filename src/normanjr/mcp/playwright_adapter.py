"""High-level typed adapter wrapping Playwright MCP tool calls."""

from __future__ import annotations

import time
from typing import Any

from mcp import ClientSession

from normanjr.exceptions import (
    BrowserTimeout,
    McpToolFailure,
    NavigationBlocked,
    TargetNotActionable,
    TargetReferenceExpired,
)
from normanjr.mcp.content import NormalizedContent, normalize_tool_result
from normanjr.security.url_policy import UrlPolicy, UrlPolicyError


class PlaywrightAdapter:
    """Provides a typed, resilient Python API on top of an MCP ClientSession."""

    def __init__(self, session: ClientSession, url_policy: UrlPolicy | None = None) -> None:
        self.session = session
        self.url_policy = url_policy

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> NormalizedContent:
        """Execute an MCP tool and return normalized output with error classification."""
        start_time = time.monotonic()
        try:
            raw_result = await self.session.call_tool(tool_name, arguments=arguments)
        except Exception as e:
            msg = str(e).lower()
            if "timeout" in msg:
                raise BrowserTimeout(f"Tool {tool_name} timed out: {e}") from e
            raise McpToolFailure(f"Execution of {tool_name} failed: {e}") from e

        normalized = normalize_tool_result(raw_result)

        if normalized.is_error:
            err_text = normalized.error_message or "Unknown MCP tool failure"
            err_lower = err_text.lower()

            if "not found" in err_lower or "expired" in err_lower or "stale" in err_lower:
                raise TargetReferenceExpired(f"Element reference expired: {err_text}")
            elif "not visible" in err_lower or "disabled" in err_lower or "obscured" in err_lower:
                raise TargetNotActionable(f"Element not actionable: {err_text}")
            elif "timeout" in err_lower:
                raise BrowserTimeout(f"Timeout during {tool_name}: {err_text}")
            else:
                raise McpToolFailure(f"Tool {tool_name} returned error: {err_text}")

        return normalized

    async def navigate(self, url: str) -> NormalizedContent:
        """Validate URL against security policy and navigate."""
        if self.url_policy:
            try:
                self.url_policy.validate_url(url)
            except UrlPolicyError as e:
                raise NavigationBlocked(str(e)) from e

        return await self._call_tool("browser_navigate", {"url": url})

    async def take_snapshot(self) -> str:
        """Capture the accessibility snapshot markdown representation of the current page."""
        result = await self._call_tool("browser_snapshot", {})
        return result.text

    async def take_screenshot(self) -> bytes:
        """Capture screenshot image bytes of the current viewport."""
        result = await self._call_tool("browser_take_screenshot", {})
        if result.images:
            return result.images[0]
        return b""

    async def click_ref(self, ref: str) -> NormalizedContent:
        """Click on the element identified by snapshot reference."""
        return await self._call_tool("browser_click", {"ref": ref})

    async def type_ref(self, ref: str, text: str) -> NormalizedContent:
        """Type text into the element identified by snapshot reference."""
        return await self._call_tool("browser_type", {"ref": ref, "text": text})

    async def select_option(self, ref: str, value: str) -> NormalizedContent:
        """Select an option in a dropdown element."""
        return await self._call_tool("browser_select_option", {"ref": ref, "value": value})

    async def press_key(self, key: str) -> NormalizedContent:
        """Press a keyboard key (e.g. Enter, Tab, Escape, ArrowDown)."""
        return await self._call_tool("browser_press_key", {"key": key})

    async def hover_ref(self, ref: str) -> NormalizedContent:
        """Hover over an element identified by snapshot reference."""
        return await self._call_tool("browser_hover", {"ref": ref})

    async def navigate_back(self) -> NormalizedContent:
        """Navigate back to the previous page in history."""
        return await self._call_tool("browser_navigate_back", {})

    async def wait_for(self, text: str | None = None, time_ms: int = 500) -> NormalizedContent:
        """Wait for dynamic content to settle or specific text to appear (Playwright MCP expects seconds)."""
        time_seconds = max(round(time_ms / 1000.0, 2), 0.1)
        args: dict[str, Any] = {"time": time_seconds}
        if text:
            args["text"] = text
        return await self._call_tool("browser_wait_for", args)


    async def evaluate_script(self, expression: str) -> Any:
        """Execute a read-only metric script in the page context and return parsed result or raw text."""
        # Wrap expression in arrow function if not already a function
        expr = expression.strip()
        if not (expr.startswith("function") or expr.startswith("()") or expr.startswith("async")):
            fn_code = f"() => ({expr})"
        else:
            fn_code = expr

        result = await self._call_tool("browser_evaluate", {"function": fn_code})
        raw_text = result.text

        # Extract result from Playwright MCP output block
        if "### Result" in raw_text:
            parts = raw_text.split("### Result", 1)[1]
            if "### Ran Playwright code" in parts:
                res_block = parts.split("### Ran Playwright code")[0].strip()
            else:
                res_block = parts.strip()
        else:
            res_block = raw_text.strip()

        # Parse JSON if possible
        import json
        try:
            parsed = json.loads(res_block)
            if isinstance(parsed, str) and (parsed.startswith("[") or parsed.startswith("{")):
                try:
                    return json.loads(parsed)
                except Exception:
                    return parsed
            return parsed
        except Exception:
            return res_block

    async def get_console_messages(self) -> list[str]:
        """Retrieve recent browser console error messages."""
        try:
            result = await self._call_tool("browser_console_messages", {})
            return [line.strip() for line in result.text.splitlines() if line.strip()]
        except Exception:
            return []

    async def get_network_requests(self) -> list[str]:
        """Retrieve recent network requests."""
        try:
            result = await self._call_tool("browser_network_requests", {})
            return [line.strip() for line in result.text.splitlines() if line.strip()]
        except Exception:
            return []
