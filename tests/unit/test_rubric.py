"""Unit tests for rubric loading and validation."""

from normanjr.audit.rubric import load_rubric
from normanjr.domain.enums import FindingSeverity


def test_load_default_rubric():
    rubric = load_rubric()
    assert rubric.rubric_id == "normanjr-ux"
    assert len(rubric.categories) == 9
    assert len(rubric.criteria) >= 15

    # Check penalties
    assert rubric.get_penalty(FindingSeverity.CRITICAL) == 15
    assert rubric.get_penalty(FindingSeverity.MAJOR) == 8
    assert rubric.get_penalty(FindingSeverity.MINOR) == 3
    assert rubric.get_penalty(FindingSeverity.OBSERVATION) == 0

    # Check criterion lookup
    target_size = rubric.get_criterion("WCAG-2.5.8-TARGET-SIZE")
    assert target_size is not None
    assert target_size.category_id == "accessibility_operability"
    assert target_size.default_severity == FindingSeverity.MAJOR
