# HOLDOUT CRITERIA - 20/20 Brief topic scouts (red team only)

Never shared with the producing scout. The producer writes to the output
contract; you judge against this rubric. The producer has never seen it.

## Your tests (execute, do not opine)

1. **Surprise test.** For each candidate: would a 5-location optometry owner
   say "I did not know that"? Score 1-10. A known fact in a new wrapper fails.
2. **Forward test.** Is there a specific person the owner would forward this
   to (partner, OD friend, office manager)? If nobody specific comes to mind,
   the shareability claim is weak. Say so.
3. **Math audit.** Recompute every derived number from the stated assumptions.
   If the candidate says "X per year" from "Y per week", multiply it yourself.
   Flag every discrepancy.
4. **Honesty audit.** Vintage figures must be flagged with their year.
   Assumptions must be labeled as assumptions. Anything presented as current
   fact that is actually old data is a red mark.
5. **Coverage plausibility.** If market_gap says NOT COVERED, judge whether
   that is believable for the named trades. You may reason from the source
   list; you do not need to re-search. If the gap claim smells wrong, flag it.
6. **Owner language audit.** The owner_language phrases must sound like real
   forum speech. Marketing-flavored phrases ("seeking solutions for...") fail.
7. **Spot checks (load-bearing).** Pick at least 2 figure+URL pairs from the
   candidate's own source list that the whole candidate depends on. Enter them
   in spot_checks. The wrapper will fetch those URLs and verify the figure
   appears on the page verbatim. Pick the claims that would kill the candidate
   if false.

## Kill criteria (any one = candidate dies, name it in kill_list)

- Money stat is unverifiable or folklore presented as fact
- Trades already own the same angle (market_gap dishonest)
- Owner language invented
- Math does not survive recomputation

## Verdict rules

- `fail`: any kill criterion hits ALL candidates, or fabrication suspected
- `revise`: at least one candidate dies or needs work, at least one survives
- `pass`: at least 2 candidates are production-ready as scouted

## Output contract

Write ./verdict.json exactly in this schema:

```json
{
  "verdict": "pass|revise|fail",
  "confidence": 0,
  "scores": {"surprise": 0, "shareability": 0, "honesty": 0, "math_holds": true, "voice": 0},
  "findings": ["one line per finding"],
  "spot_checks": [{"url": "https://...", "claimed_figure": "exact figure text", "note": "why this claim is load-bearing"}],
  "kill_list": ["candidate titles that must die"]
}
```

And ./findings.md: one short paragraph per candidate with your reasoning.
