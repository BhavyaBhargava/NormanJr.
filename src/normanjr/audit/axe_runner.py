"""Axe-core integration for deterministic WCAG accessibility audits."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from normanjr.domain.enums import FindingSeverity, FindingSource, FindingStatus
from normanjr.domain.models import Finding
from normanjr.mcp.playwright_adapter import PlaywrightAdapter

# Mapping of common axe rules to NormanJr rubric criteria
AXE_TO_RUBRIC_MAP = {
    "color-contrast": ("WCAG-1.4.3-CONTRAST", "accessibility_operability"),
    "target-size": ("WCAG-2.5.8-TARGET-SIZE", "accessibility_operability"),
    "button-name": ("WCAG-4.1.2-NAME-ROLE-VALUE", "accessibility_operability"),
    "link-name": ("WCAG-4.1.2-NAME-ROLE-VALUE", "accessibility_operability"),
    "aria-required-attr": ("WCAG-4.1.2-NAME-ROLE-VALUE", "accessibility_operability"),
    "aria-roles": ("WCAG-4.1.2-NAME-ROLE-VALUE", "accessibility_operability"),
    "label": ("WCAG-3.3.2-LABELS-INSTRUCTIONS", "constraints_error_recovery"),
    "image-alt": ("WCAG-4.1.2-NAME-ROLE-VALUE", "accessibility_operability"),
    "heading-order": ("WCAG-4.1.2-NAME-ROLE-VALUE", "accessibility_operability"),
}


def get_axe_script_content() -> str:
    """Read locked axe.min.js from node_modules."""
    axe_path = Path("node_modules/axe-core/axe.min.js")
    if not axe_path.exists():
        raise FileNotFoundError(f"axe.min.js not found at {axe_path}. Run npm install.")
    return axe_path.read_text(encoding="utf-8")


async def run_axe_scan(
    adapter: PlaywrightAdapter,
    journey_id: str | None = None,
    state_id: str | None = None,
) -> tuple[list[Finding], dict[str, Any]]:
    """Inject axe-core if needed, run WCAG 2.2 rules, and return findings and summary."""
    # Check if axe is defined in page
    is_defined = await adapter.evaluate_script("() => typeof window.axe !== 'undefined'")
    if isinstance(is_defined, bool):
        axe_present = is_defined
    else:
        axe_present = "true" in str(is_defined).lower()

    if not axe_present:
        # Inject axe-core script into the page
        axe_code = get_axe_script_content()
        await adapter.evaluate_script(f"() => {{ {axe_code} }}")

    # Run axe scan targeting WCAG A and AA tags
    run_script = """async () => {
      const results = await window.axe.run(document, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']
        }
      });
      return JSON.stringify({
        violations: results.violations.map(v => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          help: v.help,
          helpUrl: v.helpUrl,
          nodes: v.nodes.map(n => ({
            target: n.target.join(' '),
            html: (n.html || '').slice(0, 150),
            failureSummary: n.failureSummary || '',
          }))
        })),
        passesCount: results.passes.length,
        incompleteCount: results.incomplete.length,
      });
    }"""

    raw_output = await adapter.evaluate_script(run_script)
    if isinstance(raw_output, dict):
        data = raw_output
    else:
        try:
            data = json.loads(raw_output)
        except Exception:
            return [], {"error": "Failed to parse axe-core output"}

    findings: list[Finding] = []
    violations = data.get("violations", [])

    for v in violations:
        rule_id = v.get("id", "axe-violation")
        impact = (v.get("impact") or "moderate").lower()

        # Map impact to FindingSeverity
        if impact == "critical":
            sev = FindingSeverity.CRITICAL
            penalty = 15
        elif impact == "serious":
            sev = FindingSeverity.MAJOR
            penalty = 8
        elif impact == "moderate":
            sev = FindingSeverity.MINOR
            penalty = 3
        else:
            sev = FindingSeverity.OBSERVATION
            penalty = 0

        criterion_id, category_id = AXE_TO_RUBRIC_MAP.get(
            rule_id, ("WCAG-4.1.2-NAME-ROLE-VALUE", "accessibility_operability")
        )

        nodes = v.get("nodes", [])
        for node in nodes:
            target = node.get("target", "document")
            root_cause = f"axe:{rule_id}:{target}"
            html_snippet = node.get("html", "")
            summary = node.get("failureSummary", v.get("description", ""))

            finding = Finding(
                finding_id=f"axe-{rule_id}-{len(findings)+1:03d}",
                root_cause_key=root_cause,
                source=FindingSource.AXE,
                criterion_id=criterion_id,
                category_id=category_id,
                severity=sev,
                status=FindingStatus.CONFIRMED,
                confidence="high",
                score_penalty=penalty,
                scoring_eligible=True,
                journey_id=journey_id,
                state_id=state_id,
                title=f"WCAG Violation: {v.get('help', rule_id)}",
                description=v.get("description", ""),
                user_impact=f"Automated accessibility barrier affecting assistive technology users ({impact} impact).",
                expected_behavior="Element must comply with WCAG 2.2 accessibility criteria.",
                actual_behavior=summary,
                target_selector=target,
                measured_data={"html": html_snippet, "axe_rule": rule_id, "help_url": v.get("helpUrl")},
                recommendation=f"Review WCAG guidance: {v.get('helpUrl', 'https://www.w3.org/WAI/WCAG22/')}",
                verification_advice="Run axe-core scan on updated DOM to verify violation is resolved.",
            )
            findings.append(finding)

    summary_data = {
        "violations_count": len(findings),
        "passes_count": data.get("passesCount", 0),
        "incomplete_count": data.get("incompleteCount", 0),
    }

    return findings, summary_data
