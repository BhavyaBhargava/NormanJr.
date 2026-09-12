# CLI Reference

NormanJr. provides a command-line interface for running audits, managing sessions, diffing runs, generating code remediation patches, and viewing historical dashboards.

---

## Global Syntax

```bash
normanjr [OPTIONS] COMMAND [ARGS]...
```

To see available commands and flags:

```bash
normanjr --help
```

---

## Command Overview

| Command | Purpose |
|---|---|
| [`audit`](#normanjr-audit) | Run an autonomous, evidence-based UX audit on a target web application. |
| [`doctor`](#normanjr-doctor) | Verify system toolchain, dependencies, browser binaries, and model contracts. |
| [`models`](#normanjr-models) | Query and inspect available models, context lengths, and vision support. |
| [`compare`](#normanjr-compare) | Diff two audit runs to detect score deltas, regressions, and resolved issues. |
| [`patch`](#normanjr-patch) | Generate CSS, HTML, and ARIA code remediation patches for detected issues. |
| [`login`](#normanjr-login) | Interactive browser session to authenticate and capture session storage state. |
| [`serve`](#normanjr-serve) | Start a local UX intelligence web dashboard indexing all historical runs. |
| [`report`](#normanjr-report) | Regenerate HTML or PDF reports from an existing run's canonical JSON. |
| [`inspect`](#normanjr-inspect) | Inspect state, event streams, and recorded findings of a specific audit run. |
| [`ingest`](#normanjr-ingest) | Ingest real-user analytics (PostHog, GA4) to synthesize prioritized audit journeys. |
| [`resume`](#normanjr-resume) | Resume an interrupted audit run from its stored durable checkpoint. |
| [`version`](#normanjr-version) | Display the current installed version of NormanJr. |

---

## normanjr audit

Execute an autonomous UX audit against a target URL.

### Usage

```bash
normanjr audit <URL> [OPTIONS]
```

### Arguments

- `<URL>` *(required)*: The HTTP or HTTPS URL to audit.

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--goal`, `-g` | List[str] | `None` | Explicit user journey goal to explore (repeatable for multiple journeys). |
| `--profile` | str | `desktop` | Viewport profile: `desktop`, `mobile`, `mobile-safari`, or `both`. |
| `--browser` | str | `chromium` | Browser engine: `chromium`, `firefox`, or `webkit`. |
| `--model`, `-m` | str | `None` | AI reasoning model ID (overrides `.env` and configuration). |
| `--low-call` | Flag | `False` | Enable low-call token optimization mode. |
| `--max-journeys` | int | `3` | Maximum number of exploratory user journeys. |
| `--max-steps` | int | `20` | Maximum interaction steps per journey. |
| `--headed` | Flag | `False` | Launch browser in visible, interactive mode. |
| `--storage-state` | str | `None` | Path to saved authentication cookies and storage state JSON. |
| `--save-storage-state` | str | `None` | Path to save cookies/session storage after the run. |
| `--allow-private-target` | Flag | `False` | Allow auditing `localhost` or private internal network hosts. |
| `--allow-final-submit` | Flag | `False` | Permit executing final form submission actions. |
| `--stealth` | Flag | `False` | Enable stealth browsing configurations to minimize challenge interruptions. |
| `--output`, `-o` | str | `runs` | Directory where audit artifacts will be stored. |
| `--config`, `-c` | str | `None` | Path to custom TOML configuration file. |
| `--json` | Flag | `False` | Output audit summary to stdout as machine-readable JSON. |

### Examples

```bash
# Basic audit on public site
normanjr audit https://example.com

# Multi-goal audit with custom steps
normanjr audit https://ecommerce.store.com \
  --goal "Find women's jackets" \
  --goal "Select a jacket and check shipping details" \
  --max-steps 15

# Audit mobile responsive viewport
normanjr audit https://example.com --profile mobile

# Audit local development server with private target override
normanjr audit http://localhost:3000 --allow-private-target
```

---

## normanjr doctor

Inspect the health of your environment, required tools, browser engines, and model connectivity.

### Usage

```bash
normanjr doctor [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--check-model` | Flag | `False` | Perform a live probe and capability check against the configured model. |
| `--config`, `-c` | str | `None` | Path to custom configuration TOML. |

### Example

```bash
normanjr doctor --check-model
```

---

## normanjr models

List, search, and inspect available models, pricing, and vision capabilities.

### Usage

```bash
normanjr models [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--search`, `-s` | str | `None` | Filter models by keyword (e.g., `gemini`, `claude`, `llama`). |
| `--free` | Flag | `False` | Filter to show only free-tier models. |
| `--vision` | Flag | `False` | Filter to show only models supporting multimodal image input. |
| `--config`, `-c` | str | `None` | Path to custom configuration TOML. |

### Example

```bash
normanjr models --vision --search gemini
```

---

## normanjr compare

Perform visual, scoring, and finding regression analysis between a baseline run and a current run.

### Usage

```bash
normanjr compare <BASELINE_RUN_ID> <CURRENT_RUN_ID> [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--runs-dir` | str | `runs` | Base runs directory containing audit artifacts. |
| `--output`, `-o` | str | `None` | File path to write the formatted markdown comparison report. |
| `--json` | Flag | `False` | Output comparison data as structured JSON. |

### Example

```bash
normanjr compare run-20260901-baseline run-20260912-current --output regression.md
```

---

## normanjr patch

Generate ready-to-apply CSS, HTML, and ARIA remediation code snippets for findings detected during an audit.

### Usage

```bash
normanjr patch <RUN_ID> [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--runs-dir` | str | `runs` | Base runs directory. |
| `--output`, `-o` | str | `None` | File path to save generated patches (e.g. `fixes.patch`). |

### Example

```bash
normanjr patch run-20260912-120000-abc123 --output fixes.patch
```

---

## normanjr login

Launch an interactive headed browser window to complete complex authentication flows, capturing cookies and storage tokens for subsequent automated audits.

### Usage

```bash
normanjr login <URL> [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--save-storage-state`, `-s` | str | `storage-state.json` | Path where authenticated session tokens are stored. |
| `--config`, `-c` | str | `None` | Path to custom configuration TOML. |

### Example

```bash
normanjr login https://app.example.com/login -s app-auth.json
normanjr audit https://app.example.com/dashboard --storage-state app-auth.json
```

---

## normanjr serve

Start a lightweight local web dashboard to browse, filter, and inspect all historical audit runs and view their generated HTML and PDF reports.

### Usage

```bash
normanjr serve [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--port`, `-p` | int | `8000` | Port to listen on. |
| `--runs-dir` | str | `runs` | Directory containing stored audit runs. |

### Example

```bash
normanjr serve --port 8080
```

---

## normanjr report

Regenerate HTML or PDF reports from an existing run's canonical `result.json` without rerunning browser sessions.

### Usage

```bash
normanjr report <RUN_ID> [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--format`, `-f` | str | `all` | Output format: `html`, `pdf`, or `all`. |
| `--runs-dir` | str | `runs` | Base runs directory. |

### Example

```bash
normanjr report run-20260912-120000-abc123 --format pdf
```

---

## normanjr inspect

Inspect the summary, findings count, confidence score, and raw JSON data of a specific run directly in the terminal.

### Usage

```bash
normanjr inspect <RUN_ID> [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--runs-dir` | str | `runs` | Base runs directory. |
| `--json` | Flag | `False` | Print full canonical JSON payload to stdout. |

### Example

```bash
normanjr inspect run-20260912-120000-abc123
```

---

## normanjr ingest

Ingest telemetry dumps from analytics platforms (PostHog, GA4, RUM) to identify user funnels with high drop-off rates and synthesize prioritized audit journeys.

### Usage

```bash
normanjr ingest <TELEMETRY_FILE> [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--save-journeys`, `-s` | str | `None` | Path to export synthesized journeys JSON for use with `normanjr audit`. |

### Example

```bash
normanjr ingest posthog-export.json --save-journeys priority-journeys.json
```

---

## normanjr resume

Resume an interrupted audit run from its durable checkpoint.

### Usage

```bash
normanjr resume <RUN_ID> [OPTIONS]
```

### Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--runs-dir` | str | `runs` | Base runs directory. |
| `--headed` | Flag | `False` | Resume browser in visible headed mode. |
| `--config`, `-c` | str | `None` | Path to configuration TOML. |

### Example

```bash
normanjr resume run-20260912-120000-abc123
```

---

## normanjr version

Display the current installed version of NormanJr.

```bash
normanjr version
```

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
