"""Multi-run organization dashboard generator and local server."""

from __future__ import annotations

import http.server
import json
import socketserver
from pathlib import Path
from typing import Any


def scan_all_runs(runs_dir: Path) -> list[dict[str, Any]]:
    """Scan and index all historical audit runs in the runs directory."""
    runs = []
    if not runs_dir.exists():
        return runs

    for child in sorted(runs_dir.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        result_file = child / "result.json"
        if not result_file.exists():
            continue

        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            runs.append({
                "run_id": data.get("run_id", child.name),
                "target_url": data.get("target_url", ""),
                "status": data.get("status", "COMPLETED"),
                "overall_score": data.get("score", {}).get("overall_score", 0.0),
                "confidence": data.get("score", {}).get("confidence", "medium"),
                "findings_count": len(data.get("findings", [])),
                "created_at": data.get("created_at", ""),
                "has_html": (child / "report.html").exists(),
                "has_pdf": (child / "report.pdf").exists(),
                "run_dir_name": child.name,
            })
        except Exception:
            continue

    return runs


def render_dashboard_html(runs: list[dict[str, Any]]) -> str:
    """Render a modern, high-impact organization dashboard HTML."""
    total_runs = len(runs)
    avg_score = round(sum(r["overall_score"] for r in runs) / total_runs, 1) if total_runs > 0 else 0.0
    total_flaws = sum(r["findings_count"] for r in runs)

    rows_html = []
    for r in runs:
        sc = r["overall_score"]
        color = "#10b981" if sc >= 85 else ("#f59e0b" if sc >= 70 else "#ef4444")
        html_link = f'<a href="/{r["run_dir_name"]}/report.html" class="btn" target="_blank">View HTML</a>' if r["has_html"] else ""
        pdf_link = f'<a href="/{r["run_dir_name"]}/report.pdf" class="btn btn-secondary" target="_blank">PDF</a>' if r["has_pdf"] else ""

        rows_html.append(f"""
        <tr>
          <td><strong>{r['run_id']}</strong><br><small style="color: #64748b;">{r['created_at'][:19]}</small></td>
          <td><a href="{r['target_url']}" target="_blank" style="color: #38bdf8; text-decoration: none;">{r['target_url']}</a></td>
          <td><span class="score-badge" style="background: {color}22; color: {color}; border: 1px solid {color};">{sc}/100</span></td>
          <td><span class="badge">{r['findings_count']} flaws</span></td>
          <td><div style="display: flex; gap: 0.5rem;">{html_link} {pdf_link}</div></td>
        </tr>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>NormanJr. Organization UX Dashboard</title>
  <style>
    :root {{
      --bg-primary: #0f172a;
      --bg-card: #1e293b;
      --text-primary: #f8fafc;
      --text-muted: #94a3b8;
      --border: #334155;
      --accent: #38bdf8;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      margin: 0;
      padding: 2.5rem;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; margin-bottom: 2rem; }}
    h1 {{ color: var(--accent); margin: 0; font-size: 1.8rem; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem; }}
    .stat-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 1.5rem; text-align: center; }}
    .stat-num {{ font-size: 2.5rem; font-weight: 800; color: #fff; line-height: 1.1; }}
    .stat-label {{ color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; margin-top: 0.5rem; letter-spacing: 0.05em; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
    th, td {{ padding: 1rem 1.25rem; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ background: #162032; color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; }}
    .score-badge {{ padding: 0.3rem 0.6rem; border-radius: 6px; font-weight: 700; font-family: monospace; font-size: 0.9rem; }}
    .badge {{ background: #334155; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }}
    .btn {{ background: #0284c7; color: #fff; text-decoration: none; padding: 0.4rem 0.8rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600; }}
    .btn-secondary {{ background: #334155; color: #e2e8f0; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>NormanJr. UX Intelligence Dashboard</h1>
        <p style="color: var(--text-muted); margin-top: 0.25rem;">Continuous Usability, Accessibility & Core Web Vitals Tracking</p>
      </div>
      <div>
        <span class="badge" style="background: #0369a1; color: #e0f2fe; padding: 0.5rem 1rem;">Active Repository</span>
      </div>
    </header>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-num">{total_runs}</div>
        <div class="stat-label">Total Audits</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="color: {'#10b981' if avg_score >= 80 else '#f59e0b'};">{avg_score}</div>
        <div class="stat-label">Average UX Index</div>
      </div>
      <div class="stat-card">
        <div class="stat-num" style="color: #f87171;">{total_flaws}</div>
        <div class="stat-label">Total Detected Flaws</div>
      </div>
    </div>

    <h2>Audit Run History</h2>
    <table>
      <thead>
        <tr>
          <th>Run ID</th>
          <th>Target URL</th>
          <th>UX Index</th>
          <th>Findings</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html) if rows_html else '<tr><td colspan="5" style="text-align: center; color: #64748b;">No runs found.</td></tr>'}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def start_dashboard_server(runs_dir: Path, port: int = 8000) -> None:
    """Start an HTTP server serving the dashboard and reports."""
    # Write dashboard.html to runs_dir
    runs = scan_all_runs(runs_dir)
    dash_html = render_dashboard_html(runs)
    (runs_dir / "index.html").write_text(dash_html, encoding="utf-8")

    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(runs_dir), **kwargs)

    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        print(f"NormanJr. Dashboard serving at http://localhost:{port}")
        httpd.serve_forever()
