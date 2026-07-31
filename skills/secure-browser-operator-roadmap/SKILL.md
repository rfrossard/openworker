---
name: secure-browser-operator-roadmap
description: Plan, implement, validate, and continuously update the Secure Browser Operator in OpenWorker. Use for any browser-agent change involving navigation, element targeting, approvals, screenshots, downloads/uploads, authenticated profiles, recovery, replay, audit trails, or teaching browser tasks as reusable skills.
---

# Secure Browser Operator Roadmap

Evolve browser automation through small, reversible milestones while keeping every action understandable, permissioned, observable, and recoverable.

## Begin every browser task

1. Read `references/roadmap.md`, `references/validation-matrix.md`, and `references/learning-log.md`.
2. Use `$openworker-release-integrity` for all OpenWorker inspection, development, installation, or publishing.
3. Inspect the current implementation and tests before changing the roadmap.
4. Select only the smallest milestone that produces independently useful behavior.
5. Record the baseline, assumptions, scope, and success metric.

## Apply the operator contract

Require every browser action to have:

- **Intent:** the user-visible goal.
- **Target:** URL, domain, element, and expected page state.
- **Risk:** read, edit, external communication, financial, credential, or destructive.
- **Permission:** automatic, session-approved, or per-action approval.
- **Evidence:** before/after state, URL, timestamp, screenshot or DOM evidence, and result.
- **Outcome:** succeeded, failed safely, cancelled, timed out, or needs user attention.
- **Recovery:** retry, re-locate, re-plan, undo when possible, or stop without side effects.

Never infer approval for login, sending, purchasing, publishing, uploading sensitive data, deleting, or changing account state.

## Work incrementally

1. Define a user-observable slice and its explicit non-goals.
2. Add a failing test or reproducible baseline.
3. Implement the minimum vertical slice across server, tool protocol, UI, and audit trail.
4. Test success, stale targets, navigation changes, timeout, cancellation, denial, retry, and duplicate execution.
5. Verify two overlapping sessions remain isolated.
6. Verify tool-call history remains structurally valid on every exit path.
7. Verify browser and artifact usage are attributed once to the correct session.
8. Update the roadmap only from observed evidence, not optimism.

## Decide milestone status

Use only these statuses in `references/roadmap.md`:

- `discovery`: requirements or architecture remain uncertain.
- `ready`: scope and acceptance criteria are testable.
- `in_progress`: implementation has started.
- `validated`: all required tests and installed-app smoke checks passed.
- `blocked`: an external dependency or unresolved safety issue prevents progress.
- `deferred`: deliberately postponed with a recorded reason.

Do not start a dependent milestone until its prerequisite is `validated`.

## Keep the roadmap alive

At the end of every relevant task:

1. Update milestone status, evidence, remaining risks, and next smallest action.
2. Append one concise entry to `references/learning-log.md` when evidence changes a design assumption, safety rule, test, or priority.
3. Preserve prior decisions; supersede them explicitly instead of silently rewriting history.
4. Add newly discovered failure modes to `references/validation-matrix.md`.
5. Keep all user-facing OpenWorker UI copy in English.
6. Version and publish the updated skill with the associated OpenWorker checkpoint.

If no roadmap change is justified, record nothing.

## Completion standard

Call a milestone complete only when:

- its acceptance criteria pass in focused and full relevant tests;
- installed-app behavior matches the packaged build;
- permissions and audit evidence are visible and understandable;
- cancellation and failure produce no unapproved side effect;
- restart and session isolation are verified when state is persisted;
- usage accounting is reconciled without billable calls unless explicitly authorized;
- rollback is available and the private GitHub checkpoint is verified.
