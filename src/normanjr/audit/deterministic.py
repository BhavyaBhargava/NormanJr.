"""Deterministic audit collectors combining DOM metrics, Core Web Vitals, and axe-core findings."""

from __future__ import annotations

import json
from typing import Any

from normanjr.audit.axe_runner import run_axe_scan
from normanjr.audit.metrics import (
    DOM_CORE_WEB_VITALS_SCRIPT,
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
    """Execute all deterministic in-browser metrics, Core Web Vitals, and accessibility checks."""
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
                recommendation="Increase padding or dimensions so the clickable area is at least 24x24px.",
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

    # 5. Core Web Vitals & SEO Page Speed Checks
    try:
        raw_cwv = await adapter.evaluate_script(DOM_CORE_WEB_VITALS_SCRIPT)
        cwv_data = json.loads(raw_cwv) if isinstance(raw_cwv, str) else (raw_cwv or {})
        collected_metrics["core_web_vitals"] = cwv_data

        lcp_sec = float(cwv_data.get("lcpSec", 0.0))
        page_load_sec = float(cwv_data.get("pageLoadTimeSec", 0.0))
        cls_val = float(cwv_data.get("clsValue", 0.0))
        inp_ms = float(cwv_data.get("maxInteractionLatencyMs", 0.0))
        html_lang = cwv_data.get("htmlLang", "")

        # 5.1 LCP Check (Largest Contentful Paint)
        # Golden rule: Under 2.5s (Good), 2.5s-4.0s (Needs Improvement), >4.0s (Poor)
        if lcp_sec > 4.0:
            f = Finding(
                finding_id=f"det-cwv-lcp-poor-{len(all_findings)+1:03d}",
                root_cause_key=f"cwv-lcp:poor",
                source=FindingSource.DETERMINISTIC,
                criterion_id="CWV-LCP-LOAD-TIME",
                category_id="performance_stability",
                severity=FindingSeverity.CRITICAL,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=15,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Core Web Vitals: LCP Exceeds 4.0s (Poor — {lcp_sec:.2f}s)",
                description=f"Largest Contentful Paint (LCP) measured {lcp_sec:.2f} seconds. Google Core Web Vitals rates LCP > 4.0s as 'Poor'.",
                user_impact="Critical user drop-off risk and severe Google SEO ranking penalty. Fast load times serve as an official Google ranking signal.",
                expected_behavior="Main content (LCP) must load within 2.5 seconds to pass Core Web Vitals assessment.",
                actual_behavior=f"Measured LCP: {lcp_sec:.2f}s (Threshold: < 2.5s).",
                measured_data=cwv_data,
                recommendation="Optimize the critical rendering path: compress and preload hero images, enable server-side caching/CDN, and eliminate render-blocking scripts.",
                verification_advice="Inspect Network and Performance tabs in DevTools to measure LCP timeline.",
            )
            all_findings.append(f)
        elif lcp_sec > 2.5:
            f = Finding(
                finding_id=f"det-cwv-lcp-ni-{len(all_findings)+1:03d}",
                root_cause_key=f"cwv-lcp:needs-improvement",
                source=FindingSource.DETERMINISTIC,
                criterion_id="CWV-LCP-LOAD-TIME",
                category_id="performance_stability",
                severity=FindingSeverity.MAJOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=8,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Core Web Vitals: LCP Between 2.5s and 4.0s (Needs Improvement — {lcp_sec:.2f}s)",
                description=f"Largest Contentful Paint (LCP) measured {lcp_sec:.2f} seconds, failing Google's 2.5-second golden rule for main content load time.",
                user_impact="Higher bounce rate and lower SEO ranking competitiveness on search engine result pages.",
                expected_behavior="Main content should load in under 2.5 seconds.",
                actual_behavior=f"Measured LCP: {lcp_sec:.2f}s.",
                measured_data=cwv_data,
                recommendation="Preload hero images, optimize web fonts with font-display: swap, and reduce Time to First Byte (TTFB).",
                verification_advice="Verify LCP duration in Google Lighthouse / PageSpeed Insights.",
            )
            all_findings.append(f)

        # 5.2 3-Second Abandonment Threshold Check
        if page_load_sec > 3.0 and lcp_sec <= 2.5:
            f = Finding(
                finding_id=f"det-seo-load-threshold-{len(all_findings)+1:03d}",
                root_cause_key=f"seo-load:over-3s",
                source=FindingSource.DETERMINISTIC,
                criterion_id="SEO-PAGE-LOAD-THRESHOLD",
                category_id="performance_stability",
                severity=FindingSeverity.MAJOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=8,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Page Load Exceeds 3-Second Abandonment Threshold ({page_load_sec:.2f}s)",
                description=f"Total page load time reached {page_load_sec:.2f} seconds, surpassing the critical 3-second mobile abandonment threshold.",
                user_impact="Industry studies show bounce probability escalates drastically past 3 seconds, with over half of mobile users abandoning.",
                expected_behavior="Page should finish primary asset loading in under 3 seconds.",
                actual_behavior=f"Total load time: {page_load_sec:.2f}s.",
                measured_data=cwv_data,
                recommendation="Defer non-critical third-party analytics/scripts and lazy-load below-the-fold assets.",
                verification_advice="Audit bundle sizes and network waterfall.",
            )
            all_findings.append(f)

        # 5.3 CLS Check (Cumulative Layout Shift)
        # Golden rule: Below 0.1 (Good)
        if cls_val > 0.1:
            f = Finding(
                finding_id=f"det-cwv-cls-{len(all_findings)+1:03d}",
                root_cause_key=f"cwv-cls:unstable",
                source=FindingSource.DETERMINISTIC,
                criterion_id="CWV-CLS-STABILITY",
                category_id="performance_stability",
                severity=FindingSeverity.MAJOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=8,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Core Web Vitals: Visual Instability CLS Exceeds 0.1 ({cls_val:.3f})",
                description=f"Cumulative Layout Shift (CLS) measured {cls_val:.3f}, exceeding the 0.1 visual stability standard.",
                user_impact="Unexpected visual shifting causes misclicks, jarring user distraction, and Google ranking penalties.",
                expected_behavior="Visual layout should remain stable during page load (CLS < 0.1).",
                actual_behavior=f"Measured CLS: {cls_val:.3f}.",
                measured_data=cwv_data,
                recommendation="Explicitly define width and height attributes on images/embeds, and avoid injecting DOM elements above existing content.",
                verification_advice="Check Layout Shifts in DevTools Performance panel.",
            )
            all_findings.append(f)

        # 5.4 INP / Interaction Latency Check
        # Golden rule: Under 200ms (Good)
        if inp_ms > 200:
            f = Finding(
                finding_id=f"det-cwv-inp-{len(all_findings)+1:03d}",
                root_cause_key=f"cwv-inp:sluggish",
                source=FindingSource.DETERMINISTIC,
                criterion_id="CWV-INP-RESPONSIVENESS",
                category_id="performance_stability",
                severity=FindingSeverity.MAJOR,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=8,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"Core Web Vitals: Interaction to Next Paint Exceeds 200ms ({inp_ms:.0f}ms)",
                description=f"Interaction responsiveness measured {inp_ms:.0f}ms, exceeding the 200ms threshold for good responsiveness.",
                user_impact="Controls feel unresponsive or sluggish when clicked or tapped.",
                expected_behavior="Interaction latency should be under 200ms (INP).",
                actual_behavior=f"Interaction latency: {inp_ms:.0f}ms.",
                measured_data=cwv_data,
                recommendation="Break up long JavaScript tasks on the main thread and defer heavy compute.",
                verification_advice="Profile event handler execution times in DevTools.",
            )
            all_findings.append(f)

        # 5.5 Multilingual HTML lang Check
        if not html_lang.strip():
            f = Finding(
                finding_id=f"det-i18n-lang-{len(all_findings)+1:03d}",
                root_cause_key=f"i18n:missing-lang",
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
                title="Root <html> Element Missing 'lang' Attribute",
                description="The root <html> element does not specify a 'lang' attribute (e.g., lang='en').",
                user_impact="Screen readers and translation engines cannot determine the page's primary language.",
                expected_behavior="The root <html> element must include a valid lang attribute.",
                actual_behavior="<html lang> is empty or undefined.",
                measured_data={"html_lang": html_lang},
                recommendation="Add lang='en' (or target language tag) to <html>.",
                verification_advice="Verify <html lang='...'> attribute in source code.",
            )
            all_findings.append(f)

        # 5.6 Multilingual text expansion and untranslated placeholder checks
        try:
            from normanjr.audit.metrics import DOM_MULTILINGUAL_SCRIPT
            raw_multi = await adapter.evaluate_script(DOM_MULTILINGUAL_SCRIPT)
            multi_issues = json.loads(raw_multi) if isinstance(raw_multi, str) else (raw_multi or [])
            collected_metrics["multilingual_issues_count"] = len(multi_issues)

            for issue in multi_issues:
                itype = issue.get("type")
                isel = issue.get("selector", "element")
                itxt = issue.get("text", "")
                if itype == "untranslated_placeholder":
                    f = Finding(
                        finding_id=f"det-i18n-placeholder-{len(all_findings)+1:03d}",
                        root_cause_key=f"i18n:untranslated:{isel}",
                        source=FindingSource.DETERMINISTIC,
                        criterion_id="NIELSEN-CONSISTENCY-STANDARDS",
                        category_id="mapping_conceptual_model",
                        severity=FindingSeverity.MAJOR,
                        status=FindingStatus.CONFIRMED,
                        confidence="high",
                        score_penalty=8,
                        scoring_eligible=True,
                        journey_id=journey_id,
                        state_id=state_id,
                        title=f"Untranslated Placeholder in UI: '{itxt[:30]}'",
                        description=f"Element '{isel}' displays raw translation placeholder or missing key: '{itxt}'.",
                        user_impact="Users see raw programming tokens and broken localization strings.",
                        expected_behavior="All interface strings should be localized.",
                        actual_behavior=f"Raw token rendered: {itxt}",
                        measured_data=issue,
                        recommendation="Supply localized translation string in message catalog.",
                        verification_advice="Verify translated UI in target locale.",
                    )
                    all_findings.append(f)
                elif itype == "text_overflow_clipped":
                    f = Finding(
                        finding_id=f"det-i18n-overflow-{len(all_findings)+1:03d}",
                        root_cause_key=f"i18n:overflow:{isel}",
                        source=FindingSource.DETERMINISTIC,
                        criterion_id="FITTS-LAW-TARGET-DISTANCE",
                        category_id="responsive_motor",
                        severity=FindingSeverity.MINOR,
                        status=FindingStatus.CONFIRMED,
                        confidence="high",
                        score_penalty=3,
                        scoring_eligible=True,
                        journey_id=journey_id,
                        state_id=state_id,
                        title=f"Text Truncated or Clipped in Element '{isel}'",
                        description=f"Text '{itxt}' overflows its container ({isel}) and is clipped by CSS overflow rules.",
                        user_impact="Expanded localized text is truncated, preventing users from reading the full label or instruction.",
                        expected_behavior="Container should accommodate translated text expansion without clipping.",
                        actual_behavior="Text exceeds container bounds and is hidden/clipped.",
                        measured_data=issue,
                        recommendation="Use flexible container sizing or allow wrapping to accommodate text expansion.",
                        verification_advice="Test UI layout with pseudo-localization or German translations.",
                    )
                    all_findings.append(f)
        except Exception as e:
            collected_metrics["multilingual_check_error"] = str(e)

    except Exception as e:
        collected_metrics["cwv_check_error"] = str(e)

    # 6. Console errors check
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

    # 7. Axe-core scan
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
