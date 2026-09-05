"""Audit package for NormanJr."""

from normanjr.audit.accessibility import parse_snapshot_elements
from normanjr.audit.axe_runner import run_axe_scan
from normanjr.audit.deterministic import run_deterministic_audits
from normanjr.audit.metrics import (
    DOM_FORM_LABEL_SCRIPT,
    DOM_HEADING_HIERARCHY_SCRIPT,
    DOM_IMAGE_ALT_SCRIPT,
    DOM_TARGET_SIZE_SCRIPT,
)
from normanjr.audit.rubric import RubricCategory, RubricCriterion, RubricDefinition, load_rubric

__all__ = [
    "DOM_FORM_LABEL_SCRIPT",
    "DOM_HEADING_HIERARCHY_SCRIPT",
    "DOM_IMAGE_ALT_SCRIPT",
    "DOM_TARGET_SIZE_SCRIPT",
    "RubricCategory",
    "RubricCriterion",
    "RubricDefinition",
    "load_rubric",
    "parse_snapshot_elements",
    "run_axe_scan",
    "run_deterministic_audits",
]
