"""Deterministic scoring and coverage calculation."""

from __future__ import annotations

from normanjr.audit.rubric import RubricDefinition
from normanjr.domain.enums import FindingStatus
from normanjr.domain.models import AuditCoverage, AuditScore, CategoryScore, Finding, Journey


def calculate_audit_score(
    findings: list[Finding],
    rubric: RubricDefinition,
    journeys: list[Journey],
    unique_states_count: int = 0,
) -> AuditScore:
    """
    Calculate deterministic category scores, weighted overall score, journey scores,
    and transparent coverage metrics.
    """
    # Only confirmed and scoring_eligible findings affect the score
    eligible_findings = [
        f for f in findings
        if f.scoring_eligible and f.status == FindingStatus.CONFIRMED
    ]

    category_scores: list[CategoryScore] = []
    total_weight = 0.0
    weighted_sum = 0.0

    for cat in rubric.categories:
        cat_findings = [f for f in eligible_findings if f.category_id == cat.id]
        total_penalty = sum(f.score_penalty for f in cat_findings)
        raw_score = max(0.0, 100.0 - total_penalty)
        weighted_score = raw_score * cat.weight

        category_scores.append(
            CategoryScore(
                category_id=cat.id,
                category_name=cat.label,
                weight=cat.weight,
                raw_score=round(raw_score, 1),
                weighted_score=round(weighted_score, 2),
                findings_count=len(cat_findings),
                total_penalty=total_penalty,
            )
        )
        total_weight += cat.weight
        weighted_sum += weighted_score

    overall_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else 100.0

    # Journey scores
    journey_scores: dict[str, float] = {}
    for j in journeys:
        j_findings = [f for f in eligible_findings if f.journey_id == j.journey_id]
        j_penalty = sum(f.score_penalty for f in j_findings)
        journey_scores[j.journey_id] = round(max(0.0, 100.0 - j_penalty), 1)

    # Coverage metrics
    completed_journeys = sum(1 for j in journeys if j.status.value == "completed")
    coverage = AuditCoverage(
        journeys_planned=len(journeys),
        journeys_completed=completed_journeys,
        unique_states=unique_states_count,
        unique_routes=len(journeys),
        interactive_elements_tested=sum(len(j.steps) for j in journeys),
        axe_rules_run=len([f for f in findings if f.source.value == "axe"]),
    )

    # Confidence calculation: High if deterministic/axe findings represent >= 80%
    deterministic_count = sum(1 for f in findings if f.source.value in ("deterministic", "axe"))
    if not findings or (deterministic_count / len(findings) >= 0.75):
        confidence = "high"
    else:
        confidence = "medium"

    return AuditScore(
        overall_score=overall_score,
        category_scores=category_scores,
        journey_scores=journey_scores,
        confidence=confidence,
        coverage=coverage,
    )
