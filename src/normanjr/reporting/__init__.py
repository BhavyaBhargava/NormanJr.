"""Reporting package for NormanJr."""

from normanjr.reporting.builder import generate_reports
from normanjr.reporting.html import render_html_report
from normanjr.reporting.pdf import render_pdf_report

__all__ = [
    "generate_reports",
    "render_html_report",
    "render_pdf_report",
]
