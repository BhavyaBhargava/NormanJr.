# Configuration Guide

NormanJr. is designed to be fully configurable through configuration files, environment variables, and CLI flags.

---

## Configuration Hierarchy

Configuration settings are resolved using a cascading priority order:

1. **CLI Flags**: Arguments supplied directly at the command line take top priority (e.g., `--profile mobile`, `--max-steps 15`).
2. **Environment Variables**: Variables defined in your active shell or in `.env` (e.g., `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`).
3. **Custom TOML Config**: Config files passed via the `--config` / `-c` flag.
4. **Default Configuration**: Values defined in `config/default.toml`.

---

## Environment Variables

The following environment variables can be set in a `.env` file at the root of your project:

| Variable | Type | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | string | `""` | API key used for multimodal visual evaluation and journey planning. |
| `OPENROUTER_MODEL` | string | `"google/gemini-2.5-flash"` | Active model ID to request from the model router. |
| `OPENROUTER_HTTP_REFERER` | string | `"https://github.com/normanjr/normanjr"` | Optional attribution URL sent in request headers. |
| `OPENROUTER_TITLE` | string | `"NormanJr UX Auditor"` | Optional application title sent in request headers. |
| `LOG_LEVEL` | string | `"INFO"` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |

---

## TOML Configuration Sections

Below is an annotated breakdown of all configuration sections available in `config/default.toml`.

### Model Settings (`[model]`)

Controls the AI reasoning engine, multimodal expectations, retries, and token budgets:

```toml
[model]
requested_model = "google/gemini-2.5-flash"  # Default model identifier
allow_free_router = true                    # Permit using free-tier endpoints when available
require_vision = false                      # Require model to accept image payloads
require_structured_output = true            # Require schema-enforced structured JSON output
request_timeout_seconds = 60.0              # Timeout per inference call
max_retries = 2                             # Number of retry attempts on transient failure
max_calls = 40                              # Hard cap on LLM queries per audit session
max_input_tokens = 64000                    # Maximum context window input token budget
max_output_tokens = 4096                    # Maximum response token length
max_cost_usd = 2.0                          # Session spending ceiling in USD
```

### Browser Settings (`[browser]`)

Controls browser instantiation, rendering, viewports, and timing:

```toml
[browser]
browser_name = "chromium"     # Browser engine: chromium, firefox, or webkit
headless = true               # Run browser headlessly without visible GUI
isolated = true               # Use a dedicated, incognito browser context
action_timeout_ms = 10000     # Maximum wait time for single interactions (10s)
navigation_timeout_ms = 30000 # Maximum wait time for page navigations (30s)
settle_timeout_ms = 1500      # Wait time after interaction to allow DOM and CSS transitions to settle
output_max_bytes = 52428800   # Artifact buffer ceiling (50 MB)
```

#### Supported Viewport Profiles

NormanJr. includes predefined viewport profiles:

- **`desktop`**: `1280x800` viewport, standard desktop user-agent, `device_scale_factor = 1.0`, mouse pointer emulation.
- **`mobile`**: `390x844` viewport (iPhone 14 / modern smartphone baseline), mobile user-agent, touch emulation enabled, `device_scale_factor = 2.0`.
- **`mobile-safari`**: `390x844` viewport with Safari mobile user-agent string.

### Exploration Settings (`[exploration]`)

Defines traversal budgets, state tracking limits, and navigation boundaries:

```toml
[exploration]
max_journeys = 3                   # Maximum number of goal-directed journeys per session
max_steps_per_journey = 20         # Maximum sequential actions per journey
max_unique_states = 60             # Maximum unique DOM states recorded
max_pages = 25                     # Maximum distinct URL paths visited
max_duration_seconds = 1800        # Session wall-clock ceiling (30 minutes)
max_repeated_state_visits = 3      # Loop detection threshold for repeated page states
same_origin_only = true            # Constrain traversal strictly to initial domain
allowed_origins = []               # Explicit whitelist of secondary domains (e.g. auth providers)
denied_url_patterns = []           # Glob/regex patterns to avoid (e.g. *logout*, *delete*)
```

### Safety and Security Settings (`[safety]`)

Enforces zero-trust defense mechanisms and prevents unintended side effects:

```toml
[safety]
allow_final_submit = false         # Block clicking buttons that complete irreversible form submissions
allow_download = false             # Disallow file downloads
allow_upload = false               # Disallow file uploads from the host filesystem
allow_external_navigation = false  # Block navigation outside verified origins
allow_authentication = false       # Block automated credential entry unless explicitly enabled
allow_destructive_actions = false  # Strictly block actions matching destructive patterns
stop_on_captcha = true             # Immediately halt exploration upon encountering bot challenges
redact_form_values = true          # Mask typed values and secrets in logs and reports
allow_private_target = false       # Block navigation to localhost / private RFC1918 networks (SSRF defense)
```

### Reporting Settings (`[report]`)

Configures artifact retention and report detail:

```toml
[report]
output_directory = "runs"          # Output directory for audit runs
include_full_snapshots = false     # Include raw DOM trees in summary reports
include_console_errors = true      # Include browser console log entries
include_network_urls = true        # Log failed HTTP request URLs
screenshot_quality = 85            # JPEG/PNG compression quality (1-100)
retain_days = 30                   # Days before local artifact pruning
```

### Scoring Settings (`[scoring]`)

Directs the deterministic scoring engine:

```toml
[scoring]
rubric_path = "config/rubrics/ux-rubric-v1.yaml" # Path to versioned scoring rubric
rubric_version = "1.1.0"                        # Active rubric version string
score_probable_findings = false                 # Only deduct points for confirmed findings
```

---

## Using Custom Config Files

You can create project-specific configuration profiles (e.g., `ci.toml`, `mobile.toml`) and supply them at runtime:

```bash
normanjr audit https://example.com --config config/ci.toml
```

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
