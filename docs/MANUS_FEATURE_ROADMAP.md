# OpenWorker Capability Roadmap

This roadmap delivers five Manus-inspired capabilities as small, testable increments.
All user-facing copy is English. Each phase reuses the same run, artifact, approval,
and provenance concepts so later features do not create parallel infrastructure.

## Shared product model

Every capability should produce a **Run** with:

- a clear objective and current status;
- steps and child runs;
- sources, inputs, and tool activity;
- approval requests for consequential actions;
- versioned artifacts with previews;
- model, token, latency, and estimated-cost telemetry.

This model lets Usage explain not only what was spent, but which deliverable and
workflow produced the spend.

## 1. Secure Browser Operator

### V1 — Read and observe

- Isolated Playwright browser context with no persisted profile or downloads.
- Public HTTP(S) destinations only; localhost and private networks are blocked.
- Page text, visible controls, current URL, and screenshots.
- Browser status and preview in the task rail.
- External page content is explicitly treated as untrusted.

### V2 — Controlled interaction

- Per-action approval for clicks, typing, uploads, and closing.
- Workspace-only file uploads and screenshot exports.
- Domain allowlist and session-level “always allow reads” controls.
- Navigation history and evidence attached to the run.

### V3 — Reliable workflows

- Deterministic locator fallbacks and recovery.
- Login handoff without exposing credentials to the model.
- Download quarantine, content scanning, and explicit import to the workspace.
- Replayable browser traces and site-specific skills.

## 2. Wide Research

### V1 — Manual research board

- User creates research questions and assigns a model to each lane.
- Parallel read-only researchers return source cards and claims.
- A synthesis step highlights agreement, conflict, and missing evidence.

### V2 — Managed fan-out

- Automatic decomposition with a visible budget and agent limit.
- Source deduplication, citation coverage, freshness, and credibility signals.
- Pause, cancel, retry, or reassign any lane independently.

### V3 — Adaptive research

- The orchestrator opens new lanes only when evidence gaps justify the cost.
- Model Router selects models per lane using quality, latency, privacy, and price.
- Reusable research plans become templates or skills.

## 3. Artifact Studio — Presentations

### V1 — Brief to outline

- A `Presentation` artifact type inside Artifact Studio.
- Editable audience, objective, tone, slide count, and source brief.
- Outline approval before expensive generation.

### V2 — Generate and edit

- Generate `.pptx` with theme tokens, layouts, speaker notes, charts, and citations.
- Slide navigator, preview, per-slide regenerate, and version history.
- Export validation for overflow, missing assets, and unreadable contrast.

### V3 — Brand systems

- Import a reference deck and extract a reusable presentation theme.
- Brand kits, locked templates, and organization-level components.
- Data refresh for linked charts without rebuilding the deck.

## 4. Podcast Generator

### V1 — Script artifact

- Sources or task output become a structured episode script.
- Format choices: solo, interview, briefing, or debate.
- Duration, audience, chapters, pronunciation notes, and fact citations.

### V2 — Audio production

- Voice selection with a short preview before generation.
- Segment-level generation, retry, and cost estimate.
- Mix speech, intro/outro, music ducking, chapters, transcript, and cover art.

### V3 — Publishing workflow

- Loudness and clipping checks, chapter metadata, and show-note generation.
- Export an audio package; external publishing remains an explicit approved action.

## 5. Task-to-Skill

### V1 — Multimodal capture

- A guided capture session accepts voice, screen recordings, screenshots, logs,
  files, text, and diagrams.
- The timeline lets the user label intent, decisions, inputs, outputs, and exceptions.

### V2 — Skill draft

- Convert the capture into a reviewable `SKILL.md`, resources, examples, and tests.
- Detect secrets and personal data before saving.
- Show assumptions, unresolved choices, and required permissions.

### V3 — Validate and publish

- Run the draft in a disposable workspace against representative examples.
- Compare expected and actual outputs, then revise the skill.
- Save locally first; publishing to a repository is a separate approved action.

## Recommended delivery order

1. Finish Secure Browser Operator V1 and V2.
2. Build the shared Run model through Wide Research V1.
3. Add Presentation artifacts to prove Artifact Studio’s versioning and preview model.
4. Add Podcast scripts, then audio generation.
5. Build Task-to-Skill last so it can capture and reuse all four mature workflows.

This sequence gives Task-to-Skill high-quality behavior to learn from and avoids
creating one-off orchestration, artifact, or approval systems.
