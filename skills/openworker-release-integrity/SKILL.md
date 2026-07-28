---
name: openworker-release-integrity
description: Enforce safe, reversible evolution of the OpenWorker desktop app. Use whenever Codex analyzes, changes, fixes, tests, packages, installs, versions, releases, rolls back, or publishes OpenWorker, including changes to agents, browser tools, artifacts, model providers, API keys, usage, balances, or costs. Apply the smallest relevant checks during development and the complete release gates before installing or publishing.
---

# OpenWorker Release Integrity

Protect user data, credentials, financial telemetry, the installed app, and the private GitHub history while evolving OpenWorker.

## Start every task

1. Locate the OpenWorker repository and read its instructions.
2. Inspect the branch, worktree, remotes, latest local release tag, and installed app state.
3. Preserve unrelated user changes. Never discard or overwrite them.
4. Confirm `origin` is the user's private repository and upstream push remains disabled before publishing.
5. Classify the work:
   - **Inspection only:** perform read-only checks and report evidence.
   - **Development change:** run the development gates.
   - **Install or release:** run development and release gates.
   - **High-risk change:** also run the relevant checks in [integrity-matrix.md](references/integrity-matrix.md).

Treat authentication, payments/balances, migrations, file access, browser isolation, tool-call history, auto-update, packaging, and persisted session changes as high risk.

## Develop incrementally

1. Establish a focused failing test or reproducible baseline when fixing a defect.
2. Make the smallest coherent change.
3. Add regression coverage for changed behavior and important failure paths.
4. Run focused tests after each increment.
5. Never expose API keys, cookies, tokens, authorization headers, or full credential-bearing responses in source, fixtures, logs, screenshots, commits, or the final report.
6. Do not issue billable provider calls merely to test accounting. Read-only balance/account checks are permitted. Obtain explicit authorization and a spending ceiling before a paid smoke call.
7. Keep all user-visible OpenWorker UI text in English.

## Run development gates

Before calling a change complete:

1. Run focused tests for every changed component.
2. Run the full Python suite with the repository virtual environment.
3. Run the full frontend test suite and production build.
4. Run `git diff --check`.
5. Review the final diff and status for secrets, generated debris, accidental scope, debug code, and unrelated files.
6. For persisted-state changes, test loading the previous format, migration, interrupted/partial state, and round-trip preservation.
7. For async or agent changes, test success, failure, cancel, retry, idempotency, and two overlapping sessions.
8. For tool-call changes, verify every assistant tool call receives exactly one matching tool result before the next model request, including error and cancellation paths.

Never weaken or remove a test solely to make a gate pass. Stop and report a failing mandatory gate.

## Verify usage, costs, and provider accounts

For changes that can invoke models, tools, browser navigation, artifact generation, research, or provider accounting:

1. Verify usage is recorded per session and aggregated by day, model, provider, and operation type.
2. Verify input, output, cached, reasoning, image, audio, tool, browser, and artifact usage where the provider supplies those dimensions.
3. Reconcile local estimates against official provider usage or balance endpoints when available.
4. Label official balances separately from estimated spend. Never invent remaining balance for providers that do not expose it.
5. Verify configured-provider polling timestamps, stale/error states, retries, rate-limit handling, and secret redaction.
6. Compare a before/after snapshot around a controlled test. Confirm totals do not double-count retries, resumed streams, or duplicate events.
7. Treat a balance check failure as a visible degraded state, not as `$0.00`.

Read [integrity-matrix.md](references/integrity-matrix.md) for the financial and privacy assertions.

## Run release gates

Before installing, tagging, or pushing a release:

1. Complete all development gates.
2. Determine the next monotonic `local-v<base>.<sequence>` version without reusing a tag.
3. Build with the repository's complete packaging script. Do not substitute a partial frontend or Tauri build.
4. Verify the packaged app and all required sidecars/resources exist.
5. Stop only the exact running OpenWorker process.
6. Create a version-specific recoverable backup of `/Applications/OpenWorker.app` before replacement.
7. Verify the backup exists and record its path and checksum.
8. Install the packaged app, then compare checksums of critical packaged and installed binaries.
9. Launch the installed app and smoke-test health, session loading, dashboard usage, provider accounts, browser isolation, and the changed feature.
10. Verify restart persistence and that the app can reopen existing user data.
11. Keep the backup until the next release is proven stable.

Do not install or publish after a failed test, failed backup, packaging error, checksum mismatch, migration failure, secret finding, or incorrect repository visibility.

## Version, publish, and preserve rollback

1. Stage explicit intended files only.
2. Commit with a concise description of the verified change.
3. Create the release tag only after packaged-app smoke tests pass.
4. Confirm the destination repository is private immediately before push.
5. Push the current branch and exact tag to `origin`; never push to `upstream`.
6. Confirm local and remote commit/tag identities match.
7. Report the exact rollback artifact and restoration procedure.

Do not rewrite shared history, force-push, delete tags, or publish secrets. Never claim synchronization until remote verification succeeds.

## Report evidence

Finish every development or release task with:

- version, branch, commit, and tag;
- focused and full test results;
- production build and packaged-app smoke result;
- migration/security/concurrency checks relevant to the change;
- official balance status and local usage reconciliation, without secrets;
- installed binary verification;
- backup location and rollback readiness;
- private GitHub synchronization status;
- any skipped check, why it was skipped, its risk, and the next safe action.

For recurring maintenance and milestone checks, follow [integrity-matrix.md](references/integrity-matrix.md).
