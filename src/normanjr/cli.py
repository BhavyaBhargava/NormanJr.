"""Full CLI interface for NormanJr autonomous UX auditing agent."""

from __future__ import annotations

import asyncio
import json
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
from normanjr.reporting.comparator import compare_runs, format_comparison_markdown
from normanjr.reporting.dashboard import scan_all_runs, start_dashboard_server
from normanjr.reporting.patcher import format_patches_text, generate_remediation_patches
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
    search: str | None = typer.Option(None, "--search", "-s", help="Filter models by name (e.g. gemini, claude, llama)."),
    free: bool = typer.Option(False, "--free", help="Filter for free models only."),
    vision: bool = typer.Option(False, "--vision", help="Filter for multimodal/vision models."),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Path to TOML configuration"),
) -> None:
    """List available OpenRouter models, capabilities, and active configuration."""
    cfg = load_config(toml_path=config_path)
    active_model = cfg.model.requested_model
    source_str = ".env (OPENROUTER_MODEL)" if os.environ.get("OPENROUTER_MODEL") else "config/default.toml"

    console.print(Panel.fit(
        f"Active Model: [bold green]{active_model}[/bold green]\n"
        f"Source: [dim]{source_str}[/dim]\n"
        f"To change: Set [cyan]OPENROUTER_MODEL=\"<model_id>\"[/cyan] in [cyan].env[/cyan] or use [cyan]normanjr audit --model <model_id>[/cyan]",
        title="OpenRouter Model Configuration",
        border_style="cyan",
    ))

    async def _fetch():
        catalog = ModelCatalog()
        return await catalog.get_model_capabilities()

    with console.status("Fetching model catalog from OpenRouter..."):
        model_list = asyncio.run(_fetch())

    if not model_list:
        console.print("[yellow]No models found in cache or network failed.[/yellow]")
        return

    table = Table(title="OpenRouter Model Catalog", show_header=True)
    table.add_column("Model ID", style="cyan")
    table.add_column("Context", justify="right")
    table.add_column("Vision")
    table.add_column("Pricing (Prompt)")
    table.add_column("Status")

    for m in model_list:
        if free and not m.is_free:
            continue
        if vision and not m.supports_vision:
            continue
        if search and search.lower() not in m.model_id.lower():
            continue

        is_active = m.model_id == active_model
        status_tag = "[bold green]★ ACTIVE[/bold green]" if is_active else ""

        table.add_row(
            m.model_id,
            f"{m.context_length // 1000}k",
            "[green]YES[/green]" if m.supports_vision else "[dim]NO[/dim]",
            "[bold green]FREE[/bold green]" if m.is_free else f"${m.pricing_prompt*1e6:.2f}/M",
            status_tag,
        )

    console.print(table)


async def _run_audit_pipeline(
    url: str,
    goals: list[str] | None,
    config: AppConfig,
    headed: bool,
    output_dir: Path,
    run_id_override: str | None = None,
) -> int:
    run_id = run_id_override or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    repo = RunRepository(output_dir, run_id)
    repo.save_config_snapshot(config)

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
        llm_client = OpenRouterClient(
            api_key,
            settings=config.model,
            http_referer=config.openrouter_http_referer,
            title=config.openrouter_title,
        )

    engine_status = f"[bold green]{config.model.requested_model}[/bold green] (OpenRouter AI Reasoning)" if llm_client else "[yellow]Deterministic / Heuristic Mode (No API key)[/yellow]"

    console.print(Panel.fit(
        f"[bold cyan]NormanJr. Audit Session[/bold cyan]\n"
        f"Target URL: [bold]{url}[/bold]\n"
        f"Profile: [bold green]{config.browser.profile.upper()}[/bold green] ({config.browser.viewport_width}x{config.browser.viewport_height})\n"
        f"Browser: [bold cyan]{config.browser.browser_name}[/bold cyan]\n"
        f"LLM Engine: {engine_status}\n"
        f"Run ID: [dim]{run_id}[/dim]\n"
        f"Artifacts: [dim]{repo.run_dir}[/dim]",
        border_style="cyan",
    ))

    # Initialize browser settings
    browser_settings = config.browser.model_copy()
    if headed:
        browser_settings.headless = False

    mcp_client = PlaywrightMcpClient(browser_settings, output_dir=repo.run_dir)

    console.print("[dim]Connecting to Playwright MCP and launching isolated browser...[/dim]")

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

        elif llm_client:
            try:
                with console.status(f"[bold cyan]Formulating exploratory journeys using {config.model.requested_model}...[/bold cyan]"):
                    snap = await adapter.take_snapshot()
                    resp = await llm_client.generate_journeys(url, snap)
                    for i, pj in enumerate(resp.journeys[:config.exploration.max_journeys]):
                        journey_list.append(Journey(
                            journey_id=f"j{i+1}",
                            goal=pj.goal,
                            persona=pj.persona,
                        ))

            except Exception as e:
                console.print(f"[dim yellow]Model journey planning fallback: {e}[/dim yellow]")

        if not journey_list:
            journey_list.append(Journey(journey_id="j1", goal="Explore core navigation, performance, and interactive controls"))

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
    profile: str = typer.Option("desktop", "--profile", help="Viewport profile: desktop, mobile, mobile-safari, or both"),
    browser: str = typer.Option("chromium", "--browser", help="Browser engine: chromium, firefox, or webkit"),
    concurrency: int = typer.Option(1, "--concurrency", help="Number of concurrent browser worker sessions"),
    crawl_mode: str = typer.Option("standard", "--crawl-mode", help="Crawling scope: standard or full (unrestricted sitemap crawl)"),
    model: str | None = typer.Option(None, "--model", "-m", help="OpenRouter model ID"),
    low_call: bool = typer.Option(False, "--low-call", help="Enable low-call token saving mode"),
    max_journeys: int | None = typer.Option(None, "--max-journeys", help="Maximum journeys to explore"),
    max_steps: int | None = typer.Option(None, "--max-steps", help="Maximum steps per journey"),
    allow_private_target: bool = typer.Option(False, "--allow-private-target", help="Allow auditing local/private hosts"),
    authorized: bool = typer.Option(False, "--authorized", help="Confirm authorization and skip private IP blocking"),
    allow_final_submit: bool = typer.Option(False, "--allow-final-submit", help="Permit final form submission"),
    high_impact: bool = typer.Option(False, "--high-impact", help="Allow autonomous completion of high-impact/purchase workflows"),
    storage_state: str | None = typer.Option(None, "--storage-state", help="Path to saved session state JSON"),
    save_storage_state: str | None = typer.Option(None, "--save-storage-state", help="Path to save session state after run"),
    stealth: bool = typer.Option(False, "--stealth", help="Enable stealth mode to bypass anti-bot challenges"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in visible mode"),
    output: str | None = typer.Option(None, "--output", "-o", help="Custom output directory"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Path to TOML configuration"),
    json_output: bool = typer.Option(False, "--json", help="Print summary as machine-readable JSON"),
) -> None:
    """Run an autonomous evidence-based UX audit on the given URL."""
    overrides: dict[str, Any] = {}
    if max_journeys is not None:
        overrides["exploration.max_journeys"] = max_journeys
    if max_steps is not None:
        overrides["exploration.max_steps_per_journey"] = max_steps
    if allow_private_target or authorized:
        overrides["safety.allow_private_target"] = True
    if allow_final_submit or high_impact:
        overrides["safety.allow_final_submit"] = True
    if model:
        overrides["model.requested_model"] = model
    if browser:
        overrides["browser.browser_name"] = browser
    if storage_state:
        overrides["browser.storage_state_path"] = storage_state
    if save_storage_state:
        overrides["browser.save_storage_state_path"] = save_storage_state
    if stealth:
        overrides["browser.stealth"] = True
    if crawl_mode.lower() == "full":
        overrides["exploration.same_origin_only"] = False
        overrides["exploration.max_pages"] = 100

    cfg = load_config(toml_path=config_path, overrides=overrides)
    out_dir = Path(output) if output else Path(cfg.report.output_directory)

    # Normalize url
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"https://{url}"

    # Handle profile
    if profile.lower() == "both":
        # Audit desktop first, then mobile
        cfg.browser.apply_profile("desktop")
        console.print("[bold cyan]Running Phase 1: Desktop Audit...[/bold cyan]")
        c1 = asyncio.run(_run_audit_pipeline(url=url, goals=goal, config=cfg, headed=headed, output_dir=out_dir))
        
        cfg_m = cfg.model_copy(deep=True)
        cfg_m.browser.apply_profile("mobile")
        console.print("[bold cyan]Running Phase 2: Mobile Viewport Audit...[/bold cyan]")
        c2 = asyncio.run(_run_audit_pipeline(url=url, goals=goal, config=cfg_m, headed=headed, output_dir=out_dir))
        sys.exit(max(c1, c2))
    else:
        cfg.browser.apply_profile(profile)
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
def resume(
    run_id: str = typer.Argument(..., help="Run ID of the interrupted or partial audit"),
    runs_dir: str = typer.Option("runs", "--runs-dir", help="Base runs directory"),
    headed: bool = typer.Option(False, "--headed", help="Run browser in visible mode"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Path to TOML configuration"),
) -> None:
    """Resume an interrupted audit run from its stored checkpoint."""
    run_path = Path(runs_dir) / run_id
    if not run_path.exists():
        console.print(f"[bold red]Run directory not found:[/bold red] {run_path}")
        sys.exit(1)

    result_file = run_path / "result.json"
    if not result_file.exists():
        console.print(f"[bold red]result.json not found for run:[/bold red] {run_id}")
        sys.exit(1)

    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_url = data.get("target_url")
    if not target_url:
        console.print("[bold red]Could not find target URL in previous run record.[/bold red]")
        sys.exit(1)

    cfg = load_config(toml_path=config_path)
    console.print(f"[bold cyan]Resuming audit for run {run_id} ({target_url})...[/bold cyan]")

    code = asyncio.run(_run_audit_pipeline(
        url=target_url,
        goals=None,
        config=cfg,
        headed=headed,
        output_dir=Path(runs_dir),
        run_id_override=run_id,
    ))
    sys.exit(code)


@app.command()
def compare(
    baseline_run_id: str = typer.Argument(..., help="Baseline run ID or directory"),
    current_run_id: str = typer.Argument(..., help="Current run ID or directory"),
    runs_dir: str = typer.Option("runs", "--runs-dir", help="Base runs directory"),
    json_output: bool = typer.Option(False, "--json", help="Output comparison as JSON"),
    output_file: str | None = typer.Option(None, "--output", "-o", help="Path to save markdown regression report"),
) -> None:
    """Compare two audit runs to detect score deltas, regressions, and resolved flaws."""
    dir1 = Path(baseline_run_id) if Path(baseline_run_id).exists() else Path(runs_dir) / baseline_run_id
    dir2 = Path(current_run_id) if Path(current_run_id).exists() else Path(runs_dir) / current_run_id

    try:
        diff = compare_runs(dir1, dir2)
    except Exception as e:
        console.print(f"[bold red]Comparison failed:[/bold red] {e}")
        sys.exit(1)

    if json_output:
        console.print(json.dumps(diff, indent=2))
        return

    md_report = format_comparison_markdown(diff)
    if output_file:
        Path(output_file).write_text(md_report, encoding="utf-8")
        console.print(f"[bold green]Saved regression report to {output_file}[/bold green]")

    score_color = "green" if diff["score_delta"] >= 0 else "red"
    console.print(Panel.fit(
        f"Baseline: [dim]{diff['baseline_run_id']}[/dim] ({diff['baseline_score']}/100)\n"
        f"Current:  [bold]{diff['current_run_id']}[/bold] ({diff['current_score']}/100)\n"
        f"Score Delta: [{score_color}]{'+' if diff['score_delta'] >= 0 else ''}{diff['score_delta']}[/{score_color}]\n"
        f"Resolved Flaws: [bold green]{diff['counts']['resolved']}[/bold green] | "
        f"Regressions: [bold red]{diff['counts']['regressed_new']}[/bold red] | "
        f"Persistent: [yellow]{diff['counts']['persistent']}[/yellow]",
        title="UX Regression Comparison",
        border_style="cyan",
    ))

    table = Table(title="Category Score Movements", show_header=True)
    table.add_column("Category")
    table.add_column("Baseline", justify="right")
    table.add_column("Current", justify="right")
    table.add_column("Delta", justify="right")

    for c in diff["category_deltas"]:
        d = c["delta"]
        c_color = "green" if d > 0 else ("red" if d < 0 else "dim")
        table.add_row(
            c["category_name"],
            str(c["baseline_score"]),
            str(c["current_score"]),
            f"[{c_color}]{'+' if d > 0 else ''}{d}[/{c_color}]",
        )
    console.print(table)


@app.command()
def patch(
    run_id: str = typer.Argument(..., help="Run ID to generate fixes for"),
    runs_dir: str = typer.Option("runs", "--runs-dir", help="Base runs directory"),
    output_file: str | None = typer.Option(None, "--output", "-o", help="Output file path (e.g. fixes.patch)"),
) -> None:
    """Generate CSS, HTML, and ARIA remediation code patches for detected findings."""
    run_path = Path(runs_dir) / run_id
    try:
        patch_data = generate_remediation_patches(run_path)
    except Exception as e:
        console.print(f"[bold red]Patch generation failed:[/bold red] {e}")
        sys.exit(1)

    formatted = format_patches_text(patch_data)
    if output_file:
        Path(output_file).write_text(formatted, encoding="utf-8")
        console.print(f"[bold green]Saved {patch_data['total_patches']} remediation patches to {output_file}[/bold green]")
    else:
        console.print(formatted)


@app.command()
def login(
    url: str = typer.Argument(..., help="Login page URL to authenticate"),
    save_state: str = typer.Option("storage-state.json", "--save-storage-state", "-s", help="Path to save authenticated session JSON"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Path to TOML configuration"),
) -> None:
    """Launch interactive headed browser session to authenticate and capture session storage."""
    cfg = load_config(toml_path=config_path)
    cfg.browser.headless = False
    cfg.browser.save_storage_state_path = save_state

    console.print(Panel.fit(
        f"[bold cyan]Interactive Authentication Session[/bold cyan]\n"
        f"Target URL: [bold]{url}[/bold]\n"
        f"Storage Output: [bold green]{save_state}[/bold green]\n"
        f"Complete your login in the open browser window. Session cookies will be saved automatically upon closing.",
        border_style="cyan",
    ))

    async def _login():
        client = PlaywrightMcpClient(cfg.browser)
        async with client.connect() as session:
            url_pol = UrlPolicy(cfg.exploration, cfg.safety, initial_origin=url)
            adapter = PlaywrightAdapter(session, url_policy=url_pol)
            await adapter.navigate(url)
            console.print("[dim]Browser open. Perform login actions... (Press Ctrl+C or close browser when finished)[/dim]")
            await asyncio.sleep(60)

    try:
        asyncio.run(_login())
    except KeyboardInterrupt:
        pass
    console.print(f"[bold green]Session state saved to {save_state}[/bold green]")


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    runs_dir: str = typer.Option("runs", "--runs-dir", help="Base runs directory"),
) -> None:
    """Start organization UX intelligence web dashboard server."""
    rpath = Path(runs_dir)
    if not rpath.exists():
        rpath.mkdir(parents=True, exist_ok=True)
    console.print(f"[bold green]Starting NormanJr. Dashboard on http://localhost:{port}[/bold green]")
    start_dashboard_server(rpath, port=port)


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


@app.command()
def ingest(
    telemetry_file: str = typer.Argument(..., help="Path to PostHog/GA4/RUM telemetry JSON file"),
    save_journeys: str | None = typer.Option(None, "--save-journeys", "-s", help="Path to save generated journey JSON"),
) -> None:
    """Ingest real-user analytics/telemetry to synthesize prioritized audit journeys."""
    from normanjr.telemetry.ingestion import ingest_telemetry_file

    tpath = Path(telemetry_file)
    if not tpath.exists():
        console.print(f"[bold red]Telemetry file not found:[/bold red] {tpath}")
        sys.exit(1)

    try:
        res = ingest_telemetry_file(tpath)
    except Exception as e:
        console.print(f"[bold red]Telemetry ingestion failed:[/bold red] {e}")
        sys.exit(1)

    console.print(Panel.fit(
        f"Analyzed Events: [bold green]{res['total_events_analyzed']}[/bold green]\n"
        f"Synthesized Journeys: [bold cyan]{len(res['generated_journeys'])}[/bold cyan]\n"
        f"High Drop-off Targets: {', '.join(res['high_dropoff_targets']) if res['high_dropoff_targets'] else 'None'}",
        title="Telemetry Ingestion Results",
        border_style="cyan",
    ))

    if save_journeys:
        Path(save_journeys).write_text(json.dumps(res["generated_journeys"], indent=2), encoding="utf-8")
        console.print(f"[bold green]Saved journeys to {save_journeys}[/bold green]")
    else:
        for j in res["generated_journeys"]:
            console.print(f"- [bold]{j['journey_id']}:[/bold] {j['goal']}")


if __name__ == "__main__":
    app()
