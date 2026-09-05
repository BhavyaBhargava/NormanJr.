"""Error taxonomy and custom exceptions for NormanJr."""

from __future__ import annotations


class NormanJrError(Exception):
    """Base exception for all NormanJr errors."""


class McpUnavailable(NormanJrError):
    """Raised when the MCP server process fails to launch or closes unexpectedly."""


class ToolContractError(NormanJrError):
    """Raised when the MCP server does not provide required tools or changes schema."""


class TargetReferenceExpired(NormanJrError):
    """Raised when an accessibility element snapshot reference is no longer valid in the DOM."""


class TargetNotActionable(NormanJrError):
    """Raised when an element is hidden, disabled, or covered by an overlay."""


class NavigationBlocked(NormanJrError):
    """Raised when navigation is blocked by URL policy, SSRF checks, or origin boundary."""


class BrowserTimeout(NormanJrError):
    """Raised when a browser operation or navigation exceeds the configured deadline."""


class McpToolFailure(NormanJrError):
    """Raised when an MCP tool execution reports an error."""


class PolicyViolationError(NormanJrError):
    """Raised when an action or configuration violates security policy."""


class BudgetExceededError(NormanJrError):
    """Raised when step, token, time, or cost budgets are exceeded."""
