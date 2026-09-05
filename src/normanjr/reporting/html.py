"""HTML report generation using escaped Jinja2 templates."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from normanjr.domain.models import AuditRun
from normanjr.storage.artifacts import atomic_write_text
from normanjr.version import __version__


def render_html_report(audit_run: AuditRun, output_dir: Path) -> Path:
    """Render self-contained HTML report with embedded CSS."""
    pkg_dir = Path(__file__).parent
    template_dir = pkg_dir / "templates"
    css_file = pkg_dir / "assets" / "report.css"

    css_content = css_file.read_text(encoding="utf-8") if css_file.exists() else ""

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    template = env.get_template("report.html.j2")

    html = template.render(
        run=audit_run,
        css_content=css_content,
        version=__version__,
    )

    target_path = output_dir / "report.html"
    atomic_write_text(target_path, html)
    return target_path
