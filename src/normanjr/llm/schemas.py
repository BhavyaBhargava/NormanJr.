"""Pydantic schemas for structured outputs from OpenRouter models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from normanjr.domain.enums import ActionType, FindingSeverity


class ActionProposalResponse(BaseModel):
    """Schema for model-planned next action."""
    action_type: ActionType
    target_ref: str | None = None
    value: str | None = None
    rationale: str
    expected_change: str


class HeuristicFindingProposal(BaseModel):
    """Schema for a qualitative heuristic finding proposed by the model."""
    criterion_id: str
    title: str
    description: str
    user_impact: str
    severity: FindingSeverity
    target_ref: str | None = None
    recommendation: str
    confidence: str = "medium"  # "high", "medium", "low"


class HeuristicEvaluationResponse(BaseModel):
    """Schema for state-level heuristic evaluation."""
    findings: list[HeuristicFindingProposal] = Field(default_factory=list)


class JourneyProposal(BaseModel):
    """Schema for a generated safe user journey."""
    goal: str
    persona: str = "Standard user exploring website functionality."
    rationale: str


class JourneyListResponse(BaseModel):
    """Schema for list of generated journeys."""
    journeys: list[JourneyProposal] = Field(default_factory=list)
