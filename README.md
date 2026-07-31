# OpenWorker

OpenWorker is a local-first AI coworker for turning requests into finished work. It combines a desktop workspace, an approval-gated agent runtime, connected tools, model choice, research, browser operation, and artifact generation in one session.

This repository is the private enhanced edition maintained by `rfrossard`. It includes the upstream OpenWorker foundation plus the local Usage Dashboard, Intelligent Model Router, grounded Deep Research, Artifact Studio, Gemini Nano Banana 2 Lite image generation, and Secure Browser Operator described below.

> **Beta:** features that call an external provider, browse a third-party site, download media, or write to an integration remain subject to provider limits, permissions, rate limits, login state, and approval.

## What OpenWorker does

You describe an outcome, for example:

- “Research the current agent protocol landscape and create a sourced presentation.”
- “Open this public form, select the requested option, and show me the result before submitting.”
- “Turn this Markdown report into a polished PDF and an editable PowerPoint.”
- “Compare the configured models, estimate the cost, and recommend the best one for this task.”

OpenWorker plans the work, asks for approval before consequential actions, keeps evidence and artifacts with the session, and reports what actually happened.

## Feature overview

### Usage Dashboard and Model Router

- Live tabs for Usage, Models, Providers, Benchmarks, and Routing.
- Session and daily token/cost estimates, including browser, artifact, and image operations when usage dimensions are available.
- Provider cards with official account balances where supported, `Last updated` timestamps, stale/error states, and clear separation from local estimates.
- Configured-versus-all model filtering, Ollama discovery, and visual distinction between local and paid/API models.
- Manual, shadow, and automatic routing modes with confidence and estimated-cost guardrails, decision history, and feedback.

### Grounded Deep Research

- Guided quick and standard research runs.
- Computational-thinking decomposition into claims, evidence, conflicts, gaps, and sources.
- A claim ledger and provenance-aware Markdown and JSON artifacts.
- Presentation candidates for tables, charts, big numbers, timelines, processes, flow diagrams, org charts, quotes, and illustrative visuals.

### Artifact Studio

- Markdown-to-PDF conversion with preview.
- Research-to-presentation and Manus-style presentation workflows.
- Three guided stages: content/storytelling, design, and review.
- Widescreen 16:9 slides, templates, a large style catalog, per-slide editing, and live previews.
- Structured elements: tables, bar/donut charts, big numbers, timelines, processes, flow diagrams, org charts, quotes, citations, and speaker notes.
- Presentation quality checks for hierarchy, density, source coverage, layout, and missing assets.
- Editable PPTX export.
- Optional approval-gated original visuals through Gemini Nano Banana 2 Lite, with successful operations attributed in Usage.

### Secure Browser Operator

- An isolated Chromium context per OpenWorker session.
- Public-page navigation with localhost, private-network, unsafe-file, and credential-bearing URL protections.
- Live preview with configurable refresh, page text, controls, URL, screenshots, navigation history, and evidence.
- Action Inspector for click, type, select, upload, and exact inspected scroll actions.
- Single-use approval, denial, stale-target detection, expected-result checks, risk labels, and sensitive-value redaction.
- In-app human takeover in a draggable, resizable, maximizable browser surface over the workspace.
- Workspace-bound uploads and screenshot exports.
- Authorized page-media analysis and video/audio downloads with resolution selection, configurable Downloads destination, progress/cancel states, and optional EN/PT/ES subtitles where the source permits them.

External sites may require login, CAPTCHA, consent, or may rate-limit captions/media. OpenWorker does not bypass DRM, authentication, or site controls.

### Connected work

Use local files, the terminal, and MCP-compatible tools alongside integrations such as GitHub, Slack, Jira, Notion, Linear, HubSpot, Outlook, Gmail, and Google Calendar. Automations can run recurring work and park approval requests in the app.

## Models and providers

Bring your own API key or run locally. The enhanced edition supports configured models from OpenAI, Anthropic, Google Gemini, DeepSeek, Qwen, Mistral, Grok/xAI, Kimi, GLM, MiniMax, Together, Fireworks, and other compatible providers, plus local Ollama models.

Provider support depends on the model's API capabilities. A model appearing in the catalog does not guarantee tool calling, vision, audio, image generation, balance endpoints, or availability in your account.

## Privacy and approvals

The agent server, conversations, session state, connector credentials, and model keys are stored locally. External traffic occurs only through the providers and integrations you configure. Consequential writes, sends, shell commands, browser interactions, and paid image generation are approval-gated.

Do not put API keys, cookies, authorization headers, or private source material in issues, fixtures, screenshots, commits, or generated artifacts.

## Run from source

### Requirements

- macOS 12+ or Windows 10/11
- Python 3.10+
- Node.js 20+
- Rust toolchain via [rustup](https://rustup.rs/) for the desktop shell
- Ollama is optional for local models

### Start the local server and UI

```shell
git clone https://github.com/rfrossard/openworker.git
cd openworker

# Create the Python environment and install dependencies.
bash packaging/setup_dev_env.sh

# Terminal 1: start the agent server.
.venv/bin/openworker-server --cwd ~/some/project --port 8765

# Terminal 2: start the browser UI.
cd surfaces/gui
npm install
npm run dev
```

For the native desktop shell, run `npm run tauri dev` from `surfaces/gui/` instead. The Tauri shell supervises the local server.

Configure providers and connectors from the app. For Ollama, start Ollama locally and install models with the Ollama CLI; OpenWorker discovers available local models when the provider is enabled.

## Tests and builds

```shell
# Backend
.venv/bin/pytest

# GUI unit tests, end-to-end tests, and production build
cd surfaces/gui
npm test
npm run e2e
npm run build
```

Desktop packaging uses `packaging/build_dmg.sh` on macOS and `packaging/build_windows.ps1` on Windows. Release work also requires a recoverable installed-app backup, packaged/installed checksum comparison, installed-app smoke checks, monotonic local tags, and private-origin synchronization. See [ROLLBACK.md](docs/ROLLBACK.md).

## Repository map

| Path | Purpose |
|---|---|
| `coworker/` | Python agent runtime, providers, connectors, MCP, memory, and automations |
| `surfaces/gui/` | React interface and Tauri desktop shell |
| `stt/` | Rust speech-to-text sidecar |
| `packaging/` | Development bootstrap and desktop packaging |
| `docs/` | Capability reference, roadmap, decisions, and rollback procedures |
| `tests/` | Backend test suite |

## Documentation map

- [Current capabilities](docs/CURRENT_CAPABILITIES.md) — behavior available in the enhanced local branch.
- [Capability roadmap](docs/MANUS_FEATURE_ROADMAP.md) — available, in-progress, and planned work.
- [Rollback and release integrity](docs/ROLLBACK.md) — backups, tags, checksums, and recovery.
- [GUI development guide](surfaces/gui/README.md) — local UI setup and desktop development.

## Development principles

Changes should be incremental, reversible, and observable. Preserve unrelated user work, add regression coverage for behavior changes, keep all user-visible UI text in English, redact secrets, and never claim official provider balance or cost data when only a local estimate exists.

The enhanced branch uses monotonic tags in the form `local-v<base>.<sequence>` and pushes only to the private `origin`; the upstream remote is fetch-only.

## License

MIT — see [LICENSE](LICENSE).
