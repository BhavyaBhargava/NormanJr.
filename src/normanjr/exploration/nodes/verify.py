"""Verify node: captures after-state and detects UI deltas or lack of feedback."""

from __future__ import annotations

from typing import Any

from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def verify_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Observe the post-action state and detect UI transitions."""
    exec_record = state.get("current_execution")
    if not exec_record or not exec_record.success:
        return {}

    # Wait settling period
    await context.adapter.wait_for(time_ms=500)

    # Capture after snapshot
    after_snapshot = await context.adapter.take_snapshot()

    obs = state.get("current_observation")
    before_snap_hash = obs.snapshot_hash if obs else ""

    # Check for delta
    import hashlib
    after_hash = hashlib.sha256(after_snapshot.encode("utf-8")).hexdigest()
    has_delta = before_snap_hash != after_hash

    context.repo.log_event("STATE_VERIFIED", {
        "execution_id": exec_record.execution_id,
        "has_delta": has_delta,
        "before_hash": before_snap_hash,
        "after_hash": after_hash,
    })

    return {}
