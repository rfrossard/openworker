# Secure Browser Operator Learning Log

## 2026-07-30 — A fixed popup can still inherit the side rail's visual boundary

- Evidence: the human-control surface was mounted inside the right rail, so a wide
  popup remained visually associated with the narrow inspector and could extend
  beyond the usable OpenWorker window.
- Impact: the page preview was hidden at the edge and the user could not place the
  browser over the central workspace for side-by-side inspection.
- Decision: render the control surface in the application-level portal, open it
  centered over the main workspace, make its title bar draggable, retain native
  resizing, and clamp it back into view after dragging or window resizing.
- Roadmap or validation change: extend M1.6 with portal, drag, and viewport-clamping
  checks.
- Related commit/tag: planned for `local-v0.1.7.62`.

## 2026-07-30 — Intrinsic page height can defeat a nominally large control surface

- Evidence: a tall live screenshot expanded the preview's grid minimum, pushed the
  popup controls outside the visible app window, and the narrow-window rule hid the
  native resize affordance.
- Impact: the page appeared cropped and the user could not discover how to resize or
  maximize the browser even though those controls existed.
- Decision: give the preview a zero-minimum bounded grid row, keep overflow recovery
  on the popup, preserve resizing at narrow widths, and render an explicit striped
  resize corner plus visible instruction.
- Roadmap or validation change: strengthen M1.6 with a tall-content narrow-window
  containment test.
- Related commit/tag: planned for `local-v0.1.7.61`.

## 2026-07-30 — Upload approval must freeze both sides of the disclosure

- Evidence: `browser_upload_file` enforced the workspace boundary only when it ran
  and did not inspect the page field before approval.
- Impact: the user could approve a generic upload without seeing the destination
  field, while a changed file or changed page target could make that approval stale.
- Decision: freeze the unique file input plus the workspace-resolved file identity,
  name, size, and modification stamp. Show only name and size; reject any change
  before Playwright attaches the file.
- Roadmap or validation change: M1.7 and the inspected-upload failure matrix.
- Related commit/tag: planned for `local-v0.1.7.60`.

## 2026-07-30 — Available control still failed when the viewport was too small

- Evidence: installed M1.5 exposed working browser controls, but the fixed-size
  surface left the live page too small to inspect and offered no resizing affordance.
- Impact: the user could technically navigate but could not comfortably read or
  control normal desktop pages.
- Decision: make the browser surface nearly window-sized by default, resizable from
  its lower-right corner, and explicitly maximizable/restorable. Keep the rendered
  image element proportional so coordinate mapping remains accurate.
- Roadmap or validation change: M1.6 and a viewport/resize regression scenario.
- Related commit/tag: planned for `local-v0.1.7.59`.

## 2026-07-30 — In-app human-control handoff

- Observation: retaining a browser preview after an agent task was not sufficient;
  the user could inspect the page but could not interact with or assume the same
  isolated session.
- Decision: model browser ownership explicitly as `agent` or `user`. During user
  ownership, agent actions and new approval proposals fail closed. The expanded
  in-app control surface maps preview clicks to the fixed browser viewport and
  offers bounded navigation, scrolling, typing, and common keys.
- Recovery detail: if the UI is hidden or refreshed while the user owns control,
  the rail offers **Resume control**; returning control preserves the current page.
- Validation evidence: backend ownership/action tests, REST routing tests, the
  production frontend build, and the focused Chromium E2E handoff test pass.
- Roadmap or validation change: M1.5 records the handoff; inspected file upload is
  again the next smallest milestone slice.
- Related commit/tag: planned for `local-v0.1.7.58`.

Append entries only when observed evidence changes an assumption, rule, test, architecture, or priority. Keep entries concise and do not include credentials, cookies, private page content, or sensitive screenshots.

## Entry format

### YYYY-MM-DD — Short finding

- Evidence:
- Impact:
- Decision:
- Roadmap or validation change:
- Related commit/tag:

## Findings

### 2026-07-30 — A live headless browser can still be invisible to its user

- Evidence: the installed app retained the Selenium page, screenshot, and action
  evidence after the agent selected an option, while the user saw no browser surface
  and had no obvious way to restore the hidden rail.
- Impact: backend success and an open Chromium process did not satisfy observability;
  the agent could truthfully report completion while the user could not inspect it.
- Decision: reconcile the active session's browser state in the app shell, reveal the
  rail automatically, and retain a topbar Browser affordance whenever it is hidden.
  Treat true interactive takeover as a separate capability, not as a screenshot label.
- Roadmap or validation change: M1.4 covers browser visibility and recovery; an
  explicit in-app human-control handoff precedes further action expansion.
- Related commit/tag: planned for `local-v0.1.7.57`.

### 2026-07-30 — Dropdown labels and HTML values are not interchangeable

- Evidence: `browser_select` claimed to accept an option value or label, but passed
  either string directly to Playwright's value-oriented shorthand.
- Impact: a clear user request such as “choose Brazil” could fail when the HTML value
  was `br`, and a changed option list was not revalidated after approval.
- Decision: resolve the requested label/value while proposing, privately freeze the
  exact HTML value plus full option set, show only the human label, and execute the
  frozen value after revalidation.
- Roadmap or validation change: M1.3 covers dropdown selection and its failure modes.
- Related commit/tag: `local-v0.1.7.56`.

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
