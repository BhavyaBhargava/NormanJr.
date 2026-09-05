"""Full CLI interface for NormanJr autonomous UX auditing agent."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from normanjr.audit.rubric import load_rubric
from normanjr.config import AppConfig, load_config
from normanjr.doctor import run_doctor
from normanjr.domain.enums import AuditStatus
from normanjr.domain.models import Journey
from normanjr.exploration.context import AuditContext
from normanjr.exploration.graph import build_audit_graph
from normanjr.llm.client import OpenRouterClient
from normanjr.llm.model_catalog import ModelCatalog
from normanjr.mcp.client import PlaywrightMcpClient
from normanjr.mcp.playwright_adapter import PlaywrightAdapter
from normanjr.reporting.builder import generate_reports
from normanjr.security.action_policy import ActionPolicy
from normanjr.security.url_policy import UrlPolicy, UrlPolicyError
from normanjr.storage.run_repository import RunRepository
from normanjr.version import __version__

app = typer.Typer(
    name="normanjr",
    help="Autonomous, evidence-based UX auditing for web applications.",
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Show NormanJr. version."""
    console.print(f"[bold cyan]NormanJr.[/bold cyan] version [green]{__version__}[/green]")


@app.command()
def doctor(
    check_model: bool = typer.Option(
        False, "--check-model", help="Perform a live probe of the configured OpenRouter model."
    ),
    config_path: str | None = typer.Option(
        None, "--config", "-c", help="Path to custom configuration TOML."
    ),
) -> None:
    """Verify toolchain, dependencies, browser, and MCP contracts."""
    try:
        cfg = load_config(toml_path=config_path)
    except Exception as e:
        console.print(f"[bold red]Failed to load configuration:[/bold red] {e}")
        sys.exit(1)

    ok = run_doctor(config=cfg, check_model=check_model)
    if not ok:
        sys.exit(1)


@app.command()
def models(
    free: bool = typer.Option(False, "--free", help="Filter for free models only."),
    vision: bool = typer.Option(False, "--vision", help="Filter for multimodal/vision models."),
) -> None:
    """List available OpenRouter models and capabilities."""
    async def _fetch():
        catalog = ModelCatalog()
        return await catalog.get_model_capabilities()

    with console.status("Fetching model catalog..."):
        model_list = asyncio.run(_fetch())

    if not model_list:
        console.print("[yellow]No models found in cache or network failed.[/yellow]")
        return

    table = Table(title="OpenRouter Model Capabilities", show_header=True)
    table.add_column("Model ID", style="cyan")
    table.add_column("Context", justify="right")
    table.add_column("Vision")
    table.add_column("Free")

    for m in model_list:
        if free and not m.is_free:
            continue
        if vision and not m.supports_vision:
            continue

        table.add_row(
            m.model_id,
            f"{m.context_length // 1000}k",
            "[green]YES[/green]" if m.supports_vision else "[dim]NO[/dim]",
            "[bold green]FREE[/bold green]" if m.is_free else f"${m.pricing_prompt*1e6:.2f}/M",
        )

    console.print(table)


async def _run_audit_pipeline(
    url: str,
    goals: list[str] | None,
    config: AppConfig,
    headed: bool,
    output_dir: Path,
) -> int:
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    repo = RunRepository(output_dir, run_id)
    repo.save_config_snapshot(config)

    console.print(Panel.fit(
        f"[bold cyan]NormanJr. Audit Session[/bold cyan]\n"
        f"Target: [bold]{url}[/bold]\n"
        f"Run ID: [dim]{run_id}[/dim]\n"
        f"Directory: [dim]{repo.run_dir}[/dim]",
        border_style="cyan",
    ))

    # Initialize policies
    url_policy = UrlPolicy(config.exploration, config.safety, initial_origin=url)
    try:
        url_policy.validate_url(url)
    except UrlPolicyError as e:
        console.print(f"[bold red]Target URL Blocked:[/bold red] {e}")
        return 2

    action_policy = ActionPolicy(config.safety)
    rubric = load_rubric(config.scoring.rubric_path)

    # OpenRouter client if key present
    llm_client: OpenRouterClient | None = None
    api_key = config.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        llm_client = OpenRouterClient(api_key, settings=config.model)

    # Initialize browser settings
    browser_settings = config.browser.model_copy()
    if headed:
        browser_settings.headless = False

    mcp_client = PlaywrightMcpClient(browser_settings, output_dir=repo.run_dir)

    console.print("[dim]Connecting to Playwright MCP and launching isolated Chromium...[/dim]")

    async with mcp_client.connect() as session:
        adapter = PlaywrightAdapter(session, url_policy=url_policy)

        with console.status("[bold green]Navigating to target URL...[/bold green]"):
            await adapter.navigate(url)

        context = AuditContext(
            adapter=adapter,
            action_policy=action_policy,
            url_policy=url_policy,
            repo=repo,
            config=config,
            rubric=rubric,
            llm_client=llm_client,
        )

        # Plan journeys
        journey_list = []
        if goals:
            for i, g in enumerate(goals):
                journey_list.append(Journey(journey_id=f"j{i+1}", goal=g))
        else:
            journey_list.append(Journey(journey_id="j1", goal="Explore core navigation and interactive controls"))

        initial_state = {
            "run_id": run_id,
            "target_url": url,
            "journeys": journey_list,
            "current_journey_index": 0,
            "current_step_number": 0,
            "all_findings": [],
            "visited_state_fingerprints": [],
            "status": AuditStatus.RUNNING,
        }

        graph = build_audit_graph()

        console.print(f"[bold green]Starting exploration across {len(journey_list)} journey(s)...[/bold green]")
        final_state = await graph.ainvoke(
            initial_state,
            config={"configurable": {"context": context}},
        )

    # Generate Reports
    console.print("[dim]Generating HTML and PDF reports...[/dim]")
    reports = await generate_reports(repo.run_dir, output_format="all")

    # Display summary
    result = repo.load_result()
    score_val = result.score.overall_score if result.score else 0.0

    score_color = "green" if score_val >= 85 else ("yellow" if score_val >= 70 else "red")

    console.print("\n" + "=" * 60)
    console.print(f"[bold]Audit Completed for:[/bold] {url}")
    console.print(f"[bold]Overall UX Index:[/bold] [{score_color}]{score_val}/100[/{score_color}]")
    console.print(f"[bold]Confirmed Findings:[/bold] {len(result.findings)}")
    if reports.get("html"):
        console.print(f"[bold]HTML Report:[/bold] file://{reports['html']}")
    if reports.get("pdf"):
        console.print(f"[bold]PDF Report:[/bold]  file://{reports['pdf']}")
    console.print("=" * 60 + "\n")

    return 0


@app.command()
def audit(
    url: str = typer.Argument(..., help="Target URL to audit"),
    goal: list[str] = typer.Option(None, "--goal", "-g", help="Explicit journey goal (repeatable)"),
    profile: str = typer.Option("desktop", "--profile", help="Viewport profile: desktop, mobile, or both"),
    model: str | None = typer.Option(None, "--model", "-m", help="OpenRouter model ID"),
    low_call: bool = typer.Option(False, "--low-call", help="Enable low-call token saving mode"),
    max_journeys: int | None = typer.Option(None, "--max-journeys", help="Maximum journeys to explore"),
    max_steps: int | None = typer.Option(None, "--max-steps", help="Maximum steps per journey"),
    allow_private_target: bool = typer.Option(False, "--allow-private-target", help="Allow auditing local/private hosts"),
    allow_final_submit: bool = typer.Option(False, "--allow-final-submit", help="Permit final form submission"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in visible mode"),
    output: str | None = typer.Option(None, "--output", "-o", help="Custom output directory"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Path to TOML configuration"),
    json_output: bool = typer.Option(False, "--json", help="Print summary as machine-readable JSON"),
) -> None:
    """Run an autonomous evidence-based UX audit on the given URL."""
    overrides = {}
    if max_journeys is not None:
        overrides["exploration.max_journeys"] = max_journeys
    if max_steps is not None:
        overrides["exploration.max_steps_per_journey"] = max_steps
    if allow_private_target:
        overrides["safety.allow_private_target"] = True
    if allow_final_submit:
        overrides["safety.allow_final_submit"] = True
    if model:
        overrides["model.requested_model"] = model

    cfg = load_config(toml_path=config_path, overrides=overrides)
    out_dir = Path(output) if output else Path(cfg.report.output_directory)

    # Normalize url
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"https://{url}"

    code = asyncio.run(_run_audit_pipeline(
        url=url,
        goals=goal,
        config=cfg,
        headed=headed,
        output_dir=out_dir,
    ))

    if code != 0:
        sys.exit(code)


@app.command()
def report(
    run_id: str = typer.Argument(..., help="Run ID of the completed or partial audit"),
    format: str = typer.Option("all", "--format", "-f", help="Output format: html, pdf, or all"),
    runs_dir: str = typer.Option("runs", "--runs-dir", help="Base runs directory"),
) -> None:
    """Regenerate HTML/PDF reports from an existing run's canonical JSON."""
    run_path = Path(runs_dir) / run_id
    if not run_path.exists():
        console.print(f"[bold red]Run directory not found:[/bold red] {run_path}")
        sys.exit(1)

    async def _gen():
        return await generate_reports(run_path, output_format=format)

    with console.status(f"Regenerating {format} report for {run_id}..."):
        results = asyncio.run(_gen())

    console.print(f"[bold green]Report regeneration complete for {run_id}:[/bold green]")
    for fmt, path in results.items():
        if path:
            console.print(f" - {fmt.upper()}: file://{path}")


@app.command()
def inspect(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
    runs_dir: str = typer.Option("runs", "--runs-dir", help="Base runs directory"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Inspect state, events, and findings of a specific audit run."""
    run_path = Path(runs_dir) / run_id
    result_file = run_path / "result.json"

    if not result_file.exists():
        console.print(f"[bold red]result.json not found in:[/bold red] {run_path}")
        sys.exit(1)

    import json
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if json_output:
        console.print(json.dumps(data, indent=2))
        return

    score = data.get("score", {})
    console.print(f"[bold cyan]Run Summary:[/bold cyan] {run_id}")
    console.print(f"Target URL: {data.get('target_url')}")
    console.print(f"Overall Score: [bold green]{score.get('overall_score')}/100[/bold green]")
    console.print(f"Confidence: {score.get('confidence')}")
    console.print(f"Findings Count: {len(data.get('findings', []))}")


if __name__ == "__main__":
    app()
