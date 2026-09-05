"""Routing logic and conditional edge transitions for LangGraph."""

from __future__ import annotations

from normanjr.domain.enums import ActionType
from normanjr.exploration.state import AuditState


def route_after_check_progress(state: AuditState) -> str:
    """Route to finalize_journey if termination reason is present, else plan next action."""
    if state.get("termination_reason"):
        return "finalize_journey"
    return "plan"


def route_after_authorize(state: AuditState) -> str:
    """Route to finalize_journey if action is blocked or finish, else execute."""
    decision = state.get("current_policy_decision")
    action = state.get("current_action")

    if decision and not decision.allowed:
        return "finalize_journey"

    if action and action.action_type in (ActionType.FINISH, ActionType.BLOCKED):
        return "finalize_journey"

    return "execute"


def route_after_finalize_journey(state: AuditState) -> str:
    """Route to perceive for the next planned journey, or finalize_run when all are done."""
    journey_idx = state.get("current_journey_index", 0)
    journeys = state.get("journeys", [])

    if journey_idx < len(journeys):
        return "perceive"
    return "finalize_run"
