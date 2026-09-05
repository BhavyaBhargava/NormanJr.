"""Finalize journey node: records completion status and advances to next journey."""

from __future__ import annotations

from typing import Any

from normanjr.domain.enums import JourneyStatus, TerminationReason
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def finalize_journey_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Finalize current journey record and prepare for next journey."""
    journey_idx = state.get("current_journey_index", 0)
    journeys = list(state.get("journeys", []))
    reason = state.get("termination_reason")

    if journey_idx < len(journeys):
        curr_journey = journeys[journey_idx]
        if reason == TerminationReason.GOAL_COMPLETED:
            curr_journey.status = JourneyStatus.COMPLETED
        elif reason in (TerminationReason.BLOCKED_BY_POLICY, TerminationReason.FINAL_SUBMIT_BOUNDARY):
            curr_journey.status = JourneyStatus.BLOCKED
        else:
            curr_journey.status = JourneyStatus.PARTIAL

        curr_journey.termination_reason = reason
        journeys[journey_idx] = curr_journey

    context.repo.log_event("JOURNEY_FINALIZED", {
        "journey_index": journey_idx,
        "status": curr_journey.status.value if journey_idx < len(journeys) else "unknown",
        "reason": reason.value if reason else "completed",
    })

    return {
        "journeys": journeys,
        "current_journey_index": journey_idx + 1,
        "current_step_number": 0,
        "loop_count": 0,
        "termination_reason": None,
    }
