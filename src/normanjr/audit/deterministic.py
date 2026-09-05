"""Deterministic audit collectors combining DOM metrics and axe-core findings."""

from __future__ import annotations

import json
from typing import Any

from normanjr.audit.axe_runner import run_axe_scan
from normanjr.audit.metrics import (
    DOM_FORM_LABEL_SCRIPT,
    DOM_HEADING_HIERARCHY_SCRIPT,
    DOM_IMAGE_ALT_SCRIPT,
    DOM_TARGET_SIZE_SCRIPT,
)
from normanjr.domain.enums import FindingSeverity, FindingSource, FindingStatus
from normanjr.domain.models import Finding
from normanjr.mcp.playwright_adapter import PlaywrightAdapter


async def run_deterministic_audits(
    adapter: PlaywrightAdapter,
    journey_id: str | None = None,
    state_id: str | None = None,
    run_axe: bool = True,
) -> tuple[list[Finding], dict[str, Any]]:
    """Execute all deterministic in-browser metrics and accessibility checks."""
    all_findings: list[Finding] = []
    collected_metrics: dict[str, Any] = {}

    # 1. Target size check (WCAG 2.5.8)
    try:
        raw_sizes = await adapter.evaluate_script(DOM_TARGET_SIZE_SCRIPT)
        small_targets = json.loads(raw_sizes) if isinstance(raw_sizes, str) else (raw_sizes or [])
        collected_metrics["undersized_targets_count"] = len(small_targets)

        for item in small_targets:
            sel = item.get("selector", "element")
            w = item.get("width", 0)
            h = item.get("height", 0)
            name = item.get("name") or sel

            f = Finding(
                finding_id=f"det-target-size-{len(all_findings)+1:03d}",
                root_cause_key=f"target-size:{sel}",
                source=FindingSource.DETERMINISTIC,
                criterion_id="WCAG-2.5.8-TARGET-SIZE",
                category_id="accessibility_operability",
                severity=FindingSeverity.MAJOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=8,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Target Size Below 24x24px: '{name}' ({w}x{h}px)",
                description=f"Interactive element '{name}' measures {w}px wide by {h}px high, failing the minimum 24x24px target size requirement.",
                user_impact="Users with motor impairments, touch devices, or tremors will struggle to reliably activate this control.",
                expected_behavior="Interactive targets should be at least 24x24 CSS pixels or have sufficient spacing (WCAG 2.2 SC 2.5.8).",
                actual_behavior=f"Measured dimensions: width={w}px, height={h}px.",
                target_selector=sel,
                target_name=name,
                measured_data={"width": w, "height": h, "tag": item.get("tag")},
                recommendation=f"Increase padding or dimensions so the clickable area is at least 24x24px.",
                verification_advice="Inspect element bounding box in developer tools to verify computed size >= 24x24px.",
            )
            all_findings.append(f)
    except Exception as e:
        collected_metrics["target_size_error"] = str(e)

    # 2. Form label check (WCAG 3.3.2)
    try:
        raw_labels = await adapter.evaluate_script(DOM_FORM_LABEL_SCRIPT)
        unlabelled = json.loads(raw_labels) if isinstance(raw_labels, str) else (raw_labels or [])
        collected_metrics["unlabelled_inputs_count"] = len(unlabelled)

        for item in unlabelled:
            input_id = item.get("id") or item.get("name") or "input"
            sel = f"#{input_id}" if item.get("id") else f"input[name='{item.get('name')}']"

            f = Finding(
                finding_id=f"det-form-label-{len(all_findings)+1:03d}",
                root_cause_key=f"form-label:{sel}",
                source=FindingSource.DETERMINISTIC,
                criterion_id="WCAG-3.3.2-LABELS-INSTRUCTIONS",
                category_id="constraints_error_recovery",
                severity=FindingSeverity.MAJOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=8,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Form Input Missing Programmatic Label: '{sel}'",
                description=f"Form input '{sel}' has no associated <label for='...'>, aria-label, or aria-labelledby.",
                user_impact="Screen reader users cannot identify the purpose of this input field.",
                expected_behavior="Every form control must have a programmatically associated label (WCAG 2.2 SC 3.3.2).",
                actual_behavior="No associated label or ARIA labeling attributes found.",
                target_selector=sel,
                measured_data=item,
                recommendation="Associate a <label for='...'> with this input ID or provide an aria-label.",
                verification_advice="Verify that accessibility tree displays an accessible name for this control.",
            )
            all_findings.append(f)
    except Exception as e:
        collected_metrics["form_label_error"] = str(e)

    # 3. Image alt check (WCAG 4.1.2)
    try:
        raw_alts = await adapter.evaluate_script(DOM_IMAGE_ALT_SCRIPT)
        missing_alts = json.loads(raw_alts) if isinstance(raw_alts, str) else (raw_alts or [])
        collected_metrics["missing_alt_images_count"] = len(missing_alts)

        for item in missing_alts:
            src = item.get("src", "")
            f = Finding(
                finding_id=f"det-img-alt-{len(all_findings)+1:03d}",
                root_cause_key=f"img-alt:{src[:40]}",
                source=FindingSource.DETERMINISTIC,
                criterion_id="WCAG-4.1.2-NAME-ROLE-VALUE",
                category_id="accessibility_operability",
                severity=FindingSeverity.MAJOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=8,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Image Missing Alt Attribute: '{src[:40]}...'",
                description="An image is rendered without an 'alt' attribute, leaving screen readers unable to convey its purpose.",
                user_impact="Assistive technologies may announce the raw image URL instead of meaningful content.",
                expected_behavior="All <img> tags must include an alt attribute describing the image or alt='' if purely decorative.",
                actual_behavior="Image tag completely lacks the alt attribute.",
                measured_data={"src": src},
                recommendation="Add alt='...' with a concise textual description of the image.",
                verification_advice="Check the HTML source to ensure alt attribute is present.",
            )
            all_findings.append(f)
    except Exception as e:
        collected_metrics["img_alt_error"] = str(e)

    # 4. Heading hierarchy check
    try:
        raw_headings = await adapter.evaluate_script(DOM_HEADING_HIERARCHY_SCRIPT)
        heading_data = json.loads(raw_headings) if isinstance(raw_headings, str) else (raw_headings or {})
        collected_metrics["heading_skips_count"] = len(heading_data.get("skips", []))

        for skip in heading_data.get("skips", []):
            f = Finding(
                finding_id=f"det-heading-skip-{len(all_findings)+1:03d}",
                root_cause_key=f"heading-skip:h{skip['fromLevel']}-to-h{skip['toLevel']}",
                source=FindingSource.DETERMINISTIC,
                criterion_id="WCAG-4.1.2-NAME-ROLE-VALUE",
                category_id="accessibility_operability",
                severity=FindingSeverity.MINOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=3,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Heading Level Skipped: h{skip['fromLevel']} jumped to h{skip['toLevel']}",
                description=f"Headings skip levels from <h1>-<h6> hierarchy: jumped from h{skip['fromLevel']} to h{skip['toLevel']} for '{skip.get('text', '')}'.",
                user_impact="Users navigating by headings may become confused about document structure and hierarchy.",
                expected_behavior="Heading levels should increment sequentially without skipping levels.",
                actual_behavior=f"Skipped from h{skip['fromLevel']} directly to h{skip['toLevel']}.",
                measured_data=skip,
                recommendation="Adjust heading level to be sequential.",
                verification_advice="Verify heading levels follow sequential numerical hierarchy.",
            )
            all_findings.append(f)
    except Exception as e:
        collected_metrics["heading_hierarchy_error"] = str(e)

    # 5. Console errors check
    try:
        console_msgs = await adapter.get_console_messages()
        collected_metrics["console_errors_count"] = len(console_msgs)
        if console_msgs:
            f = Finding(
                finding_id=f"det-console-err-{len(all_findings)+1:03d}",
                root_cause_key=f"console-error:{console_msgs[0][:50]}",
                source=FindingSource.DETERMINISTIC,
                criterion_id="PERF-STABILITY-LAYOUT-SHIFT",
                category_id="performance_stability",
                severity=FindingSeverity.MINOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=3,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Uncaught JavaScript Console Exception ({len(console_msgs)} errors)",
                description="One or more unhandled JavaScript exceptions occurred during page execution.",
                user_impact="May cause degraded functionality, broken scripts, or unexpected UI freezes.",
                expected_behavior="Web page should execute without uncaught browser console exceptions.",
                actual_behavior="\n".join(console_msgs[:5]),
                measured_data={"console_errors": console_msgs[:10]},
                recommendation="Fix underlying script exceptions reported in browser console.",
                verification_advice="Open browser developer tools console and verify no unhandled errors appear.",
            )
            all_findings.append(f)
    except Exception as e:
        collected_metrics["console_error_check_error"] = str(e)

    # 6. Axe-core scan
    if run_axe:
        try:
            axe_findings, axe_summary = await run_axe_scan(
                adapter, journey_id=journey_id, state_id=state_id
            )
            collected_metrics["axe_summary"] = axe_summary
            all_findings.extend(axe_findings)
        except Exception as e:
            collected_metrics["axe_error"] = str(e)

    return all_findings, collected_metrics
