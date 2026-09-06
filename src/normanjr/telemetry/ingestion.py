"""Real-user telemetry ingestion for PostHog, Google Analytics, and RUM field data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from normanjr.domain.models import Journey


def ingest_telemetry_file(telemetry_path: Path) -> dict[str, Any]:
    """Parse real-user telemetry data and generate prioritized UX audit journeys."""
    if not telemetry_path.exists():
        raise FileNotFoundError(f"Telemetry file not found: {telemetry_path}")

    with open(telemetry_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support PostHog / GA4 / Custom RUM formats
    events = data if isinstance(data, list) else data.get("events", data.get("dropoffs", []))
    rum_metrics = data.get("rum_metrics", {}) if isinstance(data, dict) else {}

    extracted_journeys: list[Journey] = []
    high_dropoff_urls: list[str] = []

    if isinstance(data, dict) and "funnels" in data:
        for f_idx, funnel in enumerate(data["funnels"]):
            name = funnel.get("name", f"Funnel {f_idx+1}")
            steps = funnel.get("steps", [])
            dropoff_rate = funnel.get("dropoff_rate", 0.0)
            goal_desc = f"Audit high-dropoff user funnel: '{name}' (Drop-off: {dropoff_rate*100:.1f}%)"
            extracted_journeys.append(
                Journey(
                    journey_id=f"rum-j{f_idx+1}",
                    goal=goal_desc,
                    persona=f"Real user experiencing {dropoff_rate*100:.0f}% drop-off",
                )
            )
    else:
        # Generic event list or URLs
        for i, item in enumerate(events[:5]):
            target = item.get("path") or item.get("url") or item.get("event", f"Step {i+1}")
            dropoff = item.get("dropoff_count", item.get("exits", 0))
            if target:
                high_dropoff_urls.append(str(target))
                extracted_journeys.append(
                    Journey(
                        journey_id=f"rum-j{i+1}",
                        goal=f"Investigate high friction on page '{target}' ({dropoff} user exits)",
                        persona="Frustrated user drop-off pattern",
                    )
                )

    if not extracted_journeys:
        extracted_journeys.append(
            Journey(
                journey_id="rum-j1",
                goal="Audit high-priority user journeys from ingested telemetry",
            )
        )

    return {
        "telemetry_source": telemetry_path.name,
        "total_events_analyzed": len(events),
        "high_dropoff_targets": high_dropoff_urls,
        "rum_metrics": rum_metrics,
        "generated_journeys": [j.model_dump() for j in extracted_journeys],
    }
