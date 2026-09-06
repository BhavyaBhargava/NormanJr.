"""Automatic source code remediation patch generator for usability and accessibility findings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def generate_remediation_patches(run_dir: Path) -> dict[str, Any]:
    """Generate CSS, HTML, and ARIA code remediation patches for identified findings."""
    result_file = run_dir / "result.json"
    if not result_file.exists():
        raise FileNotFoundError(f"result.json not found in: {run_dir}")

    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    findings = data.get("findings", [])
    patches = []

    for f in findings:
        cid = f.get("criterion_id", "")
        sel = f.get("target_selector") or ""
        mdata = f.get("measured_data", {})
        title = f.get("title", "")

        patch_entry = {
            "finding_id": f.get("finding_id"),
            "criterion_id": cid,
            "title": title,
            "target_selector": sel,
            "patch_type": "none",
            "code_snippet": "",
            "explanation": f.get("recommendation", ""),
        }

        # 1. Target Size (WCAG 2.5.8) -> CSS Patch
        if "TARGET-SIZE" in cid and sel:
            css_patch = f"""/* Fix for {title} */
{sel} {{
  min-width: 24px;
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
}}"""
            patch_entry["patch_type"] = "css"
            patch_entry["code_snippet"] = css_patch
            patches.append(patch_entry)

        # 2. Form Labels (WCAG 3.3.2) -> HTML Patch
        elif "LABELS-INSTRUCTIONS" in cid and sel:
            input_id = mdata.get("id") or "field-id"
            html_patch = f"""<!-- Fix for {title} -->
<label for="{input_id}" class="form-label">
  Field Label Description
</label>
<input id="{input_id}" name="{mdata.get('name', input_id)}" ... />"""
            patch_entry["patch_type"] = "html"
            patch_entry["code_snippet"] = html_patch
            patches.append(patch_entry)

        # 3. Image Alt (WCAG 4.1.2) -> HTML Patch
        elif "img-alt" in f.get("root_cause_key", ""):
            src = mdata.get("src", "image.png")
            html_patch = f"""<!-- Fix for {title} -->
<img src="{src}" alt="Concise description of the image" />"""
            patch_entry["patch_type"] = "html"
            patch_entry["code_snippet"] = html_patch
            patches.append(patch_entry)

        # 4. CLS Layout Shift -> CSS Patch
        elif "CWV-CLS" in cid or "LAYOUT-SHIFT" in cid:
            css_patch = f"""/* Fix for {title}: Reserve aspect ratio / dimensions */
img, video, iframe, .media-embed {{
  aspect-ratio: 16 / 9;
  width: 100%;
  height: auto;
}}"""
            patch_entry["patch_type"] = "css"
            patch_entry["code_snippet"] = css_patch
            patches.append(patch_entry)

        # 5. Core Web Vitals LCP Preload -> HTML Head Patch
        elif "CWV-LCP" in cid:
            html_patch = f"""<!-- Fix for {title}: Preload Hero Image / Font -->
<link rel="preload" as="image" href="/path/to/hero-image.webp" fetchpriority="high" />
<link rel="preconnect" href="https://fonts.googleapis.com" />"""
            patch_entry["patch_type"] = "html_head"
            patch_entry["code_snippet"] = html_patch
            patches.append(patch_entry)

        # 6. HTML Missing Lang -> HTML Patch
        elif "missing-lang" in f.get("root_cause_key", ""):
            html_patch = f"""<!-- Fix for {title} -->
<html lang="en">"""
            patch_entry["patch_type"] = "html"
            patch_entry["code_snippet"] = html_patch
            patches.append(patch_entry)

    return {
        "run_id": data.get("run_id"),
        "target_url": data.get("target_url"),
        "total_patches": len(patches),
        "patches": patches,
    }


def format_patches_text(result: dict[str, Any]) -> str:
    """Format patches as a clean printable code remediation sheet."""
    lines = [
        f"# NormanJr. Automated Code Remediation Sheet",
        f"# Run: {result['run_id']} ({result['target_url']})",
        f"# Total Fix Patches: {result['total_patches']}",
        f"{'=' * 60}",
        "",
    ]
    for p in result["patches"]:
        lines.extend([
            f"/* Finding: {p['title']} [{p['criterion_id']}] */",
            f"/* Recommendation: {p['explanation']} */",
            p["code_snippet"],
            "",
            "-" * 60,
            "",
        ])
    return "\n".join(lines)
