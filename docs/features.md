# Key Features & Capabilities

NormanJr. brings together automated measurement, cognitive design psychology, and multimodal reasoning into a unified auditing system.

---

## 1. Autonomous Multi-Journey Exploration

- **Goal-Directed Journeys**: Supply specific user tasks (e.g., *"Search for a winter jacket, view item details, and proceed to checkout"*) or allow NormanJr. to automatically synthesize realistic test journeys based on landing page affordances.
- **Multi-Step Form Traversal**: Discovers and navigates multi-step wizards using synthetic persona data while strictly halting before final submission.
- **Responsive Viewport Profiles**: Test desktop (`1280x800`) and mobile (`390x844`) layouts sequentially or in dual-phase runs (`--profile both`).
- **Resumable State**: Audit sessions maintain durable SQLite checkpoints, enabling interrupted runs to resume without starting over (`normanjr resume <run_id>`).

---

## 2. Multi-Disciplinary UX Heuristics

NormanJr. evaluates user interfaces against established canons of cognitive engineering and human-computer interaction:

### Don Norman's Principles of Everyday Things
- **Affordances & Signifiers**: Differentiating interactive controls from passive background elements; ensuring icons have clear textual labels.
- **Feedback & Status**: Ensuring immediate acknowledgment of user input (spinners, disabled submit buttons, confirmation banners).
- **Constraints**: Preventing input errors before submission through smart masking and format hints.
- **Conceptual Models & Mapping**: Aligning UI control layouts with intuitive spatial and mental models.

### Jakob Nielsen's 10 Usability Heuristics
- Visibility of system status, match between system and real world, user control & freedom, consistency & standards, error prevention, recognition over recall, flexibility & efficiency, aesthetic minimalism, error recovery, and help documentation.

### Psychometric UX Laws
- **Fitts's Law**: Analyzing interactive target dimensions and travel distance for touch and mouse ergonomics.
- **Hick's Law**: Evaluating choice density, menu complexity, and cognitive load in primary workflows.

### WCAG 2.2 A/AA Conformance
- Minimum Target Size (SC 2.5.8: 24×24px minimum bounding box).
- Programmatic Form Labelling (SC 3.3.2: matching `for`/`id` labels and ARIA attributes).
- Accessible Names (SC 4.1.2: buttons and links have distinct accessible names).
- Sequential Heading Structure (validating sequential `<h1>` through `<h6>` hierarchy).
- Image Alternatives (SC 1.1.1: detecting missing or empty `alt` attributes on meaningful images).
- Keyboard Navigation and Focus Rings (SC 2.1.1, SC 2.4.7).
- In-browser execution of **axe-core** automated audit rules.

### Multilingual & Internationalization (i18n)
- Identifies missing root `<html lang>` declarations.
- Detects untranslated developer tokens and template placeholders (e.g. `{{ label_key }}`).
- Flags text expansion clipping where translated strings overflow fixed-dimension containers.

---

## 3. Real-Time Core Web Vitals & Performance

Performance directly impacts user retention. NormanJr. extracts in-browser performance metrics during audits:

- **Largest Contentful Paint (LCP)**:
  - `< 2.5s`: Good (Pass)
  - `2.5s – 4.0s`: Needs Improvement (Major penalty)
  - `> 4.0s`: Poor (Critical penalty & high bounce risk)
- **Cumulative Layout Shift (CLS)**:
  - Detects visual layout shifts exceeding `0.1` that trigger accidental misclicks.
- **Interaction to Next Paint (INP)**:
  - Validates interaction latency remains under `200ms`.
- **3-Second Mobile Abandonment Threshold**:
  - Flags total page load times exceeding 3 seconds on mobile profiles.

---

## 4. Multi-Format Reporting & Evidence Artifacts

Every completed run produces a full artifact bundle in `runs/<run-id>/`:

- **Interactive HTML Report (`report.html`)**: Self-contained single-file report with embedded CSS, category score meters, expandable finding cards, and inline screenshot evidence.
- **Executive PDF Report (`report.pdf`)**: Print-ready, professionally formatted PDF summary. See the [Sample PDF Report](../report.pdf) or [download raw](../report.pdf?raw=true).
- **Canonical Machine-Readable Data (`result.json`)**: Complete typed JSON record for integration with CI/CD quality gates.
- **Visual & Structural Evidence**: Full-resolution screenshots, accessibility trees, console log dumps, and event timelines.

---

## 5. Automated Remediation Code Patches

Fixing usability defects is streamlined with automatic patch generation:

```bash
normanjr patch <run_id> --output fixes.patch
```

NormanJr. inspects detected findings and generates drop-in code snippets:
- **CSS Patches**: Adds minimum width, height, and padding for touch target violations (WCAG 2.5.8).
- **HTML Patches**: Generates programmatic `<label>` associations for orphan form inputs (WCAG 3.3.2).
- **ARIA Patches**: Generates accessible names, roles, and alternative text.

---

## 6. Regression Comparison & CI/CD Diffing

Track design health across software releases:

```bash
normanjr compare baseline-run current-run --output regression.md
```

Detects:
- Overall UX Index score movement.
- Category-by-category score deltas.
- Resolved flaws that were fixed since the baseline.
- New regression violations introduced in the current build.

---

## 7. Real-User Telemetry Ingestion

Prioritize audits on user journeys where visitors are dropping off:

```bash
normanjr ingest posthog-analytics.json --save-journeys prioritized-journeys.json
```

Analyzes user funnel drop-offs from PostHog or Google Analytics 4 and automatically generates prioritized audit journeys for NormanJr. to explore.

---

## 8. Organization UX Intelligence Dashboard

Host a central observability dashboard for engineering and design teams:

```bash
normanjr serve --port 8000
```

Indexes all historical runs in the `runs/` directory, displaying score trajectories, category distributions, and direct links to HTML and PDF reports.

---

## 9. Interactive Authentication Session Recording

For applications behind authentication walls:

```bash
normanjr login https://app.example.com/login --save-storage-state auth.json
normanjr audit https://app.example.com/dashboard --storage-state auth.json
```

Opens a visible browser session allowing you to log in manually (including completing MFA or SSO). Session cookies and storage state are saved to inspect authenticated pages autonomously.

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
