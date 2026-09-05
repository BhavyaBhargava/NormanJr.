"""Enumeration types for NormanJr domain entities."""

from enum import Enum


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    PRESS_KEY = "press_key"
    HOVER = "hover"
    SCROLL = "scroll"
    BACK = "back"
    WAIT_FOR = "wait_for"
    NAVIGATE = "navigate"
    FINISH = "finish"
    BLOCKED = "blocked"


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"


class FindingSource(str, Enum):
    DETERMINISTIC = "deterministic"
    AXE = "axe"
    MODEL_SUPPORTED = "model_supported"
    MANUAL_REVIEW = "manual_review"


class FindingStatus(str, Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"
    DUPLICATE = "duplicate"
    SUPPRESSED = "suppressed"
    INVALID = "invalid"


class JourneyStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class AuditStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class TerminationReason(str, Enum):
    GOAL_COMPLETED = "goal_completed"
    FINAL_SUBMIT_BOUNDARY = "final_submit_boundary"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CAPTCHA_CHALLENGE = "captcha_challenge"
    NO_SAFE_ACTIONS = "no_safe_actions"
    REPEATED_STATE_LOOP = "repeated_state_loop"
    TARGET_OR_TOOL_ERROR = "target_or_tool_error"
    BUDGET_EXHAUSTED = "budget_exhausted"
    USER_INTERRUPT = "user_interrupt"
    ALL_JOURNEYS_FINISHED = "all_journeys_finished"
