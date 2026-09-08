# Debug Log — Compass (Week6 PoC)

Real issues only, found via actual E2E runs and manual (Playwright) browser testing — never
fabricated. Each entry links a symptom actually observed to a root cause actually confirmed in the
code.

| # | Title | Severity | Status |
|---|---|---|---|
| [01](issue-01-trend-radar-json-extraction-trailing-brace.md) | Trend Radar's JSON extraction failed on a real local-model output that was valid JSON plus one stray trailing `}` (a greedy regex swallowed the extra brace into the parse candidate) | Low | Fixed, re-verified |

## Real findings that are not code bugs

- **The local 0.5B model does not always include inline `[n]` citation markers in a research
  report**, even though the system prompt asks for one per claim. When it doesn't, the citation
  structural check trivially passes (there is nothing invalid to flag), and the content-similarity
  groundedness check can still legitimately pass at 100% — the answer can be accurate and grounded in
  substance while not visibly citing per-sentence. Observed directly in a captured screenshot
  (`docs/screenshots/02-research.png`). This is a known instruction-following limitation of very
  small (0.5B-parameter) local models, not a defect in the groundedness/citation-checking code
  itself — documented honestly in `docs/guide.html`'s Known Limitations section rather than
  silently ignored.
