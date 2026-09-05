"""Perceive node: captures DOM snapshot, screenshot, and element descriptors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from normanjr.audit.accessibility import parse_snapshot_elements
from normanjr.domain.models import PageObservation
from normanjr.domain.serialization import compute_state_fingerprint
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState
from normanjr.storage.artifacts import save_screenshot, save_snapshot


async def perceive_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Capture current page state, elements, and visual evidence."""
    journey_idx = state.get("current_journey_index", 0)
    journeys = state.get("journeys", [])
    journey = journeys[journey_idx] if journey_idx < len(journeys) else None
    journey_id = journey.journey_id if journey else "j0"
    step_no = state.get("current_step_number", 0)

    # 1. Take snapshot
    snapshot_text = await context.adapter.take_snapshot()
    snap_path, snap_hash = save_snapshot(
        context.repo.run_dir, snapshot_text, journey_id, step_no
    )

    # 2. Take screenshot
    screenshot_bytes = await context.adapter.take_screenshot()
    screenshot_path: str | None = None
    if screenshot_bytes:
        shot_path, _ = save_screenshot(
            context.repo.run_dir, screenshot_bytes, journey_id, step_no, suffix="state"
        )
        screenshot_path = str(shot_path)

    # 3. Parse elements
    elements = parse_snapshot_elements(snapshot_text)

    # 4. Get URL and title
    title = ""
    try:
        title_res = await context.adapter.evaluate_script("document.title")
        title = str(title_res).strip()
    except Exception:
        pass

    url = state.get("target_url", "")
    try:
        url_res = await context.adapter.evaluate_script("window.location.href")
        if url_res and str(url_res).startswith("http"):
            url = str(url_res).strip()
    except Exception:
        pass

    # 5. Compute state fingerprint
    fingerprint = compute_state_fingerprint(
        url=url,
        title=title,
        interactive_elements=elements,
    )

    obs_id = f"obs-{journey_id}-{step_no:03d}"
    obs = PageObservation(
        observation_id=obs_id,
        url=url,
        title=title,
        timestamp=datetime.now(timezone.utc).isoformat(),
        state_fingerprint=fingerprint,
        snapshot_hash=snap_hash,
        snapshot_path=str(snap_path),
        screenshot_path=screenshot_path,
        interactive_elements=elements,
    )

    context.repo.log_event("STATE_OBSERVED", {
        "observation_id": obs_id,
        "url": url,
        "title": title,
        "elements_count": len(elements),
        "fingerprint": fingerprint,
    })

    return {
        "current_observation": obs,
        "visited_state_fingerprints": [fingerprint],
    }
