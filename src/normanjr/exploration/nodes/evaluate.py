"""Evaluate node: assesses transition heuristics, journey complexity, and feedback timeliness."""

from __future__ import annotations

from typing import Any

from normanjr.domain.enums import FindingSeverity, FindingSource, FindingStatus
from normanjr.domain.models import Finding
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def evaluate_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Assess whether the executed transition violated UX feedback, journey complexity, or affordance principles."""
    exec_record = state.get("current_execution")
    if not exec_record:
        return {}

    findings: list[Finding] = []
    journey_idx = state.get("current_journey_index", 0)
    journeys = state.get("journeys", [])
    journey = journeys[journey_idx] if journey_idx < len(journeys) else None
    journey_id = journey.journey_id if journey else "j0"
    journey_goal = journey.goal if journey else "Exploration Goal"
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

    # 3. User Journey Length & Complexity / Cognitive Fatigue Check
    existing_findings = state.get("all_findings", [])
    has_journey_friction = any(
        f.journey_id == journey_id and f.criterion_id == "COGNITIVE-JOURNEY-COMPLEXITY" and f.severity == FindingSeverity.MINOR
        for f in existing_findings
    )
    has_journey_fatigue = any(
        f.journey_id == journey_id and f.criterion_id == "COGNITIVE-JOURNEY-COMPLEXITY" and f.severity == FindingSeverity.MAJOR
        for f in existing_findings
    )

    if step_no >= 8 and not has_journey_fatigue:
        f = Finding(
            finding_id=f"eval-journey-fatigue-{journey_id}-{step_no:03d}",
            root_cause_key=f"journey-complexity:{journey_id}:major",
            source=FindingSource.DETERMINISTIC,
            criterion_id="COGNITIVE-JOURNEY-COMPLEXITY",
            category_id="cognitive_load",
            severity=FindingSeverity.MAJOR,
            status=FindingStatus.CONFIRMED,
            confidence="high",
            score_penalty=8,
            scoring_eligible=True,
            journey_id=journey_id,
            title=f"Excessively Long & Complex Journey ({step_no} Steps — High Drop-off Risk)",
            description=f"Journey '{journey_goal}' reached {step_no} interaction steps. Overly long and complex flows violate Hick's Law, increase interaction cost, and cause user fatigue and abandonment.",
            user_impact="Users find the application non-intuitive and lose interest or abandon the journey before reaching their goal.",
            expected_behavior="User journeys should be concise, progressive, and completed in minimal steps.",
            actual_behavior=f"Journey has required {step_no} steps so far.",
            measured_data={"journey_id": journey_id, "step_count": step_no, "goal": journey_goal},
            recommendation="Streamline multi-step workflows: eliminate redundant branching, batch related fields, use progressive disclosure, and provide clear step indicators.",
            verification_advice="Conduct user flow funnel audit to identify where interaction steps can be merged or automated.",
        )
        findings.append(f)
    elif step_no >= 5 and not has_journey_friction and not has_journey_fatigue:
        f = Finding(
            finding_id=f"eval-journey-friction-{journey_id}-{step_no:03d}",
            root_cause_key=f"journey-complexity:{journey_id}:minor",
            source=FindingSource.DETERMINISTIC,
            criterion_id="COGNITIVE-JOURNEY-COMPLEXITY",
            category_id="cognitive_load",
            severity=FindingSeverity.MINOR,
            status=FindingStatus.CONFIRMED,
            confidence="high",
            score_penalty=3,
            scoring_eligible=True,
            journey_id=journey_id,
            title=f"Journey Step Count Exceeds 5 Steps (Potential User Friction)",
            description=f"Journey '{journey_goal}' has reached 5 interaction steps. Users may experience friction and diminishing interest if progress is not clearly communicated.",
            user_impact="Increased cognitive friction may lead users to perceive the workflow as cumbersome.",
            expected_behavior="Primary tasks should provide clear progress landmarks and require minimal friction.",
            actual_behavior=f"Journey reached {step_no} steps.",
            measured_data={"journey_id": journey_id, "step_count": step_no, "goal": journey_goal},
            recommendation="Introduce a visible stepper/progress bar and reduce non-essential inputs.",
            verification_advice="Review user journey steps against benchmark shortest-path flows.",
        )
        findings.append(f)

    # 4. Model heuristic evaluation if LLM client is available (evaluated once per unique state)
    obs = state.get("current_observation")
    existing_model_findings = [f for f in state.get("all_findings", []) if f.source == FindingSource.MODEL_SUPPORTED]
    already_evaluated_state = any(f.journey_id == journey_id and obs and f.measured_data.get("state_fingerprint") == obs.state_fingerprint for f in existing_model_findings)

    if context.llm_client and obs and not already_evaluated_state:
        try:
            import asyncio
            eval_resp = await asyncio.wait_for(
                context.llm_client.evaluate_heuristics(
                    observation=obs,
                    rubric_criteria=context.rubric.criteria,
                ),
                timeout=10.0,
            )
            sev_map = {
                "minor": FindingSeverity.MINOR,
                "moderate": FindingSeverity.MAJOR,
                "major": FindingSeverity.MAJOR,
                "critical": FindingSeverity.CRITICAL,
            }
            pen_map = {
                FindingSeverity.MINOR: 2,
                FindingSeverity.MAJOR: 8,
                FindingSeverity.CRITICAL: 15,
                FindingSeverity.OBSERVATION: 0,
            }
            for i, hf in enumerate(eval_resp.findings):
                sev = sev_map.get(hf.severity.lower(), FindingSeverity.MINOR)
                f = Finding(
                    finding_id=f"eval-heuristic-{step_no:03d}-{i+1:02d}",
                    root_cause_key=f"heuristic:{hf.criterion_id}:{hf.title[:30]}",
                    source=FindingSource.MODEL_SUPPORTED,
                    criterion_id=hf.criterion_id,
                    category_id="cognitive_load",
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
                    measured_data={"state_fingerprint": obs.state_fingerprint},
                    recommendation=hf.recommendation,
                    verification_advice="Verify usability against Nielsen and Norman UX principles.",
                )
                findings.append(f)
        except Exception as e:
            context.repo.log_event("LLM_EVALUATION_SKIPPED", {
                "reason": str(e),
                "model": context.llm_client.settings.requested_model,
            })

    return {
        "all_findings": findings,
    }
