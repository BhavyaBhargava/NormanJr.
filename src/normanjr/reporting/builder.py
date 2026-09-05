"""High-level builder orchestrating HTML and PDF report generation."""

from __future__ import annotations

import json
from pathlib import Path

from normanjr.domain.models import AuditRun
from normanjr.reporting.html import render_html_report
from normanjr.reporting.pdf import render_pdf_report


async def generate_reports(
    run_dir: Path | str,
    output_format: str = "all",
) -> dict[str, Path | None]:
    """Generate HTML and PDF reports from a run directory containing result.json."""
    dir_path = Path(run_dir).resolve()
    result_file = dir_path / "result.json"

    if not result_file.exists():
        raise FileNotFoundError(f"result.json not found in {dir_path}")

    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    audit_run = AuditRun(**data)

    results: dict[str, Path | None] = {"html": None, "pdf": None}

    # 1. HTML generation
    if output_format in ("all", "html"):
        html_path = render_html_report(audit_run, dir_path)
        results["html"] = html_path

    # 2. PDF generation
    if output_format in ("all", "pdf"):
        # Ensure HTML exists first
        if not (dir_path / "report.html").exists():
            render_html_report(audit_run, dir_path)
        pdf_path = await render_pdf_report(dir_path)
        results["pdf"] = pdf_path

    return results
