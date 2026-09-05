"""Finalize run node: deduplicates findings, computes scores, and writes canonical result.json."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from normanjr.audit.deduplication import deduplicate_findings
from normanjr.audit.scoring import calculate_audit_score
from normanjr.domain.enums import AuditStatus, TerminationReason
from normanjr.domain.models import AuditRun
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState
from normanjr.storage.manifest import generate_run_manifest


async def finalize_run_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Compile final audit results, calculate scores, and persist canonical artifacts."""
    raw_findings = state.get("all_findings", [])
    deduped = deduplicate_findings(raw_findings)

    journeys = state.get("journeys", [])
    unique_states = len(set(state.get("visited_state_fingerprints", [])))

    score = calculate_audit_score(
        findings=deduped,
        rubric=context.rubric,
        journeys=journeys,
        unique_states_count=unique_states,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    audit_run = AuditRun(
        run_id=state.get("run_id", context.repo.run_id),
        target_url=state.get("target_url", ""),
        created_at=now_iso,
        completed_at=now_iso,
        status=AuditStatus.COMPLETED,
        termination_reason=state.get("termination_reason", TerminationReason.ALL_JOURNEYS_FINISHED),
        config=context.config.redacted_dict(),
        journeys=journeys,
        findings=deduped,
        score=score,
    )

    # 1. Save canonical result.json
    context.repo.save_result(audit_run)

    # 2. Generate manifest.json
    generate_run_manifest(context.repo.run_dir, rubric_version=context.rubric.rubric_version)

    context.repo.log_event("RUN_COMPLETED", {
        "overall_score": score.overall_score,
        "findings_count": len(deduped),
        "confidence": score.confidence,
    })

    return {
        "status": AuditStatus.COMPLETED,
        "all_findings": deduped,
    }
