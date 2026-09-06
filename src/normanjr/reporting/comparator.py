"""Historical run comparator for visual, scoring, and finding regression analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def compare_runs(run_dir_1: Path, run_dir_2: Path) -> dict[str, Any]:
    """Compare two audit runs to detect score deltas, regressions, fixes, and persistent flaws."""
    file1 = run_dir_1 / "result.json"
    file2 = run_dir_2 / "result.json"

    if not file1.exists():
        raise FileNotFoundError(f"Result file not found for run 1: {file1}")
    if not file2.exists():
        raise FileNotFoundError(f"Result file not found for run 2: {file2}")

    with open(file1, "r", encoding="utf-8") as f:
        r1 = json.load(f)
    with open(file2, "r", encoding="utf-8") as f:
        r2 = json.load(f)

    score1 = r1.get("score", {}).get("overall_score", 0.0)
    score2 = r2.get("score", {}).get("overall_score", 0.0)
    score_delta = round(score2 - score1, 2)

    cat1 = {c["category_id"]: c for c in r1.get("score", {}).get("category_scores", [])}
    cat2 = {c["category_id"]: c for c in r2.get("score", {}).get("category_scores", [])}
    all_cats = set(cat1.keys()).union(set(cat2.keys()))

    category_deltas = []
    for cid in sorted(all_cats):
        s1 = cat1.get(cid, {}).get("raw_score", 0.0)
        s2 = cat2.get(cid, {}).get("raw_score", 0.0)
        name = cat2.get(cid, {}).get("category_name") or cat1.get(cid, {}).get("category_name") or cid
        category_deltas.append({
            "category_id": cid,
            "category_name": name,
            "baseline_score": s1,
            "current_score": s2,
            "delta": round(s2 - s1, 2),
        })

    findings1 = {f.get("root_cause_key", f.get("finding_id")): f for f in r1.get("findings", [])}
    findings2 = {f.get("root_cause_key", f.get("finding_id")): f for f in r2.get("findings", [])}

    keys1 = set(findings1.keys())
    keys2 = set(findings2.keys())

    resolved_keys = keys1 - keys2
    regressed_keys = keys2 - keys1
    persistent_keys = keys1.intersection(keys2)

    resolved_findings = [findings1[k] for k in resolved_keys]
    regressed_findings = [findings2[k] for k in regressed_keys]
    persistent_findings = [findings2[k] for k in persistent_keys]

    return {
        "baseline_run_id": r1.get("run_id"),
        "baseline_url": r1.get("target_url"),
        "current_run_id": r2.get("run_id"),
        "current_url": r2.get("target_url"),
        "baseline_score": score1,
        "current_score": score2,
        "score_delta": score_delta,
        "improved": score_delta > 0,
        "category_deltas": category_deltas,
        "counts": {
            "resolved": len(resolved_findings),
            "regressed_new": len(regressed_findings),
            "persistent": len(persistent_findings),
        },
        "resolved_findings": resolved_findings,
        "regressed_findings": regressed_findings,
        "persistent_findings": persistent_findings,
    }


def format_comparison_markdown(diff: dict[str, Any]) -> str:
    """Format run comparison as a clear Markdown summary."""
    lines = [
        f"# NormanJr. UX Regression Report",
        f"",
        f"- **Baseline Run:** `{diff['baseline_run_id']}` ({diff['baseline_url']})",
        f"- **Current Run:** `{diff['current_run_id']}` ({diff['current_url']})",
        f"- **Score Trend:** {diff['baseline_score']} ➔ {diff['current_score']} ({'+' if diff['score_delta'] >= 0 else ''}{diff['score_delta']})",
        f"",
        f"## Summary Overview",
        f"| Metric | Count |",
        f"|---|---|",
        f"| Resolved / Fixed Flaws | **{diff['counts']['resolved']}** |",
        f"| New Flaws (Regressions) | **{diff['counts']['regressed_new']}** |",
        f"| Persistent Flaws | **{diff['counts']['persistent']}** |",
        f"",
        f"## Category Score Changes",
        f"| Category | Baseline | Current | Delta |",
        f"|---|---|---|---|",
    ]
    for c in diff["category_deltas"]:
        d_str = f"+{c['delta']}" if c['delta'] > 0 else f"{c['delta']}"
        lines.append(f"| {c['category_name']} | {c['baseline_score']} | {c['current_score']} | {d_str} |")

    if diff["regressed_findings"]:
        lines.extend([
            f"",
            f"## ⚠️ Regressed / New Findings",
        ])
        for f in diff["regressed_findings"]:
            lines.append(f"- **[{f.get('severity', '').upper()}]** {f.get('title')}: {f.get('description')}")

    if diff["resolved_findings"]:
        lines.extend([
            f"",
            f"## ✅ Resolved / Fixed Findings",
        ])
        for f in diff["resolved_findings"]:
            lines.append(f"- **[{f.get('severity', '').upper()}]** {f.get('title')}")

    return "\n".join(lines)
