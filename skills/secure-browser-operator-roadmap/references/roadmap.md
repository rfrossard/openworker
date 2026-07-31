# Secure Browser Operator Roadmap

Last reviewed: 2026-07-30

## Product objective

Let OpenWorker agents complete browser tasks transparently and reliably while the user retains control over credentials, consequential actions, data movement, and recovery.

## Current baseline

- Isolated Chromium sessions run inside OpenWorker.
- The right rail shows a live preview with configurable refresh timing.
- Agents can navigate public pages with session-level permission.
- Page media detection and authorized downloads are available.
- Browser events and artifact operations participate in local usage accounting.
- The remaining gap is dependable, visible interaction with page elements and proof that each action produced its expected result.

## Milestones

### M1 — Action Inspector

Status: `ready`

Goal: show what the agent intends to interact with before execution.

Scope:

- Represent click, type, select, scroll, download, and upload proposals.
- Highlight the target in the preview using a numbered overlay.
- Show action, target label, domain, risk, expected result, and approval requirement.
- Allow approve once, deny, and cancel task.
- Re-resolve the target immediately before execution and reject stale proposals.

Acceptance:

- The overlay and action card refer to the same stable target.
- Denial or cancellation causes no browser-side mutation.
- A changed page invalidates the proposal instead of clicking a different element.
- Every proposal and decision appears in the session audit trail.
- Keyboard navigation and screen-reader labels work.

Non-goals: persistent login profiles, multi-step replay, autonomous recovery.

Next smallest action: document the existing browser action protocol and add a failing test for a stale click target.

### M2 — Reliable Actions

Status: `discovery`
Prerequisite: M1 `validated`

Goal: execute common interactions and verify outcomes.

Scope: click, fill, select, scroll, file download/upload, navigation waits, outcome assertions, idempotency keys.

Exit signal: success is based on observed state change, not only a successful automation command.

### M3 — Risk & Permission Engine

Status: `discovery`
Prerequisite: M2 `validated`

Goal: classify actions consistently and request the least disruptive safe approval.

Scope: domain policies, action classes, session grants, per-action approvals, expiry, permission explanations, default deny for consequential actions.

### M4 — Secure Persistent Profiles

Status: `discovery`
Prerequisite: M3 `validated`

Goal: preserve authenticated sessions in isolated, encrypted, user-controlled profiles.

Scope: profile per site/account, cookie and storage isolation, lock/unlock, expiry, clear profile, no credential exposure to model context.

### M5 — Replay & Recovery

Status: `discovery`
Prerequisite: M2 and M4 `validated`

Goal: recover safely from layout changes, transient failures, interruptions, and restarts.

Scope: action journal, checkpoints, target re-location, bounded retry, resume, screenshot comparison, explicit stop conditions.

### M6 — Teach & Automate

Status: `discovery`
Prerequisite: M5 `validated`

Goal: convert a demonstrated browser workflow into an editable, reusable skill.

Scope: demonstration capture, parameter extraction, secret redaction, approval boundaries, generated tests, dry run, versioning.

### M7 — Multi-Agent Browser Work

Status: `deferred`
Prerequisite: M5 `validated`

Goal: let agents research, verify, and synthesize using separate isolated contexts and shared non-secret evidence.

Reason deferred: reliable single-agent execution and recovery must be proven first.

## Roadmap adjustment rules

- Promote a milestone to `ready` only with testable scope and acceptance criteria.
- Split work when a milestone needs more than one independently useful release.
- Reorder only when evidence changes risk, dependency, or user value; record the reason in the learning log.
- Never hide an unresolved safety or reliability issue by lowering an acceptance criterion.
