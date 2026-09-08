# Debug Log — Cradle (Week5_2 PoC)

Real issues only, found via actual design research (including tracing an assumed guardrail-ordering
behavior by hand) and manual (Playwright) browser testing — never fabricated. Each entry links a
symptom actually observed to a root cause actually confirmed in the code.

| # | Title | Severity | Status |
|---|---|---|---|
| [01](issue-01-guardrail-check-order.md) | A naive guardrail check order (cost cap before permission) mislabels unauthorized-tool attempts in the audit trail as budget events instead of permission violations | Medium (identified during design; corrected proactively in Cradle, never shipped here) | Corrected by design, regression-tested |
| [02](issue-02-stale-thinking-box-after-final-answer.md) | The Final Answer step doesn't participate in the normal step lifecycle — causing (a) a stale "thinking" box left on screen after a live run completes, and (b) the answer rendering twice when reopening a past run | Low | Fixed, re-verified |
| [03](issue-03-abandoned-runs-stuck-at-running-forever.md) | A run whose SSE stream is abandoned mid-flight (browser navigates away / tab closes while the agent loop is still running) stays "RUNNING" forever — never completable, never escalatable, invisible to History, permanently skewing analytics | Medium | Fixed (lazy reaper), regression-tested |
| [04](issue-04-live-vs-reopened-step-numbering-mismatch.md) | The same completed run shows different step numbers for the same card depending on whether it's watched live or reopened from History — the live view invents its own per-card counter instead of using the backend's real per-cycle step number | Low | Fixed, re-verified |
| [05](issue-05-e2e-regression-test-polluted-the-admin-account.md) | The E2E suite's stale-run regression test attached its synthetic data to whichever user has the lowest id — always the real admin account, not the suite's own disposable test user — polluting the admin's Dashboard/Console/History with a fake "(regression test — simulated abandoned run)" entry | Low | Fixed, re-verified |
| [06](issue-06-audit-log-latency-always-zero.md) | The audit trail's own `latency_ms` column — the "how long did this take" field, present specifically for that — is hardcoded to `0.0` at every AI-call log site, so every row for every action always reads exactly 0ms regardless of real duration | Low | Fixed, re-verified |

## Real findings that are not code bugs

- **A screenshot-script wait condition (`text=/Final Answer/`) resolved on the model's own raw
  streaming text mid-generation**, not on true completion — this is what led to discovering issue
  03 (the script's premature navigation reproduced the exact abandonment scenario a real user
  closing a tab mid-response would also trigger). The underlying vulnerability was real; the wait
  condition just found it earlier than a human would have noticed it. See
  `prompts/vibe_coding_prompts.md`.
- **A second, separate selector-precision trap**: `getByRole('button', {name: 'Approve', exact:
  true})` matched nothing because the real accessible name includes a checkmark prefix
  ("✓ Approve"). Fixed before it could produce a false bug report.
- **A third selector/API-usage trap, initially mistaken for a possible product bug**: after fixing
  the Final-Answer-substring wait, the replacement condition — "wait for the Run button to
  re-enable" — was itself invalid, not just imprecise. It didn't fail because of a Playwright
  quirk; the button's `disabled={busy || !question.trim()}` stays permanently `true` once
  `send()` clears the input field, regardless of `busy`. A direct poll of `button.isDisabled()`
  read `true` at every checkpoint through 56 seconds while the page's own rendered text
  simultaneously showed a fully correct completed answer — proof the signal itself was wrong, not
  slow. Separately, `page.waitForFunction(fn, {timeout})` was passing `{timeout}` as the function's
  `arg` parameter instead of as `options` (the correct 3-argument form is
  `page.waitForFunction(fn, null, {timeout})`), which silently fell back to Playwright's default
  30s timeout — a second, independent mistake layered on top of the first. Fixed by waiting on the
  same status-badge text already proven reliable elsewhere in the script, and dropping the
  button-state approach entirely.
