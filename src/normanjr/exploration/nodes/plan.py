"""Plan node: proposes the next safe action using deterministic heuristics or model reasoning."""

from __future__ import annotations

from typing import Any

from normanjr.domain.enums import ActionType, RiskClass
from normanjr.domain.models import ProposedAction
from normanjr.exploration.context import AuditContext
from normanjr.exploration.state import AuditState


async def plan_node(state: AuditState, context: AuditContext) -> dict[str, Any]:
    """Propose one typed action toward the journey goal."""
    obs = state.get("current_observation")
    journey_idx = state.get("current_journey_index", 0)
    journeys = state.get("journeys", [])
    journey = journeys[journey_idx] if journey_idx < len(journeys) else None
    goal = journey.goal if journey else "explore site"

    if not obs or not obs.interactive_elements:
        return {
            "current_action": ProposedAction(
                action_type=ActionType.FINISH,
                rationale="No interactive elements found on page.",
                risk_class=RiskClass.LOW,
                source_observation_id=obs.observation_id if obs else "",
            )
        }

    # Deterministic candidate ranking:
    # 1. Look for actionable elements (buttons, links, inputs) with valid refs
    actionable = [
        e for e in obs.interactive_elements
        if e.ref and e.is_enabled and not e.ref.startswith("anon-")
    ]

    if not actionable:
        return {
            "current_action": ProposedAction(
                action_type=ActionType.FINISH,
                rationale="No actionable elements with valid snapshot references.",
                risk_class=RiskClass.LOW,
                source_observation_id=obs.observation_id,
            )
        }

    # 2. Try Model-driven action proposal if LLM client is available
    if context.llm_client:
        try:
            proposal = await context.llm_client.propose_action(
                goal=goal,
                observation=obs,
                candidate_elements=actionable,
            )
            matching_elem = None
            if proposal.target_ref:
                matching_elem = next((e for e in actionable if e.ref == proposal.target_ref), None)

            action_type_val = proposal.action_type.lower()
            try:
                action_type = ActionType(action_type_val)
            except ValueError:
                action_type = ActionType.CLICK

            if action_type == ActionType.FINISH or matching_elem:
                action = ProposedAction(
                    action_type=action_type,
                    target_ref=proposal.target_ref if matching_elem else None,
                    value=proposal.value,
                    rationale=f"[{context.llm_client.settings.requested_model}] {proposal.rationale}",
                    expected_change=proposal.expected_change,
                    risk_class=RiskClass.LOW,
                    source_observation_id=obs.observation_id,
                )
                context.repo.log_event("ACTION_PROPOSED", {
                    "action": action.action_type.value,
                    "target_ref": action.target_ref,
                    "target_name": matching_elem.name if matching_elem else None,
                    "rationale": action.rationale,
                    "model": context.llm_client.settings.requested_model,
                })
                return {"current_action": action}
        except Exception as e:
            context.repo.log_event("LLM_PLANNER_FALLBACK", {
                "error": str(e),
                "model": context.llm_client.settings.requested_model,
            })

    # 3. Deterministic candidate ranking fallback:
    # Match goal tokens against element names
    goal_tokens = [t.lower() for t in goal.split() if len(t) > 2]
    best_elem = None
    best_score = -1

    for elem in actionable:
        score = 0
        name_lower = elem.name.lower()
        for token in goal_tokens:
            if token in name_lower:
                score += 2
        # Prefer buttons and links
        if elem.role in ("button", "link"):
            score += 1
        if score > best_score:
            best_score = score
            best_elem = elem

    chosen = best_elem or actionable[0]


    # Decide action type
    if chosen.role in ("textbox", "searchbox"):
        action = ProposedAction(
            action_type=ActionType.TYPE,
            target_ref=chosen.ref,
            value="Jane Doe",
            rationale=f"Enter synthetic data into input '{chosen.name}'",
            expected_change="Input value populated",
            risk_class=RiskClass.LOW,
            source_observation_id=obs.observation_id,
        )
    else:
        action = ProposedAction(
            action_type=ActionType.CLICK,
            target_ref=chosen.ref,
            rationale=f"Click on {chosen.role} '{chosen.name}' to progress goal '{goal}'",
            expected_change="Page navigation or UI state change",
            risk_class=RiskClass.LOW,
            source_observation_id=obs.observation_id,
        )

    context.repo.log_event("ACTION_PROPOSED", {
        "action": action.action_type.value,
        "target_ref": action.target_ref,
        "target_name": chosen.name,
        "rationale": action.rationale,
    })

    return {
        "current_action": action,
    }
