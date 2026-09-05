"""Execute node: maps the authorized action to a Playwright MCP tool call."""

from __future__ import annotations

import time
from typing import Any

from normanjr.domain.enums import ActionType
from normanjr.domain.models import ExecutionRecord
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def execute_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Execute the authorized action in the browser."""
    action = state.get("current_action")
    decision = state.get("current_policy_decision")
    obs = state.get("current_observation")

    if not action or (decision and not decision.allowed):
        return {}

    start_t = time.monotonic()
    success = True
    error_class: str | None = None
    error_msg: str | None = None
    tool_used = "browser_noop"

    try:
        if action.action_type == ActionType.CLICK and action.target_ref:
            tool_used = "browser_click"
            await context.adapter.click_ref(action.target_ref)
        elif action.action_type == ActionType.TYPE and action.target_ref:
            tool_used = "browser_type"
            await context.adapter.type_ref(action.target_ref, action.value or "")
        elif action.action_type == ActionType.SELECT and action.target_ref:
            tool_used = "browser_select_option"
            await context.adapter.select_option(action.target_ref, action.value or "")
        elif action.action_type == ActionType.PRESS_KEY:
            tool_used = "browser_press_key"
            await context.adapter.press_key(action.value or "Enter")
        elif action.action_type == ActionType.HOVER and action.target_ref:
            tool_used = "browser_hover"
            await context.adapter.hover_ref(action.target_ref)
        elif action.action_type == ActionType.BACK:
            tool_used = "browser_navigate_back"
            await context.adapter.navigate_back()
        elif action.action_type == ActionType.WAIT_FOR:
            tool_used = "browser_wait_for"
            await context.adapter.wait_for(time_ms=1000)
    except Exception as e:
        success = False
        error_class = e.__class__.__name__
        error_msg = str(e)

    duration_ms = round((time.monotonic() - start_t) * 1000, 2)

    record = ExecutionRecord(
        execution_id=f"exec-{state.get('current_step_number', 0):03d}",
        action=action,
        mcp_tool=tool_used,
        arguments={"target_ref": action.target_ref, "value": action.value},
        duration_ms=duration_ms,
        success=success,
        error_class=error_class,
        error_message=error_msg,
        before_observation_id=obs.observation_id if obs else None,
    )

    context.repo.log_event("ACTION_EXECUTED", {
        "tool": tool_used,
        "duration_ms": duration_ms,
        "success": success,
        "error": error_msg,
    })

    return {
        "current_execution": record,
        "current_step_number": state.get("current_step_number", 0) + 1,
        "budget_used_steps": state.get("budget_used_steps", 0) + 1,
    }
