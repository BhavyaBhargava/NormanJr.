# CI/CD Integration Guide

Automating UX quality gates in your continuous integration and deployment pipelines ensures design standards, accessibility compliance, and performance metrics are guarded just as strictly as unit tests.

---

## Why Automate UX Auditing in CI/CD?

Teams frequently run automated functional tests, yet UX and accessibility regressions often slip into production unnoticed:

- A CSS change inadvertently reduces a button's touch target below the 24×24px minimum.
- A new form input is merged without an associated `<label>`.
- An unoptimized hero asset inflates Largest Contentful Paint (LCP) past 4 seconds.
- A modal introduces an inadvertent keyboard trap.

With NormanJr. integrated into your pull request pipeline, regressions are detected and flagged immediately with actionable remediation patches before reaching production users.

---

## GitHub Actions Workflow

Below is a complete, production-ready GitHub Actions workflow (`.github/workflows/ux-audit.yml`):

```yaml
name: NormanJr UX Quality Gate

on:
  pull_request:
    branches: [main, master]
  workflow_dispatch:

jobs:
  ux-audit:
    name: Autonomous UX Audit & Regression Check
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install Dependencies
        run: |
          pip install -e .
          npm install
          npx playwright install --with-deps chromium

      - name: Verify Environment Toolchain
        run: normanjr doctor

      - name: Start Application Preview Server
        run: |
          npm run build
          npm run preview -- --port 4173 &
          # Wait for preview server to respond
          timeout 30 bash -c 'until curl -s http://127.0.0.1:4173 > /dev/null; do sleep 1; done'

      - name: Execute Autonomous UX Audit
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: |
          normanjr audit http://127.0.0.1:4173 \
            --allow-private-target \
            --profile desktop \
            --output pr-audit-run \
            --json > audit-summary.json

      - name: Enforce UX Quality Thresholds
        run: |
          python3 - << 'EOF'
          import json, sys

          with open('pr-audit-run/result.json') as f:
              data = json.load(f)

          score = data.get('score', {}).get('overall_score', 0.0)
          findings = data.get('findings', [])
          critical_count = sum(1 for item in findings if item.get('severity') == 'critical')

          print(f"========================================")
          print(f"Overall UX Index: {score}/100")
          print(f"Critical Findings: {critical_count}")
          print(f"Total Confirmed Issues: {len(findings)}")
          print(f"========================================")

          MIN_SCORE = 80.0
          failed = False

          if score < MIN_SCORE:
              print(f"FAIL: UX Index ({score}) is below minimum threshold ({MIN_SCORE}).")
              failed = True

          if critical_count > 0:
              print(f"FAIL: Build contains {critical_count} critical UX/accessibility violation(s).")
              failed = True

          if failed:
              sys.exit(1)

          print("PASS: All UX quality gate criteria met.")
          EOF

      - name: Generate Remediation Patches
        if: failure()
        run: |
          normanjr patch pr-audit-run --output pr-fixes.patch
          echo "Generated auto-remediation patches:"
          cat pr-fixes.patch

      - name: Upload Audit Reports & Artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: normanjr-ux-report
          path: |
            pr-audit-run/report.html
            pr-audit-run/report.pdf
            pr-audit-run/result.json
            pr-fixes.patch
```

---

## Comparing PR Runs Against Baseline

To guard against score regressions relative to your main branch, save a baseline run artifact from your `main` branch deployments and compare against it during pull requests:

```bash
# Compare baseline vs. current PR run
normanjr compare baseline-run pr-audit-run --output regression-report.md
```

If score deltas fall below an acceptable threshold (e.g. score drops by more than 2 points), the build can be configured to fail.

---

## Summary of Exit Codes

When scripting in CI environments, NormanJr. returns predictable exit codes:

- `0`: Audit completed successfully without errors.
- `1`: Execution error, broken environment, or toolchain verification failure.
- `2`: Target URL blocked by security policy (e.g., SSRF boundary violation).

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
