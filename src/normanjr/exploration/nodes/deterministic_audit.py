"""Deterministic audit node: runs in-browser metric scripts and axe-core scan."""

from __future__ import annotations

from typing import Any

from normanjr.audit.deterministic import run_deterministic_audits
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState
from normanjr.storage.artifacts import save_metrics


async def deterministic_audit_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Execute DOM metric scripts and axe-core rules on current observation."""
    journey_idx = state.get("current_journey_index", 0)
    journeys = state.get("journeys", [])
    journey = journeys[journey_idx] if journey_idx < len(journeys) else None
    journey_id = journey.journey_id if journey else "j0"
    step_no = state.get("current_step_number", 0)

    obs = state.get("current_observation")
    state_id = obs.observation_id if obs else f"s{step_no}"

    # Run deterministic audits
    findings, metrics = await run_deterministic_audits(
        context.adapter,
        journey_id=journey_id,
        state_id=state_id,
        run_axe=True,
    )

    # Save metrics artifact
    save_metrics(context.repo.run_dir, metrics, journey_id, step_no, prefix="dom")

    context.repo.log_event("DETERMINISTIC_AUDIT_COMPLETED", {
        "state_id": state_id,
        "findings_count": len(findings),
        "metrics": metrics,
    })

    return {
        "all_findings": findings,
    }
