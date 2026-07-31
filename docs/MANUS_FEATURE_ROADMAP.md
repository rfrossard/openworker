# OpenWorker capability roadmap

This roadmap tracks the five Manus-inspired capability families. For a factual list
of what works today, see [Current capabilities](CURRENT_CAPABILITIES.md).

Status meanings:

- **Available:** implemented and exposed in the local app.
- **In progress:** useful slices work, but the complete capability is not finished.
- **Planned:** design direction only; do not present it as available.

## Shared product model — In progress

Sessions already expose objectives, progress, sources, approvals, browser state,
artifacts, and usage. A fully unified, versioned Run model across every artifact and
multi-agent child run remains planned.

## 1. Secure Browser Operator — In progress

Available:

- isolated public-web Chromium sessions and live preview;
- page snapshots, screenshots, evidence, and navigation policy;
- inspected click, type, select, upload, and exact scroll actions;
- single-use approval, denial, stale-target rejection, and sensitive-value redaction;
- in-app user takeover in a draggable, resizable control surface;
- authorized page-media downloads and configurable destination.

Next:

- inspected download contract and quarantine;
- reliable outcome assertions, bounded retries, recovery, and replay;
- secure persistent profiles and login handoff;
- site-specific reusable skills.

Detailed implementation tracking lives in
[`skills/secure-browser-operator-roadmap`](../skills/secure-browser-operator-roadmap/).

## 2. Wide Research — In progress

Available:

- guided Deep Research;
- claim decomposition and grounded claim ledger;
- source/evidence artifacts and missing-evidence visibility;
- structured presentation candidates.

Next:

- visible parallel research lanes;
- managed fan-out with agent and budget limits;
- source deduplication, freshness, credibility, and conflict views;
- adaptive new lanes driven by evidence gaps and model routing.

## 3. Artifact Studio presentations — In progress

Available:

- Markdown/structured research ingestion;
- story, design, and review workflow;
- templates, slide styles, previews, editing, quality checks, and PPTX export;
- tables, charts, timelines, diagrams, org charts, quotes, citations, and generated
  image directions;
- approval-gated Gemini Nano Banana 2 Lite visuals with Usage attribution.

Next:

- stronger automatic visual-element selection and data validation;
- reference-deck theme extraction and organization brand kits;
- linked-data chart refresh;
- richer per-slide version comparison and recovery.

## 4. Podcast Generator — Planned

Planned slices:

1. sourced script artifact with solo, interview, briefing, and debate formats;
2. voice preview, segment generation, retry, cost estimate, mixing, chapters, and
   transcript;
3. loudness/clipping checks and an export package, with publishing separately
   approval-gated.

## 5. Task-to-Skill — Planned

Planned slices:

1. guided voice, screen, screenshot, log, file, text, and diagram capture;
2. reviewable `SKILL.md`, resources, examples, permission boundaries, and tests;
3. secret detection, disposable dry run, expected/actual comparison, local
   versioning, and separately approved publishing.

## Recommended delivery order

1. Finish the Secure Browser Action Inspector and reliable-action layer.
2. Add visible Wide Research lanes on the existing grounded-research foundation.
3. Continue presentation quality and artifact versioning.
4. Add podcast scripting before paid audio production.
5. Build Task-to-Skill after the workflows it must learn are mature.
