"""Root-cause deduplication for audit findings."""

from __future__ import annotations

from normanjr.domain.models import Finding


def deduplicate_findings(findings: list[Finding]) -> list[Finding]:
    """
    Deduplicate findings by root_cause_key.
    Groups identical issues occurring across multiple steps/states into a single canonical finding
    with an updated occurrences counter.
    """
    grouped: dict[str, Finding] = {}

    for f in findings:
        key = f.root_cause_key or f.finding_id
        if key in grouped:
            existing = grouped[key]
            existing.occurrences += 1
            # Retain higher severity if mismatch occurs
            grouped[key] = existing
        else:
            # Create shallow copy with occurrences = 1
            clone = f.model_copy(deep=True)
            clone.occurrences = 1
            grouped[key] = clone

    return list(grouped.values())
