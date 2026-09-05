# Security Policy — NormanJr.

## Core Security Posture

NormanJr. is an autonomous UX auditing assistant. Because autonomous browsers interact with untrusted websites and execute model-directed actions, NormanJr. adheres to a strict least-privilege security architecture:

1. **Target Content as Untrusted Data:** All DOM text, accessible names, images, console logs, network responses, and URLs from target sites are treated as hostile, untrusted data.
2. **Deterministic Policy Gateway:** LLMs never select arbitrary tools, execute arbitrary code, or access local files. Every proposed action passes through a deterministic `ActionPolicy` gateway before any browser execution.
3. **SSRF & Network Boundary:** Navigation to loopback (`127.0.0.1`, `::1`), private RFC1918 networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local, multicast, and cloud metadata IP ranges (`169.254.169.254`) is blocked by default. A local test flag is required for fixture testing.
4. **Action Risk Classification:**
   - **Safe/Low Risk:** Reading DOM snapshots, screenshots, scrolling, local hovering.
   - **Medium Risk:** Typing synthetic persona data into non-sensitive fields, local non-destructive clicks.
   - **High Risk / Blocked by Default:** Final form submissions, file uploads/downloads, external redirects, payments, account deletions, data modifications.
5. **Secret Redaction:** API keys, authorization tokens, cookies, passwords, and sensitive persona inputs are stripped from logs and reports.

## Reporting a Vulnerability

If you discover a security vulnerability in NormanJr., please report it responsibly by contacting the maintainers. Do not disclose vulnerabilities in public issue trackers.
