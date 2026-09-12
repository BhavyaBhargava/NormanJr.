<p align="center">
  <img src="logo.jpg" alt="NormanJr." width="650" style="max-width: 100%; height: auto;" />
</p>

> **Autonomous, evidence-based UX auditing for web applications.**  
> Bridging the gap between functional code and exceptional usability through empirical measurements, cognitive design heuristics, and autonomous exploration.

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12%2B-blue.svg?logo=python&logoColor=white" alt="Python Version" /></a>
  <a href="https://www.w3.org/WAI/standards-guidelines/wcag/"><img src="https://img.shields.io/badge/Standard-WCAG%202.2%20A%2FAA-blueviolet.svg" alt="Accessibility Standard" /></a>
  <a href="https://github.com/dequelabs/axe-core"><img src="https://img.shields.io/badge/Engine-axe--core-red.svg" alt="A11y Engine" /></a>
  <a href="https://web.dev/explore/learn-core-web-vitals"><img src="https://img.shields.io/badge/Performance-Core%20Web%20Vitals-orange.svg" alt="Web Vitals" /></a>
  <a href="https://openrouter.ai/"><img src="https://img.shields.io/badge/AI%20Reasoning-OpenRouter-black.svg" alt="AI Reasoning" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" /></a>
  <a href="docs/assets/sample-report.pdf"><img src="https://img.shields.io/badge/Sample%20Report-PDF-red.svg?logo=adobeacrobatreader&logoColor=white" alt="Sample Report" /></a>
</p>

---

> *"Good design is actually a lot harder to notice than poor design, in part because good designs fit our needs so well that the design is invisible."*  
> — **Don Norman**, *The Design of Everyday Things*

---

## Table of Contents

- [Overview](#overview)
- [The Core Philosophy](#the-core-philosophy)
- [Core Architecture](#core-architecture)
- [Key Capabilities](#key-capabilities)
- [Sample Audit Report](#sample-audit-report)
- [Documentation](#documentation)
- [License and Acknowledgments](#license-and-acknowledgments)

---

## Overview

A web application can have bulletproof backend architecture, flawless databases, and sophisticated business logic, yet still fail completely in the market because it is simply not **usable**. 

When interfaces suffer from confusing navigation hierarchies, unlabelled controls, sluggish interaction latency, poor visual affordances, or accessibility barriers, real users become frustrated and abandon the site. Countless websites that are functionally sound under the hood end up struggling to gain popularity or retain users because the actual human experience of using them was never properly validated.

Historically, bridging this gap required one of two extremes:
1. **Expensive and Slow Manual Audits**: Hiring specialized UX and accessibility consultancies, which often takes weeks of manual review, costs thousands of dollars per audit, and cannot scale to modern continuous deployment cycles.
2. **Superficial Automated Linting**: Relying on basic static checkers that only inspect raw HTML syntax without understanding dynamic user journeys, visual layout shifts, cognitive friction, or how real humans navigate interfaces.

**NormanJr. was created to bridge this exact gap.**

Named in honor of **Don Norman**—cognitive scientist, author of *The Design of Everyday Things*, and pioneer of user-centered design—NormanJr. provides teams with an autonomous, evidence-first auditing system. It explores web applications just like a human user would: navigating journeys, assessing touch and visual ergonomics, verifying accessibility standards (WCAG 2.2 A/AA), measuring real-world Google Core Web Vitals, and applying multimodal AI reasoning against established cognitive heuristics.

The result is a fast, reproducible, and objective audit that delivers transparent scores, detailed visual evidence, and drop-in code fixes without the traditional cost, delay, or human bias of manual agency reviews.

---

## The Core Philosophy

NormanJr. is built on four core principles:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NORMANJR CORE PILLARS                             │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ Evidence Over Opinion│ Deterministic checks │ Objective measurements (DOM   │
│                      │ precede AI judgment  │ target sizes, contrast, axe,  │
│                      │                      │ Core Web Vitals) come first.  │
├──────────────────────┼──────────────────────┼───────────────────────────────┤
│ Grounded Heuristics  │ Cognitive psychology │ Evaluates Don Norman's laws,  │
│                      │ & usability canons   │ Nielsen's 10 heuristics,      │
│                      │                      │ Fitts's law, & Hick's law.    │
├──────────────────────┼──────────────────────┼───────────────────────────────┤
│ Zero-Trust Security  │ Untrusted pages &    │ Deterministic ActionPolicy &  │
│                      │ hostile input        │ UrlPolicy gateway prevent     │
│                      │                      │ SSRF, mutations, & injection. │
├──────────────────────┼──────────────────────┼───────────────────────────────┤
│ Explainable Scoring  │ Fixed versioned      │ The AI never invents scores.  │
│                      │ penalty calculus     │ Deduplicated root causes feed │
│                      │                      │ a transparent 0-100 UX Index. │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
```

1. **Evidence First, Judgment Second**: An automated tool should never guess button dimensions, contrast ratios, or load latencies when the browser engine can measure them with precision. NormanJr. captures computed bounding boxes, accessibility trees, timing metrics, and automated rules before applying AI reasoning.
2. **Stateful Journey Exploration**: Real users navigate dynamic, multi-step flows. NormanJr. uses an autonomous state machine to explore user journeys, fill forms with safe synthetic data, handle interactive modals, and test responsive states.
3. **No Hallucinated Scores**: The system never invents an arbitrary rating. Scores are calculated deterministically from an open, versioned rubric where verified issues apply fixed mathematical deductions grouped by root cause.
4. **Zero-Trust Safety & Isolation**: Web content is treated as untrusted data. A deterministic policy gateway intercepts every proposed action, preventing SSRF, external redirections, destructive actions, and unauthorized form submissions.

---

## Core Architecture

The following flowchart illustrates how NormanJr. moves from initial target input through autonomous exploration, deterministic verification, heuristic evaluation, and final reporting:

```mermaid
flowchart TD
    %% Input Layer
    START(["Start Audit"]):::terminal
    INPUT[/"Target URL, Journey Goals & Viewport Profile"/]:::input
    
    START --> INPUT
    
    %% Security & Initialization
    subgraph S1 ["1. Security & Preflight Gateway"]
        URL_CHECK{"Validate URL against<br/>SSRF & Origin Policy"}:::decision
        ENV_CHECK["Initialize Isolated Browser Session<br/>& Load Versioned Scoring Rubric"]:::process
    end
    
    INPUT --> URL_CHECK
    URL_CHECK -->|Violates Policy| BLOCK(["Halt: Target Blocked"]):::error
    URL_CHECK -->|Safe URL| ENV_CHECK

    %% Autonomous Exploration Loop
    subgraph S2 ["2. Autonomous Perception & Verification Loop"]
        NAV["Navigate & Settle Page State"]:::process
        PERCEIVE["Perceive DOM, Accessibility Tree,<br/>Screenshots & Console Logs"]:::process
        
        DET_AUDIT["Run Deterministic Measurements:<br/>• Touch Target Sizes (WCAG 2.5.8)<br/>• Programmatic Form Labels (WCAG 3.3.2)<br/>• Heading Hierarchy & Image Alt Text<br/>• Core Web Vitals (LCP, CLS, INP, TTFB)<br/>• Automated axe-core Rule Engine<br/>• Internationalization & Text Clipping"]:::process
        
        BUDGET{"Goal Satisfied or<br/>Budget Exhausted?"}:::decision
        
        PLAN["Formulate Next Action Proposal<br/>(Click, Type, Scroll, or Finish)"]:::process
        
        ACTION_GATE{"Action Policy Gate:<br/>Safe & Non-Destructive?"}:::decision
        
        EXEC["Dispatch Action in Isolated Browser"]:::process
        EVAL["Evaluate Visual & Cognitive UX:<br/>• Norman's Affordances & Feedback<br/>• Nielsen's 10 Usability Heuristics<br/>• Fitts's Law & Hick's Cognitive Load"]:::process
    end

    ENV_CHECK --> NAV
    NAV --> PERCEIVE
    PERCEIVE --> DET_AUDIT
    DET_AUDIT --> BUDGET
    
    BUDGET -->|In Progress| PLAN
    PLAN --> ACTION_GATE
    ACTION_GATE -->|Disallowed / Unsafe| WRAPUP
    ACTION_GATE -->|Approved| EXEC
    EXEC --> EVAL
    EVAL --> NAV

    %% Scoring & Synthesis
    subgraph S3 ["3. Synthesis & Deterministic Scoring Engine"]
        BUDGET -->|Journey Finished| WRAPUP["Finalize Journey & Check Remaining Goals"]:::process
        WRAPUP --> DEDUP["Root-Cause Deduplication<br/>(Group recurring defects by root key)"]:::process
        SCORE["Calculate UX Index (0–100):<br/>Apply Fixed Penalties across 9 Weighted Categories"]:::process
    end

    DEDUP --> SCORE

    %% Reporting & Artifact Output
    subgraph S4 ["4. Enterprise Artifacts & Remediation"]
        HTML["Interactive HTML Report<br/>(report.html)"]:::artifact
        PDF["Print-Ready Executive PDF<br/>(report.pdf)"]:::artifact
        JSON["Canonical Machine Data<br/>(result.json)"]:::artifact
        PATCH["Auto-Remediation Patches<br/>(CSS, HTML, ARIA fixes)"]:::artifact
    end

    SCORE --> HTML
    SCORE --> PDF
    SCORE --> JSON
    SCORE --> PATCH

    END_NODE(["Audit Completed"]):::terminal
    HTML --> END_NODE
    PDF --> END_NODE
    JSON --> END_NODE
    PATCH --> END_NODE

    %% Styling classes
    classDef terminal fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef input fill:#1e293b,stroke:#818cf8,stroke-width:1.5px,color:#f8fafc;
    classDef process fill:#1e293b,stroke:#64748b,stroke-width:1px,color:#f8fafc;
    classDef decision fill:#312e81,stroke:#a5b4fc,stroke-width:1.5px,color:#f8fafc;
    classDef artifact fill:#064e3b,stroke:#34d399,stroke-width:1.5px,color:#f8fafc;
    classDef error fill:#7f1d1d,stroke:#f87171,stroke-width:1.5px,color:#f8fafc;
```

---

## Key Capabilities

- **Autonomous Multi-Journey Exploration**: Evaluates end-to-end user journeys, wizards, and interactive forms with safe synthetic data while automatically halting before final irreversible submissions.
- **Empirical Accessibility Auditing**: Evaluates WCAG 2.2 A/AA standards including 24×24px touch targets, programmatic form labels, heading hierarchies, keyboard traps, and embedded axe-core checks.
- **Cognitive & Usability Heuristics**: Evaluates interfaces against Don Norman's principles (affordances, signifiers, constraints, feedback), Jakob Nielsen's 10 heuristics, and psychometric UX laws (Fitts's Law, Hick's Law).
- **Real-Time Core Web Vitals**: In-browser extraction of Largest Contentful Paint (LCP), Cumulative Layout Shift (CLS), interaction latency (INP), and mobile abandonment thresholds.
- **Zero-Trust Security**: Hardened SSRF defense blocking loopback and private subnets, strict gates against destructive actions (deletions, checkouts), and defenses against indirect prompt injection.
- **Deterministic UX Index (0–100)**: Transparent scoring across 9 weighted categories with root-cause deduplication to prevent repeated-penalty distortion.
- **Automatic Remediation Patches**: Generates ready-to-apply CSS, HTML, and ARIA fixes for detected accessibility and touch-target violations.
- **Regression Diffing for CI/CD**: Compare baseline vs. pull request audit runs to prevent UX regressions from reaching production.

---

## Sample Audit Report

Want to see what an actual audit output looks like? Explore the real 2-page sample audit report generated directly by NormanJr., featuring executive UX Index scores, Core Web Vitals breakdowns, WCAG 2.2 touch target measurements, and prioritized remediation recommendations:

<p align="center">
  <a href="docs/assets/sample-report.pdf">
    <img src="https://img.shields.io/badge/View_Sample_Report-PDF_Viewer-0284c7?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="View Sample Report in PDF Viewer" height="38" />
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <a href="docs/assets/sample-report.pdf?raw=true">
    <img src="https://img.shields.io/badge/Download_Sample-sample--report.pdf-059669?style=for-the-badge&logo=pdf&logoColor=white" alt="Download Sample report.pdf" height="38" />
  </a>
</p>

> **Report Highlights**: Includes overall UX Index score, category breakdowns across all 9 usability dimensions, measured Google Core Web Vitals (LCP, CLS, INP), detected accessibility defects with exact DOM selectors, and prioritized engineering recommendations.

---

## Documentation

Comprehensive guides and detailed references are organized in the [`docs/`](docs/) directory:

- **[Quickstart Guide](docs/quickstart.md)**: System prerequisites, installation steps, environment setup, and running your first audit.
- **[CLI Reference](docs/cli-reference.md)**: Complete command-line syntax, flags, and options for all NormanJr. commands (`audit`, `doctor`, `models`, `compare`, `patch`, `login`, `serve`, `report`, `inspect`, `ingest`, `resume`).
- **[Configuration Guide](docs/configuration.md)**: Breakdown of configuration files (`config/default.toml`), environment variables, model selection, exploration budgets, and browser profiles.
- **[UX Rubric & Scoring Guide](docs/rubric-and-scoring.md)**: Deep dive into the 9 UX categories, fixed severity deductions, root-cause deduplication, and confidence calculations.
- **[Key Features Deep-Dive](docs/features.md)**: Complete breakdown of heuristic evaluation, accessibility checks, Core Web Vitals, and team dashboards.
- **[CI/CD Integration Guide](docs/cicd-integration.md)**: Ready-to-use GitHub Actions workflow, quality threshold assertions, and pull request gating.
- **[Safety Boundaries & Qualified Claims](docs/safety-and-claims.md)**: Security architecture, SSRF prevention, action policies, and ethical/legal audit boundaries.
- **[Development & Testing Guide](docs/development.md)**: Running test suites (unit, contract, integration, e2e), code style standards, and adding custom rubric criteria.

---

## License and Acknowledgments

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

### Acknowledgments

- **Don Norman** — for pioneering user-centered design, cognitive engineering, and the principles of everyday things.
- **Jakob Nielsen** — for establishing the foundational 10 Usability Heuristics.
- **Deque Systems** — for developing the world-class `axe-core` accessibility engine.
- **OpenRouter** — for high-performance multimodal AI model access.

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
