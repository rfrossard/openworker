# Secure Browser Operator Learning Log

Append entries only when observed evidence changes an assumption, rule, test, architecture, or priority. Keep entries concise and do not include credentials, cookies, private page content, or sensitive screenshots.

## Entry format

### YYYY-MM-DD — Short finding

- Evidence:
- Impact:
- Decision:
- Roadmap or validation change:
- Related commit/tag:

## Findings

### 2026-07-30 — Approval and preview paths need one redaction boundary

- Evidence: audit storage redacted `browser_type.text`, but the live tool event,
  parked approval payload, Inbox body, and post-fill screenshot were separate paths
  that could still carry the raw value.
- Impact: protecting only the audit database did not satisfy the operator privacy
  contract for passwords, tokens, and other sensitive input.
- Decision: redact display/persistence arguments before emitting or parking them,
  retain raw arguments only for execution, and persistently mask recognized sensitive
  fields in browser preview screenshots.
- Roadmap or validation change: M1.2 adds typed-input redaction, screenshot masking,
  and changed-input rejection; the validation matrix now covers every exposure path.
- Related commit/tag: `local-v0.1.7.55`.

### 2026-07-30 — Approval previously described a selector, not a stable element

- Evidence: `browser_click` resolved a selector only after approval and intentionally selected the first match.
- Impact: a changed or ambiguous page could activate an element the user never reviewed.
- Decision: freeze a unique element fingerprint and bounding box when approval is raised, then resolve and compare it immediately before execution.
- Roadmap or validation change: M1.1 starts with click actions; ambiguous and stale targets fail closed.
- Related commit/tag: `5cfa673` / `local-v0.1.7.54`.

### 2026-07-30 — Visibility must precede greater autonomy

- Evidence: the embedded preview made browser activity understandable, but users still cannot inspect the exact target and consequence before an interaction.
- Impact: adding more autonomous actions first would make failures harder to trust and diagnose.
- Decision: implement Action Inspector before Reliable Actions or persistent authenticated profiles.
- Roadmap or validation change: M1 requires a target overlay, stale-target invalidation, risk explanation, and audit evidence.
- Related commit/tag: planning baseline after `local-v0.1.7.53`.
