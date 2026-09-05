"""UX Rubric loader and schema definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

from normanjr.domain.enums import FindingSeverity


class RubricCategory(BaseModel):
    id: str
    label: str
    weight: float


class RubricCriterion(BaseModel):
    id: str
    category_id: str
    title: str
    authority: str
    default_severity: FindingSeverity
    allowed_severities: list[FindingSeverity] = Field(default_factory=list)
    scope: str = "component"
    scoring_eligible: bool = True


class RubricDefinition(BaseModel):
    schema_version: str = "1.0"
    rubric_id: str
    rubric_version: str
    categories: list[RubricCategory]
    severity_penalties: dict[FindingSeverity, int]
    criteria: list[RubricCriterion]

    @model_validator(mode="after")
    def validate_weights(self) -> RubricDefinition:
        total_weight = sum(c.weight for c in self.categories)
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Rubric category weights must sum to 1.0, got {total_weight:.3f}")
        return self

    def get_criterion(self, criterion_id: str) -> RubricCriterion | None:
        """Find criterion by ID."""
        for c in self.criteria:
            if c.id == criterion_id:
                return c
        return None

    def get_penalty(self, severity: FindingSeverity) -> int:
        """Get fixed numeric penalty for severity level."""
        return self.severity_penalties.get(severity, 0)

    def get_category(self, category_id: str) -> RubricCategory | None:
        """Find category by ID."""
        for cat in self.categories:
            if cat.id == category_id:
                return cat
        return None


def load_rubric(rubric_path: str | Path = "config/rubrics/ux-rubric-v1.yaml") -> RubricDefinition:
    """Load and validate UX rubric YAML."""
    path = Path(rubric_path)
    if not path.exists():
        raise FileNotFoundError(f"Rubric file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Convert severity_penalties keys to FindingSeverity enum
    if "severity_penalties" in data:
        penalties = {}
        for k, v in data["severity_penalties"].items():
            penalties[FindingSeverity(k)] = v
        data["severity_penalties"] = penalties

    return RubricDefinition(**data)
