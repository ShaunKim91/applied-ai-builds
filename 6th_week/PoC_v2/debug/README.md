# Debug Log — Verity (Week6 PoC_v2)

Real issues only, found via actual manual (Playwright) browser testing and direct measurement
against the running models — never fabricated. Each entry links a symptom actually observed to a
root cause actually confirmed in the code.

| # | Title | Severity | Status |
|---|---|---|---|
| [01](issue-01-entries-race-condition.md) | A newly-created research thread's entries could theoretically be silently wiped by a stale background fetch racing against an in-flight streaming query | Low (not actually triggered in practice, but a real architectural risk) | Fixed by design, structural |
| [02](issue-02-fraud-signal-false-positives.md) | The fraud-signal embedding-similarity fallback flagged all five fraud patterns on a completely unrelated question — measured cosine similarity of 0.74–0.82 regardless of actual relevance | Medium (undermines the whole feature's credibility) | Fixed (keyword-only), regression-tested |
| [03](issue-03-groundedness-blind-spot.md) | The groundedness check gave a perfect 1.0 score to a real, hallucinated federal agency name that appears in none of the fictional sources — the exact failure the whole grounding pipeline exists to catch | High (a real gap in the product's core safety claim) | Partially mitigated (entity cross-check), regression-tested, honestly disclosed as incomplete |

## Real findings that are not code bugs

- **A Playwright actionability-retry quirk**: a "submit" button whose `onClick` handler
  synchronously sets `busy=true` (disabling itself) confuses Playwright's own `.click()` retry loop —
  the very first dispatch actually succeeds and the real request goes through, but Playwright
  interprets the button going disabled immediately after its own dispatch as "the click didn't
  land," and retries pointlessly for the full timeout even though the real work already happened.
  Fixed in the screenshot script with `{ force: true }`, which skips Playwright's own
  actionability re-check.
- **A more consequential wait-condition trap**: `page.waitForResponse()` resolves once a response's
  **headers** arrive, not once its **body** finishes — for `/api/research/query` (a genuine
  `StreamingResponse`), that's nearly instantaneous, long before the model has actually finished
  generating or the client has processed the terminal `done` event. Combined with the actionability
  quirk above, this produced a real, confusing failure chain: the first query's screenshot was taken
  moments after headers arrived (not after the answer rendered), showing "No research yet in this
  thread"; the *second* query in the same script then silently no-op'd because the first query's
  `busy` flag was still `true` in the background, making the second `waitForResponse` time out
  waiting for a request that was never sent. The fix was waiting on an actual UI completion signal
  (the rendered "Groundedness" badge) instead of any network-level proxy for a streaming endpoint.
  This is the same class of trap — a network/DOM signal that doesn't actually correlate with a
  streaming response's true completion — that has now recurred, in different specific forms, across
  every prior week's screenshot script in this project series.
