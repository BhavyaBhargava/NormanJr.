"""Action safety policy gateway."""

from __future__ import annotations

import re
from typing import NamedTuple

from normanjr.config import SafetySettings
from normanjr.domain.enums import ActionType, RiskClass
from normanjr.domain.models import PolicyDecision, ProposedAction

# Regex patterns for inherently destructive keywords in action text / target names
DESTRUCTIVE_PATTERN = re.compile(
    r"\b(delete|remove|destroy|erase|drop|terminate|cancel\s+account|deactivate)\b",
    re.IGNORECASE,
)
PURCHASE_PATTERN = re.compile(
    r"\b(buy|purchase|checkout|pay\s+now|place\s+order|confirm\s+payment|subscribe)\b",
    re.IGNORECASE,
)
SUBMIT_PATTERN = re.compile(
    r"\b(submit|complete|finish|send|confirm)\b",
    re.IGNORECASE,
)


class ActionPolicy:
    """Enforces safety constraints and deterministic approval decisions on browser actions."""

    def __init__(self, safety: SafetySettings) -> None:
        self.safety = safety

    def evaluate(self, action: ProposedAction, target_name: str = "") -> PolicyDecision:
        """Evaluate whether a proposed action is permitted, denied, or requires approval."""
        combined_text = f"{action.rationale} {action.expected_change} {target_name}".strip()

        # 1. Check for blocked actions
        if action.action_type == ActionType.BLOCKED:
            return PolicyDecision(
                allowed=False,
                reason="Action is explicitly marked as blocked.",
                reason_code="ACTION_BLOCKED",
            )

        # 2. Check for inherently destructive actions (e.g. account deletion)
        if not self.safety.allow_destructive_actions and DESTRUCTIVE_PATTERN.search(combined_text):
            return PolicyDecision(
                allowed=False,
                reason="Destructive actions (delete/remove/terminate) are blocked by policy.",
                reason_code="DESTRUCTIVE_ACTION_BLOCKED",
            )

        # 3. Check for financial/payment actions
        if PURCHASE_PATTERN.search(combined_text):
            return PolicyDecision(
                allowed=False,
                reason="Financial transactions and purchase submissions are strictly blocked.",
                reason_code="PURCHASE_ACTION_BLOCKED",
            )

        # 4. Check for final form submissions
        if action.action_type == ActionType.CLICK and SUBMIT_PATTERN.search(target_name):
            if not self.safety.allow_final_submit:
                return PolicyDecision(
                    allowed=False,
                    reason="Final form submission is blocked by default safety policy.",
                    reason_code="FINAL_SUBMIT_BLOCKED",
                )

        # 5. Check uploads / downloads
        if action.action_type == ActionType.TYPE and action.value and action.value.startswith("file://"):
            if not self.safety.allow_upload:
                return PolicyDecision(
                    allowed=False,
                    reason="File uploads are blocked by safety policy.",
                    reason_code="UPLOAD_BLOCKED",
                )

        # 6. Safe / allowed
        return PolicyDecision(
            allowed=True,
            reason="Action permitted under current safety policy.",
            reason_code="ALLOWED",
        )
