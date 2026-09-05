"""Authorize node: evaluates proposed action through the deterministic ActionPolicy gateway."""

from __future__ import annotations

from typing import Any

from normanjr.domain.enums import TerminationReason
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def authorize_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Pass the proposed action through the security policy gateway."""
    action = state.get("current_action")
    obs = state.get("current_observation")

    if not action:
        return {}

    target_name = ""
    if obs and action.target_ref:
        for elem in obs.interactive_elements:
            if elem.ref == action.target_ref:
                target_name = elem.name
                break

    decision = context.action_policy.evaluate(action, target_name=target_name)

    context.repo.log_event("POLICY_DECISION", {
        "action": action.action_type.value,
        "target_ref": action.target_ref,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "reason_code": decision.reason_code,
    })

    updates: dict[str, Any] = {"current_policy_decision": decision}
    if not decision.allowed:
        if decision.reason_code == "FINAL_SUBMIT_BLOCKED":
            updates["termination_reason"] = TerminationReason.FINAL_SUBMIT_BOUNDARY
        else:
            updates["termination_reason"] = TerminationReason.BLOCKED_BY_POLICY

    return updates
