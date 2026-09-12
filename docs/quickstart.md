# Quickstart Guide

This guide walks you through setting up NormanJr. and running your first automated UX audit in under five minutes.

---

## Prerequisites

Before running NormanJr., ensure your environment meets the following requirements:

- **Python 3.12+**
- **Node.js 18+** (with `npm`)
- **Chromium browser binaries** (managed via standard browser installation tools)
- **OpenRouter API Key** (optional for deterministic DOM and accessibility checks; recommended for multimodal visual analysis and autonomous journey planning)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/normanjr/normanjr.git
cd normanjr
```

### 2. Set Up Python Environment

Create and activate an isolated Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install NormanJr. and its core dependencies:

```bash
pip install -e .
```

### 3. Install Browser and Engine Assets

Install the required browser automation runner and accessibility engine:

```bash
npm install
npx playwright install chromium
```

---

## Environment Setup

Create a local `.env` configuration file from the provided template:

```bash
cp .env.example .env
```

Open `.env` and configure your API key and preferred reasoning model:

```dotenv
# OpenRouter API Key
OPENROUTER_API_KEY="your-api-key-here"

# Multimodal model to use for visual assessment and heuristic evaluation
OPENROUTER_MODEL="google/gemini-2.5-flash"

# Optional logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL="INFO"
```

---

## Verify Environment Health

NormanJr. includes a built-in diagnostic tool to verify all runtimes, engine assets, browser binaries, and model connections:

```bash
normanjr doctor --check-model
```

If all checks display green, your system is ready for auditing.

---

## Running Your First Audit

### Basic Audit

To audit a web application using default exploration parameters:

```bash
normanjr audit https://example.com
```

### Guided Audit with Explicit Goals

You can supply specific user tasks for NormanJr. to explore:

```bash
normanjr audit https://ecommerce.store.com \
  --goal "Search for running shoes and filter by size 10" \
  --goal "Add an item to the shopping cart and proceed to checkout"
```

### Mobile Viewport Audit

Evaluate touch usability, small-screen ergonomics, and responsive layout stability:

```bash
normanjr audit https://example.com --profile mobile
```

To run both desktop and mobile evaluations sequentially in a single session:

```bash
normanjr audit https://example.com --profile both
```

### Visible (Headed) Exploration

To watch the browser navigate and interact with the page in real time:

```bash
normanjr audit https://example.com --headed
```

---

## Understanding Audit Output

When an audit completes, NormanJr. prints a summary to your terminal:

```
============================================================
Audit Completed for: https://example.com
Overall UX Index: 88.5/100
Confirmed Findings: 3
HTML Report: file:///path/to/NormanJr/runs/run-20260912-120000-abc123/report.html
PDF Report:  file:///path/to/NormanJr/runs/run-20260912-120000-abc123/report.pdf
============================================================
```

All session artifacts are organized inside the `runs/<run-id>/` directory:

- **`report.html`**: Self-contained interactive report with embedded CSS, category scores, and evidence captures.
- **`report.pdf`**: Print-ready executive PDF summary.
- **`result.json`**: Canonical structured audit data containing metrics, deductions, and findings.
- **`screenshots/`**: High-resolution viewport captures taken at critical steps.
- **`snapshots/`**: Accessibility trees and DOM states.

To view your report in your browser:

```bash
# Linux
xdg-open runs/<run-id>/report.html

# macOS
open runs/<run-id>/report.html
```

---

## Next Steps

- Explore all command-line options in the [CLI Reference](cli-reference.md).
- Learn about configuration parameters in the [Configuration Guide](configuration.md).
- Understand how findings are calculated in the [Rubric & Scoring Guide](rubric-and-scoring.md).
- Set up automated audits in CI/CD using the [CI/CD Integration Guide](cicd-integration.md).

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
