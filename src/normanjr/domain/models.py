"""Domain models for NormanJr."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from normanjr.domain.enums import (
    ActionType,
    AuditStatus,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    JourneyStatus,
    RiskClass,
    TerminationReason,
)


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ElementDescriptor(BaseModel):
    ref: str
    role: str
    name: str = ""
    element_type: str = ""
    value: str | None = None
    bounding_box: BoundingBox | None = None
    is_visible: bool = True
    is_enabled: bool = True
    is_focusable: bool = True
    states: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str = ""


class ProposedAction(BaseModel):
    action_type: ActionType
    target_ref: str | None = None
    value: str | None = None
    rationale: str = ""
    expected_change: str = ""
    risk_class: RiskClass = RiskClass.LOW
    source_observation_id: str = ""


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    reason_code: str
    requires_approval: bool = False
    policy_version: str = "1.0.0"


class ExecutionRecord(BaseModel):
    execution_id: str
    action: ProposedAction
    mcp_tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = True
    error_class: str | None = None
    error_message: str | None = None
    before_observation_id: str | None = None
    after_observation_id: str | None = None


class PageObservation(BaseModel):
    observation_id: str
    url: str
    title: str = ""
    timestamp: str
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 800})
    state_fingerprint: str = ""
    snapshot_hash: str = ""
    snapshot_path: str | None = None
    screenshot_path: str | None = None
    interactive_elements: list[ElementDescriptor] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    axe_summary: dict[str, Any] | None = None
    console_errors: list[str] = Field(default_factory=list)
    failed_requests: list[dict[str, Any]] = Field(default_factory=list)


class Finding(BaseModel):
    finding_id: str
    root_cause_key: str
    source: FindingSource
    criterion_id: str
    category_id: str
    severity: FindingSeverity
    status: FindingStatus = FindingStatus.CONFIRMED
    confidence: str = "high"  # "high", "medium", "low"
    score_penalty: int = 0
    scoring_eligible: bool = True
    journey_id: str | None = None
    state_id: str | None = None
    title: str
    description: str = ""
    user_impact: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    target_selector: str | None = None
    target_name: str | None = None
    screenshot_path: str | None = None
    measured_data: dict[str, Any] = Field(default_factory=dict)
    recommendation: str = ""
    verification_advice: str = ""
    occurrences: int = 1


class CategoryScore(BaseModel):
    category_id: str
    category_name: str
    weight: float
    raw_score: float
    weighted_score: float
    findings_count: int
    total_penalty: int


class AuditCoverage(BaseModel):
    journeys_planned: int = 0
    journeys_completed: int = 0
    unique_states: int = 0
    unique_routes: int = 0
    interactive_elements_tested: int = 0
    axe_rules_run: int = 0
    visual_criteria_assessed: int = 0
    states_skipped: int = 0


class AuditScore(BaseModel):
    overall_score: float
    category_scores: list[CategoryScore] = Field(default_factory=list)
    journey_scores: dict[str, float] = Field(default_factory=dict)
    confidence: str = "medium"
    coverage: AuditCoverage = Field(default_factory=AuditCoverage)


class StepRecord(BaseModel):
    step_id: str
    journey_id: str
    step_number: int
    before_observation_id: str
    proposed_action: ProposedAction
    policy_decision: PolicyDecision
    execution: ExecutionRecord | None = None
    after_observation_id: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    created_at: str


class Journey(BaseModel):
    journey_id: str
    goal: str
    persona: str | None = None
    status: JourneyStatus = JourneyStatus.NOT_STARTED
    start_state_id: str | None = None
    end_state_id: str | None = None
    steps: list[StepRecord] = Field(default_factory=list)
    completion_status: str | None = None
    termination_reason: TerminationReason | None = None


class AuditRun(BaseModel):
    run_id: str
    schema_version: str = "1.0"
    target_url: str
    created_at: str
    completed_at: str | None = None
    status: AuditStatus = AuditStatus.INITIALIZED
    termination_reason: TerminationReason | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    journeys: list[Journey] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    score: AuditScore | None = None
    summary: str | None = None
