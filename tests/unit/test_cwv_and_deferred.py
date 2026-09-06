"""Unit tests for Core Web Vitals, Journey Complexity, and Deferred Capabilities."""

import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock

from normanjr.audit.deterministic import run_deterministic_audits
from normanjr.audit.rubric import load_rubric
from normanjr.domain.enums import ActionType, FindingSeverity, FindingSource, FindingStatus, RiskClass
from normanjr.domain.models import ExecutionRecord, Finding, Journey, PageObservation, ProposedAction
from normanjr.exploration.context import AuditContext
from normanjr.exploration.nodes.evaluate import evaluate_node
from normanjr.exploration.synthetic_data import generate_synthetic_persona, match_synthetic_value
from normanjr.reporting.comparator import compare_runs, format_comparison_markdown
from normanjr.reporting.patcher import generate_remediation_patches


@pytest.mark.asyncio
async def test_cwv_lcp_and_cls_checks():
    """Verify deterministic evaluation of Google Core Web Vitals thresholds."""
    mock_adapter = AsyncMock()
    # Mock evaluate_script responses
    mock_adapter.evaluate_script.side_effect = [
        "[]",  # target sizes
        "[]",  # form labels
        "[]",  # image alts
        '{"skips": []}',  # headings
        json.dumps({  # CWV data
            "pageLoadTimeSec": 4.5,
            "ttfbSec": 0.4,
            "fcpSec": 1.2,
            "lcpSec": 4.2,  # > 4.0s (Poor)
            "clsValue": 0.25,  # > 0.1 (Unstable)
            "maxInteractionLatencyMs": 250,  # > 200ms (Sluggish)
            "htmlLang": "",  # Missing lang
        }),
    ]
    mock_adapter.get_console_messages.return_value = []

    findings, metrics = await run_deterministic_audits(mock_adapter, run_axe=False)

    crit_ids = [f.criterion_id for f in findings]
    assert "CWV-LCP-LOAD-TIME" in crit_ids
    assert "CWV-CLS-STABILITY" in crit_ids
    assert "CWV-INP-RESPONSIVENESS" in crit_ids

    lcp_finding = next(f for f in findings if f.criterion_id == "CWV-LCP-LOAD-TIME")
    assert lcp_finding.severity == FindingSeverity.CRITICAL
    assert "Poor" in lcp_finding.title

    cls_finding = next(f for f in findings if f.criterion_id == "CWV-CLS-STABILITY")
    assert cls_finding.severity == FindingSeverity.MAJOR
    assert "0.25" in cls_finding.title


@pytest.mark.asyncio
async def test_cwv_needs_improvement_and_3s_threshold():
    """Verify LCP between 2.5-4s triggers Needs Improvement."""
    mock_adapter = AsyncMock()
    mock_adapter.evaluate_script.side_effect = [
        "[]", "[]", "[]", '{"skips": []}',
        json.dumps({
            "pageLoadTimeSec": 3.2,
            "ttfbSec": 0.3,
            "fcpSec": 1.0,
            "lcpSec": 2.8,  # 2.5s - 4.0s (Needs Improvement)
            "clsValue": 0.02,  # Good (<0.1)
            "maxInteractionLatencyMs": 50,  # Good (<200ms)
            "htmlLang": "en",
        }),
    ]
    mock_adapter.get_console_messages.return_value = []

    findings, _ = await run_deterministic_audits(mock_adapter, run_axe=False)

    lcp_finding = next((f for f in findings if f.criterion_id == "CWV-LCP-LOAD-TIME"), None)
    assert lcp_finding is not None
    assert lcp_finding.severity == FindingSeverity.MAJOR
    assert "Needs Improvement" in lcp_finding.title


@pytest.mark.asyncio
async def test_journey_complexity_evaluation():
    """Verify journey length triggers minor friction at 5 steps and major fatigue at 8 steps."""
    mock_context = AsyncMock()
    mock_context.llm_client = None

    # Step 5 evaluation (Minor warning)
    state_step5 = {
        "current_execution": ExecutionRecord(
            execution_id="exec-1",
            mcp_tool="browser_click",
            action=ProposedAction(
                action_type=ActionType.CLICK,
                target_ref="e1",
                rationale="Click button",
                risk_class=RiskClass.LOW,
                source_observation_id="obs1",
            ),
            success=True,
            duration_ms=250.0,
        ),
        "current_journey_index": 0,
        "journeys": [Journey(journey_id="j1", goal="Checkout purchase")],
        "current_step_number": 5,
        "all_findings": [],
    }

    res5 = await evaluate_node(state_step5, mock_context)
    findings5 = res5.get("all_findings", [])
    j_finding5 = next((f for f in findings5 if f.criterion_id == "COGNITIVE-JOURNEY-COMPLEXITY"), None)
    assert j_finding5 is not None
    assert j_finding5.severity == FindingSeverity.MINOR
    assert "5 Steps" in j_finding5.title

    # Step 8 evaluation (Major cognitive fatigue & drop-off warning)
    state_step8 = {
        "current_execution": state_step5["current_execution"],
        "current_journey_index": 0,
        "journeys": [Journey(journey_id="j1", goal="Checkout purchase")],
        "current_step_number": 8,
        "all_findings": [],
    }

    res8 = await evaluate_node(state_step8, mock_context)
    findings8 = res8.get("all_findings", [])
    j_finding8 = next((f for f in findings8 if f.criterion_id == "COGNITIVE-JOURNEY-COMPLEXITY"), None)
    assert j_finding8 is not None
    assert j_finding8.severity == FindingSeverity.MAJOR
    assert "High Drop-off Risk" in j_finding8.title


def test_synthetic_persona_generation():
    """Verify synthetic persona generates valid test fields."""
    p = generate_synthetic_persona(123)
    assert len(p.first_name) > 0
    assert len(p.last_name) > 0
    assert "@example.test" in p.email
    assert p.card_number == "4242424242424242"

    assert match_synthetic_value("Email Address", p) == p.email
    assert match_synthetic_value("Phone Number", p) == p.phone
    assert match_synthetic_value("Credit Card", p) == p.card_number
    assert match_synthetic_value("Zip Code", p) == p.postal_code


def test_rubric_shortened_categories():
    """Verify updated rubric has clean shortened category labels."""
    rubric = load_rubric("config/rubrics/ux-rubric-v1.yaml")
    labels = [c.label for c in rubric.categories]
    assert "Task Flow" in labels
    assert "Accessibility" in labels
    assert "Speed & Web Vitals" in labels
    assert "Status & Feedback" in labels


def test_comparator_and_patcher(tmp_path):
    """Verify comparator calculates score deltas and patcher produces code snippets."""
    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"
    run1_dir.mkdir()
    run2_dir.mkdir()

    r1_data = {
        "run_id": "run-001",
        "target_url": "https://example.com",
        "score": {"overall_score": 75.0, "category_scores": [{"category_id": "accessibility_operability", "category_name": "Accessibility", "raw_score": 70.0}]},
        "findings": [
            {
                "finding_id": "f1",
                "root_cause_key": "target-size:#submit-btn",
                "criterion_id": "WCAG-2.5.8-TARGET-SIZE",
                "title": "Undersized button",
                "target_selector": "#submit-btn",
                "severity": "major",
                "recommendation": "Increase button padding to 24px",
            }
        ],
    }

    r2_data = {
        "run_id": "run-002",
        "target_url": "https://example.com",
        "score": {"overall_score": 90.0, "category_scores": [{"category_id": "accessibility_operability", "category_name": "Accessibility", "raw_score": 90.0}]},
        "findings": [],
    }

    (run1_dir / "result.json").write_text(json.dumps(r1_data))
    (run2_dir / "result.json").write_text(json.dumps(r2_data))

    diff = compare_runs(run1_dir, run2_dir)
    assert diff["score_delta"] == 15.0
    assert diff["counts"]["resolved"] == 1
    assert diff["counts"]["regressed_new"] == 0

    md = format_comparison_markdown(diff)
    assert "+15.0" in md
    assert "Resolved / Fixed Flaws" in md

    patches = generate_remediation_patches(run1_dir)
    assert patches["total_patches"] == 1
    assert "min-width: 24px;" in patches["patches"][0]["code_snippet"]


def test_telemetry_ingestion(tmp_path):
    """Verify real-user telemetry data parses into prioritized journeys."""
    from normanjr.telemetry.ingestion import ingest_telemetry_file

    telemetry_file = tmp_path / "posthog_funnel.json"
    data = {
        "funnels": [
            {
                "name": "Signup & Onboarding Flow",
                "dropoff_rate": 0.45,
                "steps": ["/signup", "/verify", "/onboarding"],
            }
        ],
        "events": [{"path": "/checkout/step-2", "dropoff_count": 120}],
    }
    telemetry_file.write_text(json.dumps(data))

    res = ingest_telemetry_file(telemetry_file)
    assert res["total_events_analyzed"] == 1
    assert len(res["generated_journeys"]) == 1
    assert "Signup & Onboarding Flow" in res["generated_journeys"][0]["goal"]
