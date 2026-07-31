# Current capabilities

This document describes the enhanced local OpenWorker branch as of
`local-v0.1.7.65`. It distinguishes working capabilities from roadmap items.
All provider calls still depend on the user's own configuration, permissions, and
provider availability.

## Usage, providers, and model routing

- Live Usage Dashboard with Usage, Models, Providers, Benchmarks, and Routing tabs.
- Per-session and daily token/cost estimates derived from recorded OpenWorker usage.
- Operation accounting for browser work, artifacts, and successful paid image
  generation where those dimensions are available.
- Provider account cards with status and `Last updated` timestamps. Official balances
  are shown only when a provider exposes a supported balance endpoint; unavailable
  data is not represented as zero.
- Configured/all model filters and Ollama model discovery from the local Ollama
  installation.
- Model comparison views distinguish local Ollama models from paid/API models.
- Intelligent Model Router with manual, shadow, and automatic modes; configurable
  history length, minimum confidence, maximum estimated cost, decision history, and
  user feedback.

Important limitation: costs are estimates unless explicitly labeled as official
provider data. A configured key does not imply that its provider exposes remaining
credit through an API.

## Deep Research

- Guided quick and standard research runs.
- Computational-thinking workflow that decomposes a question into claims.
- Grounded claim ledger with supporting, conflicting, and missing evidence.
- Source provenance and citation-oriented output.
- Structured research metadata for presentation candidates such as tables, charts,
  big numbers, timelines, processes, flow diagrams, org charts, quotes, and visuals.
- Markdown reports and structured JSON artifacts that can feed later artifact tools.

## Artifact Studio

### Documents

- Markdown-to-PDF conversion with a generated PDF artifact and preview.

### Presentations

- Research-to-presentation and Manus-style presentation launchers.
- Three-step Slide Designer: content/storytelling, visual design, and review.
- Standard widescreen 16:9 slide geometry.
- Presentation templates and a large slide-style catalog.
- Per-slide editing and previews based on Markdown/structured research content.
- Structured elements including tables, charts, timelines, processes, flow diagrams,
  org charts, quotes, and big-number slides.
- Presentation quality checks for hierarchy, density, visual direction, citations,
  and missing assets.
- Editable PowerPoint export.
- Optional original visuals through the approval-gated
  **Gemini Nano Banana 2 Lite** image tool.

Image generation is a paid external operation. OpenWorker shows approval before the
call and records successful billed operations in Usage. Declined or failed calls
must remain visible rather than being reported as successful images.

## Secure Browser Operator

- One isolated headless Chromium context per OpenWorker session.
- Public HTTP(S) navigation with localhost, private-network, credential-bearing URL,
  and unsafe file-path restrictions.
- Live preview in the right rail with a configurable refresh interval.
- Page text, visible controls, URL, screenshots, navigation history, and evidence.
- Action Inspector for click, type, select, upload, and scroll proposals.
- Target labels, domain, risk, expected result, stale-target detection, and
  `Approve once` / `Deny` controls beside the browser preview.
- Sensitive typed values are redacted from approval, event, audit, and screenshot
  display paths.
- Exact inspected scrolling with direction, pixel distance, affected area, changed
  page/position rejection, and single-use approval.
- In-app human-control handoff for navigation, clicking, scrolling, typing, and
  common keys in the same isolated browser session.
- Draggable, resizable, maximizable browser control surface over the main workspace.
- Workspace-bound uploads and screenshot exports.
- Page media analysis and authorized video/audio download controls, resolution
  selection, configurable Downloads destination, progress/cancel states, and
  optional EN/PT/ES subtitle handling where the source permits it.

External sites can rate-limit, require login, present CAPTCHA, restrict captions, or
use DRM. OpenWorker does not promise to bypass those controls.

## Local-first safety and release integrity

- Model keys and connector credentials stay in the local secret store.
- Consequential tool calls are approval-gated.
- Browser sessions, approvals, files, and evidence are isolated by OpenWorker session.
- Local releases use monotonic checkpoint tags and private GitHub synchronization.
- The installed app is backed up before replacement and critical packaged/installed
  binary checksums are compared.
- The latest rollback instructions are in [ROLLBACK.md](ROLLBACK.md).

## Still on the roadmap

- Fully reliable browser outcome assertions and bounded recovery/replay.
- Secure persistent authenticated browser profiles.
- Download quarantine and content scanning.
- Wide Research with managed multi-agent fan-out and adaptive evidence-gap routing.
- Podcast audio production and publishing workflow.
- Multimodal Task-to-Skill capture, disposable validation, and publishing.
- Organization-level brand systems and linked-data chart refresh.

See [MANUS_FEATURE_ROADMAP.md](MANUS_FEATURE_ROADMAP.md) for delivery status and
dependencies.
