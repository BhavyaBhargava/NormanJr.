"""Check progress node: evaluates goals, loops, and budget boundaries."""

from __future__ import annotations

from typing import Any

from normanjr.domain.enums import TerminationReason
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def check_progress_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Check whether the current journey should continue or terminate."""
    obs = state.get("current_observation")
    step_no = state.get("current_step_number", 0)
    max_steps = context.config.exploration.max_steps_per_journey
    max_visits = context.config.exploration.max_repeated_state_visits

    visited = state.get("visited_state_fingerprints", [])

    # 1. Step budget check
    if step_no >= max_steps:
        return {
            "termination_reason": TerminationReason.BUDGET_EXHAUSTED,
        }

    # 2. Loop detection check
    if obs and obs.state_fingerprint:
        occurrences = visited.count(obs.state_fingerprint)
        if occurrences > max_visits:
            context.repo.log_event("LOOP_DETECTED", {
                "fingerprint": obs.state_fingerprint,
                "occurrences": occurrences,
            })
            return {
                "termination_reason": TerminationReason.REPEATED_STATE_LOOP,
                "loop_count": state.get("loop_count", 0) + 1,
            }

    return {}
