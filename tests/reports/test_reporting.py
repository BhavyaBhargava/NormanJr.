"""Tests for HTML and PDF report generation."""

from pathlib import Path
import pytest

from normanjr.audit.rubric import load_rubric
from normanjr.audit.scoring import calculate_audit_score
from normanjr.domain.enums import AuditStatus, FindingSeverity, FindingSource, FindingStatus
from normanjr.domain.models import AuditRun, Finding, Journey
from normanjr.domain.serialization import to_canonical_json
from normanjr.reporting.builder import generate_reports
from normanjr.reporting.html import render_html_report


def create_sample_run() -> AuditRun:
    rubric = load_rubric()
    f1 = Finding(
        finding_id="f-001",
        root_cause_key="target-size:#submit-btn",
        source=FindingSource.DETERMINISTIC,
        criterion_id="WCAG-2.5.8-TARGET-SIZE",
        category_id="accessibility_operability",
        severity=FindingSeverity.MAJOR,
        status=FindingStatus.CONFIRMED,
        confidence="high",
        score_penalty=8,
        scoring_eligible=True,
        title="Button is too small (12x12px)",
        description="The submit button is smaller than the minimum 24x24px requirement.",
        user_impact="Users may misclick or fail to activate the button.",
        recommendation="Add at least 8px padding around the icon.",
        target_selector="#submit-btn",
    )
    f2 = Finding(
        finding_id="f-002",
        root_cause_key="security-alert:xss",
        source=FindingSource.DETERMINISTIC,
        criterion_id="WCAG-4.1.2-NAME-ROLE-VALUE",
        category_id="accessibility_operability",
        severity=FindingSeverity.MINOR,
        status=FindingStatus.CONFIRMED,
        confidence="high",
        score_penalty=3,
        scoring_eligible=True,
        title="Escaping test <script>alert(1)</script>",
        description="Text with <img src=x onerror=alert(1)> must be properly escaped.",
        recommendation="Escape user input.",
    )
    journeys = [Journey(journey_id="j1", goal="Complete purchase workflow")]
    score = calculate_audit_score([f1, f2], rubric, journeys, unique_states_count=3)

    return AuditRun(
        run_id="sample-run-123",
        target_url="https://example.com/store",
        created_at="2026-09-05T12:00:00Z",
        completed_at="2026-09-05T12:05:00Z",
        status=AuditStatus.COMPLETED,
        journeys=journeys,
        findings=[f1, f2],
        score=score,
    )


def test_html_report_escaping_and_content(tmp_path: Path):
    audit_run = create_sample_run()
    html_file = render_html_report(audit_run, tmp_path)

    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")

    # Verify key metadata
    assert "https://example.com/store" in content
    assert "sample-run-123" in content
    assert "Button is too small" in content

    # Verify HTML escaping: <script> should be escaped to &lt;script&gt;
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in content


@pytest.mark.asyncio
async def test_generate_reports_full(tmp_path: Path):
    audit_run = create_sample_run()
    result_file = tmp_path / "result.json"
    result_file.write_text(to_canonical_json(audit_run), encoding="utf-8")

    reports = await generate_reports(tmp_path, output_format="all")

    assert reports["html"] is not None
    assert reports["html"].exists()

    # If PDF generation succeeded in this headless environment, verify it exists
    if reports["pdf"] is not None:
        assert reports["pdf"].exists()
        assert reports["pdf"].stat().st_size > 0
