"""Diagnostics and health checks for NormanJr."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from rich.console import Console
from rich.table import Table

from normanjr.config import AppConfig, load_config
from normanjr.version import __version__


class CheckResult(NamedTuple):
    name: str
    status: bool  # True = pass, False = fail
    details: str
    is_warning: bool = False


def check_python() -> CheckResult:
    v = sys.version_info
    status = v.major == 3 and v.minor >= 12
    return CheckResult(
        name="Python Runtime",
        status=status,
        details=f"Python {v.major}.{v.minor}.{v.micro} ({sys.executable})",
        is_warning=not status,
    )


def check_node() -> CheckResult:
    node_path = shutil.which("node")
    if not node_path:
        return CheckResult(
            name="Node.js",
            status=False,
            details="Node.js executable not found in PATH",
            is_warning=False,
        )
    try:
        out = subprocess.check_output([node_path, "--version"], text=True).strip()
        return CheckResult(
            name="Node.js",
            status=True,
            details=f"{out} ({node_path})",
        )
    except Exception as e:
        return CheckResult(
            name="Node.js",
            status=False,
            details=f"Failed to query node: {e}",
        )


def check_mcp_binary() -> CheckResult:
    mcp_bin = Path("node_modules/.bin/playwright-mcp")
    if mcp_bin.exists() and os.access(mcp_bin, os.X_OK):
        return CheckResult(
            name="Playwright MCP Binary",
            status=True,
            details=f"Found executable {mcp_bin}",
        )
    return CheckResult(
        name="Playwright MCP Binary",
        status=False,
        details=f"Missing or non-executable {mcp_bin}. Run `npm install`.",
    )


def check_axe_core() -> CheckResult:
    axe_path = Path("node_modules/axe-core/axe.min.js")
    if axe_path.exists():
        size_kb = axe_path.stat().st_size / 1024
        return CheckResult(
            name="axe-core Asset",
            status=True,
            details=f"Found {axe_path} ({size_kb:.1f} KB)",
        )
    return CheckResult(
        name="axe-core Asset",
        status=False,
        details=f"Missing {axe_path}. Run `npm install`.",
    )


def check_chromium() -> CheckResult:
    mcp_bin = Path("node_modules/.bin/playwright-mcp")
    if not mcp_bin.exists():
        return CheckResult(
            name="Playwright Browser",
            status=False,
            details="Playwright MCP binary not installed.",
        )
    # Check if playwright chromium cache directory exists
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    chromium_dirs = list(cache_dir.glob("chromium*")) if cache_dir.exists() else []
    if chromium_dirs:
        latest = sorted(chromium_dirs)[-1].name
        return CheckResult(
            name="Playwright Browser",
            status=True,
            details=f"Installed in ~/.cache/ms-playwright ({latest})",
        )
    return CheckResult(
        name="Playwright Browser",
        status=False,
        details="No Chromium browser found in ~/.cache/ms-playwright. Run `npx playwright install chromium`.",
    )


def check_openrouter_key(config: AppConfig) -> CheckResult:
    key = config.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
    if key and key.strip():
        masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "***"
        return CheckResult(
            name="OpenRouter API Key",
            status=True,
            details=f"Present ({masked})",
        )
    return CheckResult(
        name="OpenRouter API Key",
        status=True,
        details="Not configured. Deterministic audits and offline tests work without an API key.",
        is_warning=True,
    )


def check_model_config(config: AppConfig) -> CheckResult:
    model_name = config.model.requested_model
    source = ".env (OPENROUTER_MODEL)" if os.environ.get("OPENROUTER_MODEL") else "default.toml"
    return CheckResult(
        name="Configured LLM Model",
        status=True,
        details=f"{model_name} (via {source})",
    )


def check_live_model_probe(config: AppConfig) -> CheckResult:
    key = config.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key or not key.strip():
        return CheckResult(
            name="OpenRouter Live Probe",
            status=False,
            details="Skipped: No OPENROUTER_API_KEY found in .env or environment.",
            is_warning=True,
        )
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": config.openrouter_http_referer or "",
            "X-Title": config.openrouter_title or "",
        }
        payload = {
            "model": config.model.requested_model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            provider = data.get("provider", "OpenRouter")
            return CheckResult(
                name="OpenRouter Live Probe",
                status=True,
                details=f"Verified connection to {config.model.requested_model} [{provider}]",
            )
        else:
            return CheckResult(
                name="OpenRouter Live Probe",
                status=False,
                details=f"HTTP {resp.status_code}: {resp.text[:120]}",
                is_warning=False,
            )
    except Exception as e:
        return CheckResult(
            name="OpenRouter Live Probe",
            status=False,
            details=f"Failed to probe {config.model.requested_model}: {e}",
            is_warning=False,
        )


def check_output_dir(config: AppConfig) -> CheckResult:
    out_dir = Path(config.report.output_directory)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        test_file = out_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return CheckResult(
            name="Run Storage Directory",
            status=True,
            details=f"Writable ({out_dir.resolve()})",
        )
    except Exception as e:
        return CheckResult(
            name="Run Storage Directory",
            status=False,
            details=f"Directory {out_dir} is not writable: {e}",
        )


def run_doctor(config: AppConfig | None = None, check_model: bool = False) -> bool:
    """Run all diagnostics checks and print rich report. Returns True if all required checks pass."""
    console = Console()
    console.print(f"[bold cyan]NormanJr. System Diagnostics[/bold cyan] (v{__version__})\n")

    if config is None:
        try:
            config = load_config()
        except Exception as e:
            console.print(f"[bold red]Configuration error:[/bold red] {e}")
            return False

    checks = [
        check_python(),
        check_node(),
        check_mcp_binary(),
        check_chromium(),
        check_axe_core(),
        check_openrouter_key(config),
        check_model_config(config),
        check_output_dir(config),
    ]

    if check_model:
        with console.status(f"[bold cyan]Probing OpenRouter model {config.model.requested_model}...[/bold cyan]"):
            checks.append(check_live_model_probe(config))

    table = Table(title="System Readiness Checks", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="dim", width=26)
    table.add_column("Status", width=12)
    table.add_column("Details")

    all_passed = True
    for c in checks:
        if not c.status and not c.is_warning:
            all_passed = False
            status_str = "[bold red]FAIL[/bold red]"
        elif c.is_warning:
            status_str = "[yellow]WARN[/yellow]"
        else:
            status_str = "[bold green]PASS[/bold green]"

        table.add_row(c.name, status_str, c.details)

    console.print(table)
    console.print()

    if all_passed:
        console.print("[bold green]✔ All critical system checks passed![/bold green]")
    else:
        console.print("[bold red]✖ Some critical system checks failed. Review issues above.[/bold red]")

    return all_passed

