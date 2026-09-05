"""Evaluate node: assesses transition heuristics and feedback timeliness."""

from __future__ import annotations

from typing import Any

from normanjr.domain.enums import FindingSeverity, FindingSource, FindingStatus
from normanjr.domain.models import Finding
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def evaluate_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Assess whether the executed transition violated UX feedback or affordance principles."""
    exec_record = state.get("current_execution")
    if not exec_record:
        return {}

    findings: list[Finding] = []
    journey_idx = state.get("current_journey_index", 0)
    journeys = state.get("journeys", [])
    journey = journeys[journey_idx] if journey_idx < len(journeys) else None
    journey_id = journey.journey_id if journey else "j0"
    step_no = state.get("current_step_number", 0)

    # 1. Action latency > 3000ms check (Feedback delayed)
    if exec_record.duration_ms > 3000:
        f = Finding(
            finding_id=f"eval-latency-{step_no:03d}",
            root_cause_key=f"latency:{exec_record.action.action_type.value}:{exec_record.action.target_ref}",
            source=FindingSource.DETERMINISTIC,
            criterion_id="NORMAN-FEEDBACK-IMMEDIATE",
            category_id="feedback_status",
            severity=FindingSeverity.MINOR,
            status=FindingStatus.CONFIRMED,
            confidence="high",
            score_penalty=3,
            scoring_eligible=True,
            journey_id=journey_id,
            title=f"Slow Interaction Response ({exec_record.duration_ms:.0f}ms)",
            description=f"Action '{exec_record.action.rationale}' took {exec_record.duration_ms:.0f}ms to respond, exceeding the recommended 1000ms limit without clear loading state.",
            user_impact="Users may believe the interface is frozen or click repeatedly, creating duplicate actions.",
            expected_behavior="Actions requiring more than 1000ms should display an immediate loading indicator or skeleton screen.",
            actual_behavior=f"Action took {exec_record.duration_ms:.0f}ms.",
            measured_data={"duration_ms": exec_record.duration_ms},
            recommendation="Introduce immediate optimistic UI feedback or a visible loading spinner.",
            verification_advice="Measure time to first visual response after user action in browser performance profile.",
        )
        findings.append(f)

    # 2. Tool failure check
    if not exec_record.success and exec_record.error_class:
        f = Finding(
            finding_id=f"eval-tool-err-{step_no:03d}",
            root_cause_key=f"tool-err:{exec_record.error_class}",
            source=FindingSource.DETERMINISTIC,
            criterion_id="NIELSEN-USER-CONTROL-FREEDOM",
            category_id="task_completion",
            severity=FindingSeverity.MAJOR,
            status=FindingStatus.CONFIRMED,
            confidence="high",
            score_penalty=8,
            scoring_eligible=True,
            journey_id=journey_id,
            title=f"Interaction Failed: {exec_record.error_class}",
            description=f"Browser action failed: {exec_record.error_message}",
            user_impact="Prevents user from completing the intended task flow.",
            expected_behavior="Target element should respond to user action without throwing browser errors.",
            actual_behavior=f"Action failed with {exec_record.error_class}: {exec_record.error_message}",
            measured_data={"error_class": exec_record.error_class, "error_message": exec_record.error_message},
            recommendation="Ensure target control is visible, unblocked by overlays, and interactable.",
            verification_advice="Verify control responds to click and keyboard activation in browser.",
        )
        findings.append(f)

    # 3. Model heuristic evaluation if LLM client is available and not in low-call budget lock
    obs = state.get("current_observation")
    if context.llm_client and obs:
        try:
            eval_resp = await context.llm_client.evaluate_heuristics(
                observation=obs,
                rubric_criteria=context.rubric.criteria,
            )
            sev_map = {
                "minor": FindingSeverity.MINOR,
                "moderate": FindingSeverity.MODERATE,
                "major": FindingSeverity.MAJOR,
                "critical": FindingSeverity.CRITICAL,
            }
            pen_map = {
                FindingSeverity.MINOR: 2,
                FindingSeverity.MODERATE: 5,
                FindingSeverity.MAJOR: 8,
                FindingSeverity.CRITICAL: 15,
            }
            for i, hf in enumerate(eval_resp.findings):
                sev = sev_map.get(hf.severity.lower(), FindingSeverity.MINOR)
                f = Finding(
                    finding_id=f"eval-heuristic-{step_no:03d}-{i+1:02d}",
                    root_cause_key=f"heuristic:{hf.criterion_id}:{hf.title[:30]}",
                    source=FindingSource.MODEL_REASONING,
                    criterion_id=hf.criterion_id,
                    category_id="cognitive_clarity",
                    severity=sev,
                    status=FindingStatus.CONFIRMED,
                    confidence="medium",
                    score_penalty=pen_map[sev],
                    scoring_eligible=True,
                    journey_id=journey_id,
                    title=hf.title,
                    description=hf.description,
                    user_impact=hf.user_impact,
                    expected_behavior="User interface follows UX usability and clarity principles.",
                    actual_behavior=hf.description,
                    recommendation=hf.recommendation,
                    verification_advice="Verify usability against Nielsen and Norman UX principles.",
                )
                findings.append(f)
        except Exception as e:
            context.repo.log_event("LLM_EVALUATION_ERROR", {
                "error": str(e),
                "model": context.llm_client.settings.requested_model,
            })

    return {
        "all_findings": findings,
    }

