# OpenWorker Integrity Matrix

Use this matrix to select checks in addition to the core gates. A changed subsystem requires its row. Run all milestone checks before a public release or after a major dependency/platform upgrade.

| Area | Every relevant change | Every local release | Milestone / periodic |
|---|---|---|---|
| Persisted data | Old fixture loads; round trip; unknown fields preserved; corrupt state handled | Backup and restart against installed app | Restore drill on a copy; migration chain from oldest supported version |
| Sessions and agents | Success, failure, cancel, retry; tool-call/result pairing | Two-session isolation smoke test | Long-running resume and crash recovery |
| Browser | SSRF and local-network denial; origin boundaries; download path safety | Isolated launch, navigation, preview, close, cleanup | Adversarial pages, permission prompts, resource leak soak |
| Artifacts/files | Path traversal denial; atomic write; filename collision | Generate, reopen, export one artifact | Large-file limits, disk-full and interrupted-write recovery |
| Providers | Key redaction; auth failure; timeout; 429; malformed response | Configured provider/account refresh | Contract test against provider sandbox or fixtures |
| Usage/costs | One event counted once; session/day/model/provider attribution | Dashboard and account snapshot after controlled non-billable flow | Reconcile sampled invoices/official usage; rounding and currency audit |
| Model routing | Availability changes; fallback reason; local/paid distinction | Selected-model smoke without paid call | Budget caps, latency/cost policies, routing replay |
| Packaging | Resource and sidecar manifest tests | Full package, checksum, installed-app smoke | Clean-machine and supported-OS matrix |
| Security | Secret scan; dependency inputs validated; least privilege | Private remote and disabled upstream push | Dependency audit, SBOM, threat-model review, signed release evaluation |
| UI | English copy; loading/empty/error/stale states; keyboard path | Light/dark and narrow panel smoke | Accessibility scan, visual regression, localization readiness |
| Performance | No obvious unbounded polling/listeners | Startup and idle-resource sanity | Large-history benchmark, memory/network soak, regression budgets |
| Rollback | Changes remain backward-aware where feasible | Versioned backup and verified checksum | Actual restore/relaunch drill using a disposable data copy |

## Hard invariants

- Never store or render raw API keys after entry.
- Never send local files, browser cookies, prompts, or artifacts to a provider unless the user authorized that scope.
- Never represent an unavailable official balance as zero.
- Never count failed preflight requests as model usage unless the provider billed them.
- Never double-count streamed, retried, resumed, or replayed events.
- Never let one session read another session's browser, credentials, files, or temporary artifacts.
- Never silently discard old persisted fields during migrations.
- Never install without a recoverable previous app bundle.
- Never publish to a repository whose ownership or privacy was not verified.

## Financial acceptance checks

For a controlled event, capture sanitized values before and after:

- session input/output tokens and estimated cost;
- daily/provider/model totals;
- operation counters for browser navigations and artifacts;
- official balance/usage timestamp and provider status.

Assert:

1. The session delta equals the aggregate delta.
2. Exactly one provider and model receive the event unless routing actually changed.
3. Retry and resume do not duplicate the event.
4. Official and estimated values remain visually and structurally distinct.
5. Rate limits and unavailable endpoints preserve the last known value with a stale marker.
6. Account polling uses bounded backoff and does not create billable calls.

## Release stop conditions

Stop before install/tag/push when any of these is true:

- mandatory tests or production build fail;
- worktree scope is ambiguous;
- backup or checksum verification fails;
- installed binary differs from the packaged binary;
- persisted data cannot be migrated or reopened;
- a credential or private payload appears in a diff/log;
- accounting duplicates or loses a controlled event;
- origin ownership/privacy cannot be confirmed;
- remote commit/tag verification fails.

Document non-blocking external outages separately; do not convert them into false success or zero values.

## Recommended repository protections

- Keep the canonical repository private.
- Require pull requests and successful checks for the protected release branch when collaboration begins.
- Require review from the owner or CODEOWNERS for security, provider, migration, and release files.
- Enable secret scanning, dependency alerts, and automated dependency update review.
- Prefer signed commits/tags for releases and retain build provenance/checksums.
- Keep CI credentials read-only by default and scope release credentials to protected environments.
- Exercise backup restoration periodically; an untested backup is not a rollback guarantee.
