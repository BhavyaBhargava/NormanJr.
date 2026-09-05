"""State definition and reducers for the LangGraph audit workflow."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from normanjr.domain.enums import AuditStatus, TerminationReason
from normanjr.domain.models import (
    ExecutionRecord,
    Finding,
    Journey,
    PageObservation,
    PolicyDecision,
    ProposedAction,
)


def replace_value(old_val: Any, new_val: Any) -> Any:
    """Replacement reducer for non-accumulating fields."""
    return new_val


class AuditState(TypedDict, total=False):
    run_id: str
    target_url: str
    journeys: list[Journey]
    current_journey_index: int
    current_step_number: int
    current_observation: PageObservation | None
    current_action: ProposedAction | None
    current_policy_decision: PolicyDecision | None
    current_execution: ExecutionRecord | None
    all_findings: Annotated[list[Finding], operator.add]
    visited_state_fingerprints: Annotated[list[str], operator.add]
    loop_count: int
    status: AuditStatus
    termination_reason: TerminationReason | None
    budget_used_steps: int
