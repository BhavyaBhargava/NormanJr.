# UX Rubric & Scoring Guide

This guide explains how NormanJr. evaluates web experiences, deduplicates issues, and calculates the overall **UX Index (0–100)** without relying on arbitrary model-generated numbers.

---

## Scoring Philosophy

A common weakness of AI-assisted evaluation tools is scoring hallucination—where an LLM invents a subjective rating (such as giving a page "8/10") based on arbitrary impressions.

NormanJr. takes an opposite, mathematically rigorous approach:

1. **Fixed Versioned Penalties**: Every defect is classified by an objective severity level with a fixed mathematical penalty.
2. **Deterministic Precedence**: Measurements that can be calculated by the browser (target dimensions, contrast ratios, axe-core rules, Core Web Vitals) always dictate severity and score penalties.
3. **Root-Cause Deduplication**: Issues occurring across multiple steps or repeated pages (such as an unlabelled navigation icon present on every route) are merged into a single canonical defect.
4. **Transparent Category Weights**: Scores are weighted across nine distinct usability categories representing cognitive design, accessibility, ergonomics, and performance.

---

## The UX Index Formula

The overall UX Index is a weighted average of individual category scores:

$$\text{UX Index} = \frac{\sum_{i=1}^{n} (\text{Category Raw Score}_i \times \text{Category Weight}_i)}{\sum_{i=1}^{n} \text{Category Weight}_i}$$

Where:
- **Category Raw Score** starts at `100.0` and is decremented by the sum of penalties for confirmed findings within that category:
  $$\text{Category Raw Score} = \max(0.0, 100.0 - \sum \text{Finding Penalties})$$
- Only findings with status `CONFIRMED` and `scoring_eligible = True` contribute penalties.

---

## The 9 UX Categories

NormanJr. evaluates web applications across nine categories defined in `config/rubrics/ux-rubric-v1.yaml`:

| Category ID | Category Name | Weight | Primary Standards & Focus |
|---|---|:---:|---|
| `task_completion` | **Task Flow** | **22%** | Unbroken journey progress, clarity of calls to action, dead ends, clear completion states. |
| `accessibility_operability` | **Accessibility** | **18%** | WCAG 2.2 A/AA conformance, axe-core automated audit rules, target size minimums (24×24px), focus states. |
| `feedback_status` | **Status & Feedback** | **12%** | Visibility of system status, progress bars, loading spinners, instant interaction response. |
| `constraints_error_recovery` | **Error Recovery** | **12%** | Form error messaging, input formatting guidance, clear error identification (WCAG 3.3.1). |
| `discoverability_affordance` | **Affordance & Signs** | **10%** | Visual affordances, clickability signifiers, clear icons, unambiguous button states. |
| `performance_stability` | **Speed & Web Vitals** | **10%** | Largest Contentful Paint (LCP), Cumulative Layout Shift (CLS), interaction latency, console errors. |
| `cognitive_load` | **Cognitive Load** | **8%** | Hick's Law, choice density, visual clutter, visual hierarchy, information chunking. |
| `mapping_conceptual_model` | **Mapping & Mental Model** | **5%** | Natural conceptual mappings, consistency with real-world conventions, localization placeholders. |
| `responsive_motor` | **Ergonomics & Mobile** | **3%** | Fitts's Law, touch target distance, thumb-zone reachability, text truncation/clipping. |

---

## Severity Deductions

Each identified issue is assigned a severity rating based on user impact:

| Severity | Penalty | Impact Criteria | Examples |
|---|:---:|---|---|
| **Critical** | **-15** | Prevents core task completion, introduces inaccessible barriers, or severely degrades performance. | Keyboard trap (WCAG 2.1.2), primary CTA missing accessible name (WCAG 4.1.2), LCP > 4.0s (Poor Web Vitals). |
| **Major** | **-8** | Causes significant user frustration, layout instability, or accessibility non-conformance. | Touch targets < 24×24px (WCAG 2.5.8), unlabelled inputs (WCAG 3.3.2), visual shift CLS > 0.1, LCP between 2.5s and 4.0s. |
| **Minor** | **-3** | Suboptimal UX, inconsistency, or secondary structural flaw. | Skipped heading levels (`<h1>` to `<h4>`), missing root `<html lang>`, uncaught console exceptions. |
| **Observation** | **0** | Best-practice recommendations, suggestions, or design praise. | Color palette suggestions, typography contrast enhancements, optional micro-animations. |

---

## Root-Cause Deduplication

If an application displays an undersized 18×18px search icon in a persistent global header, a visitor encounters that defective button on every single page they visit.

In a naive evaluation tool, visiting 10 pages would penalize the site 10 times for the same button (-80 points), ruining the audit's credibility.

NormanJr. groups every finding by a unique `root_cause_key`:

- Target size issues: `target-size:<selector>`
- Form label defects: `form-label:<selector>`
- Missing alt text: `img-alt:<source-hash>`
- Web vitals failures: `cwv-lcp:poor` or `cwv-cls:unstable`
- Heading skips: `heading-skip:h1-to-h4`

Identical defects discovered across multiple steps increment the finding's `occurrences` counter while applying the score penalty **only once**.

---

## Confidence and Coverage Assessment

Every audit report provides explicit coverage statistics:

- **Journeys Planned vs. Completed**: Bounded user paths successfully traversed.
- **Unique States**: Total distinct DOM layouts evaluated.
- **Interactive Elements Tested**: Number of links, buttons, and inputs exercised.
- **Automated Rules Checked**: Total automated accessibility checks executed.

### Confidence Rating

- **High Confidence**: Calculated when 75% or more of scored findings are backed by deterministic DOM measurements and automated engine rules.
- **Medium Confidence**: Generated when visual heuristics represent a greater portion of findings.

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
