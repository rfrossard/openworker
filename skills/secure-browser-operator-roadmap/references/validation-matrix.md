# Secure Browser Operator Validation Matrix

Apply relevant rows to every milestone and add newly observed failure modes.

| Area | Required assertions |
|---|---|
| Targeting | Unique target; visible and enabled; iframe/shadow DOM handled; stale target rejected; overlay matches action |
| Navigation | Redirect, new tab, same-page update, slow load, back/forward, unexpected domain, download navigation |
| Approval | Approve, deny, cancel, expiry, changed proposal, session-only grant, consequential action always gated |
| Execution | Exactly once; bounded retry; no duplicate submit; expected outcome verified; partial failure visible |
| Forms | Sensitive fields redacted; autofill not exposed; validation errors surfaced; unsaved state understood |
| Files | Explicit path and type; size limits; malware/untrusted warning; upload/download evidence; artifact attribution |
| Authentication | Model never receives secrets; profile isolation; logout/expiry; CAPTCHA and MFA defer to user |
| Recovery | Timeout, crash, restart, browser closed, selector drift, detached frame, offline/rate-limited state |
| Concurrency | Two sessions do not share page, cookies, approvals, files, action IDs, or audit events |
| Audit | Intent, target, domain, risk, approval, timestamps, before/after evidence, outcome, error, recovery |
| Tool protocol | One result for every tool call on success, error, denial, cancel, and timeout |
| Usage | Browser/action/artifact operation recorded once by session, day, and operation; retries not double-counted |
| Accessibility | Full keyboard operation, focus visibility, readable status, screen-reader name, contrast, reduced motion |
| Privacy | Logs and screenshots redact secrets; retention is explicit; private/local data never leaves scope |
| Packaging | Sidecar and browser assets present; installed build checksum matches; restart smoke passes |

## Minimum Action Inspector scenarios

1. Propose and approve a normal button click.
2. Deny a proposed form submission and verify no request occurs.
3. Change the DOM between proposal and approval and verify safe invalidation.
4. Present two similar labels and verify the overlay identifies only the intended target.
5. Cancel while waiting for approval.
6. Close the browser before approval.
7. Run two sessions with simultaneous proposals and verify isolation.
8. Restart OpenWorker and verify pending approvals are not executed.
9. Match zero, one, and multiple elements; only one unique visible enabled target may proceed.
10. Type a secret-like value and verify the execution input remains intact while live
    events, approval storage, audit output, controls, and screenshots expose no raw value.
11. Select an option by value and label; reject missing, disabled, ambiguous, changed,
    or differently executed options without mutating the page.
12. Finish an agent browser task with the browser still open; verify the current
    session's rail becomes visible, can be hidden, and can be restored from an
    explicit Browser affordance without changing pages or crossing sessions.
13. Take control of an active in-app browser, click, scroll, type, navigate, and
    return control; agent browser actions and proposals must fail closed throughout
    user ownership, and the page/session must remain unchanged at handoff.
14. Try takeover with a pending approval, a closed browser, and a second session;
    verify safe rejection and no ownership, action, cookie, or preview leakage.
15. Reload or temporarily hide the UI during user ownership; verify the control
    surface can be resumed and control can still be returned to the agent.
16. Open human control on large and narrow viewports; verify the browser starts
    large, can be resized and maximized/restored, keeps the full page aspect ratio,
    and maps preview clicks to the same browser coordinates at every size. Repeat
    with tall page content and verify the header, footer, controls, preview bounds,
    resize corner, and Maximize action all remain visible. Verify the window is
    portaled outside the right rail, opens over the central workspace, can be moved
    by its title bar, and is clamped fully into view after dragging or resizing the
    OpenWorker window.
17. Propose a workspace file upload and show the exact destination field plus only
    the file name and size. Reject an outside-workspace path, non-file input,
    ambiguous or changed target, substituted path, and file modified after approval;
    no rejected case may attach a file.
18. Resolve a pending browser action beside the preview with Approve once and Deny.
    Verify both controls address the same live composer approval, only appear for
    the matching browser tool, lock after the first decision, produce exactly one
    tool result, and cannot race a second click into duplicate execution.
19. Propose page and container scrolling in both directions. Show exact distance,
    affected area, and expected visible outcome. Reject a changed distance, URL,
    page/container scroll position, stale container, zero/oversized distance, denied
    action, reused approval, and approval from another session; no rejected case may
    move the page.
