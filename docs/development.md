# Development & Testing Guide

This guide covers contributing to NormanJr., running the test suites, and extending its auditing heuristics.

---

## Local Development Setup

Clone the repository and install development dependencies:

```bash
git clone https://github.com/normanjr/normanjr.git
cd normanjr

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package with development dependencies
pip install -e ".[dev]"

# Install browser automation runner and axe-core
npm install
npx playwright install chromium
```

---

## Running Test Suites

NormanJr. maintains a test suite organized into distinct testing tiers:

```bash
# Run all tests
pytest

# Run unit tests only (fast in-memory checks)
pytest tests/unit

# Run contract tests (deterministic DOM scripts and browser adapter)
pytest tests/contract

# Run integration tests (workflow state machine across pages)
pytest tests/integration

# Run end-to-end tests against local fixture sites
pytest tests/e2e

# Run tests with test coverage reporting
pytest --cov=normanjr tests/
```

---

## Code Quality and Linting

We enforce strict formatting and static typing standards:

```bash
# Check code style with Ruff
ruff check src tests

# Format code with Ruff
ruff format src tests

# Static type checking with mypy
mypy src
```

---

## Extending Auditing Rules

### Adding Deterministic DOM Checks

To add a new deterministic measurement (e.g. checking for missing landmarks or meta tags):

1. Define a read-only, side-effect-free JavaScript extraction script in `src/normanjr/audit/metrics.py`.
2. Register the check in `src/normanjr/audit/deterministic.py`.
3. Map the finding to a registered criterion ID in the rubric.
4. Add a unit test verifying the script extracts the correct values from a mock HTML fixture.

### Customizing Scoring Rubrics

Rubrics are defined in YAML under `config/rubrics/`:

```yaml
schema_version: "1.0"
rubric_id: "custom-ux"
rubric_version: "1.0.0"

categories:
  - id: task_completion
    label: "Task Flow"
    weight: 0.30
  - id: accessibility_operability
    label: "Accessibility"
    weight: 0.25

severity_penalties:
  critical: 15
  major: 8
  minor: 3
  observation: 0

criteria:
  - id: CUSTOM-NAV-CLARITY
    category_id: task_completion
    title: "Primary navigation clarity"
    authority: "Internal Design System"
    default_severity: major
    allowed_severities: [minor, major]
    scope: component
    scoring_eligible: true
```

Specify your custom rubric at runtime:

```bash
normanjr audit https://example.com --config config/my-rubric.toml
```

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
