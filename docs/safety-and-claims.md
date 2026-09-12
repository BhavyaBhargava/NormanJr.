# Safety Boundaries & Qualified Claims

Operating autonomous agents in browser environments requires strict defensive engineering. This document details NormanJr.'s security posture, action boundaries, and product qualifications.

---

## Security Architecture

NormanJr. follows a zero-trust design philosophy:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ZERO-TRUST SECURITY ARCHITECTURE                     │
├────────────────────────────┬────────────────────────────────────────────┤
│ SSRF Network Boundary      │ Blocks access to loopback, private         │
│                            │ subnets, and cloud metadata endpoints.     │
├────────────────────────────┼────────────────────────────────────────────┤
│ Action Policy Gateway      │ Deterministic inspection intercepts every  │
│                            │ proposed action before browser execution.  │
├────────────────────────────┼────────────────────────────────────────────┤
│ Hostile Input Sanitization │ Page text and OCR elements are treated as  │
│                            │ untrusted data (anti-prompt injection).    │
├────────────────────────────┼────────────────────────────────────────────┤
│ Mutation Safeguards        │ Destructive actions, account deletions,   │
│                            │ and final purchases are strictly blocked.  │
├────────────────────────────┼────────────────────────────────────────────┤
│ Automatic Redaction        │ API keys, tokens, and form input values   │
│                            │ are sanitized from logs and artifacts.     │
└────────────────────────────┴────────────────────────────────────────────┘
```

---

## SSRF Network Boundary

To prevent autonomous agents from being redirected toward internal enterprise infrastructure, NormanJr. strictly blocks access to the following IP networks by default:

- **Loopback**: `127.0.0.0/8`, `::1/128`
- **RFC1918 Private Networks**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- **Cloud Provider Metadata Endpoints**: `169.254.169.254` (AWS, GCP, Azure, DigitalOcean)
- **Link-Local & Multicast**: `169.254.0.0/16`, `224.0.0.0/4`, `fe80::/10`

When auditing local development environments, an explicit `--allow-private-target` flag is required.

---

## Action Policy Gateway

The AI reasoning engine never executes arbitrary scripts or interacts directly with the browser engine. Instead:

1. The model proposes a structured, typed intent (e.g. `ClickElement(ref="e4")`).
2. The proposal is intercepted by the deterministic `ActionPolicy` gateway.
3. The gateway inspects element labels, target selectors, and risk classes.
4. If approved, the action is dispatched using fixed, application-owned executor templates.

### Risk Classifications

- **Low Risk (Permitted)**: Reading DOM state, taking screenshots, scrolling, element inspection.
- **Medium Risk (Permitted with Safeguards)**: Typing synthetic persona data into non-sensitive text fields, navigating safe links, clicking non-destructive buttons.
- **High Risk / Blocked by Default**: Submitting final purchase forms, uploading/downloading local files, entering credit card details, navigating to unapproved external domains.

### Destructive Action Prevention

Actions matching destructive patterns are unconditionally blocked:

- Account deactivation or deletion (`delete`, `terminate`, `deactivate`, `cancel account`)
- Data modification or removal (`remove`, `drop`, `erase`)
- Financial transactions (`buy now`, `place order`, `confirm payment`, `subscribe`)

---

## Anti-Prompt Injection Defenses

Untrusted web pages may embed indirect prompt injection attacks designed to hijack AI agent behavior (e.g. hidden text instructing the agent to navigate elsewhere or ignore rules).

NormanJr. mitigates this risk by:

- Encapsulating all DOM content and page observations inside strict, structural XML data boundaries.
- Explicitly instructing the reasoning model that web content represents passive runtime data rather than executable system instructions.
- Constraining action targets to verified references (`ref`) present in the deterministic accessibility tree.

---

## Qualified Claims and Limitations

NormanJr. is an **automated heuristic and evidence-gathering assistant**, not:

- **A Substitute for Human Testing**: Automated audits cannot replace moderated usability studies with real human users, diverse user groups, or people who rely on assistive technologies daily.
- **A Legal Guarantee of Compliance**: A high score does not constitute legal certification of WCAG 2.2, ADA Title III, Section 508, or EN 301 549 compliance.
- **A Security Penetration Tool**: NormanJr. does not test for web application security vulnerabilities (e.g., XSS, SQLi, CSRF).
- **A Tool to Bypass Protections**: NormanJr. does not bypass CAPTCHAs, bot defenses, or `robots.txt` directives, and must only be executed against systems you own or have explicit authorization to audit.

Every generated report includes a clear summary of audit limitations, stating visited state counts, route coverage, and unassessed categories.

---

<p align="center">
  Built with care for designers, developers, and QA engineers who believe great user experience should be measurable, explainable, and accessible to all.
</p>
