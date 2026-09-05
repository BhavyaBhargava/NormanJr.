"""Tool contract definitions and validation for Playwright MCP server."""

from __future__ import annotations

from typing import Any, NamedTuple


class ToolContractValidation(NamedTuple):
    is_valid: bool
    missing_required: list[str]
    missing_optional: list[str]
    available_tools: list[str]
    diagnostics: str


REQUIRED_TOOLS = [
    "browser_navigate",
    "browser_snapshot",
    "browser_take_screenshot",
    "browser_click",
    "browser_type",
    "browser_evaluate",
    "browser_wait_for",
]

OPTIONAL_TOOLS = [
    "browser_navigate_back",
    "browser_fill_form",
    "browser_select_option",
    "browser_press_key",
    "browser_hover",
    "browser_console_messages",
    "browser_network_requests",
    "browser_tabs",
    "browser_pdf_save",
]


def validate_tool_contract(tools: list[Any]) -> ToolContractValidation:
    """Verify that the MCP server provides all required tools for NormanJr."""
    tool_names = set()
    for t in tools:
        name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else str(t))
        if name:
            tool_names.add(name)

    missing_required = [req for req in REQUIRED_TOOLS if req not in tool_names]
    missing_optional = [opt for opt in OPTIONAL_TOOLS if opt not in tool_names]

    is_valid = len(missing_required) == 0

    if not is_valid:
        diag = (
            f"MCP Tool Contract Failure: Missing required tools: {', '.join(missing_required)}. "
            f"Available tools: {', '.join(sorted(tool_names))}."
        )
    elif missing_optional:
        diag = (
            f"MCP Tool Contract Valid with warnings: Missing optional tools: {', '.join(missing_optional)}."
        )
    else:
        diag = "MCP Tool Contract fully satisfied."

    return ToolContractValidation(
        is_valid=is_valid,
        missing_required=missing_required,
        missing_optional=missing_optional,
        available_tools=sorted(tool_names),
        diagnostics=diag,
    )
