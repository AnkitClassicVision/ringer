# HOLDOUT CRITERIA - 20/20 Brief episode (red team only)

Never shared with the producer. The producer writes to the article template;
you judge against this rubric. The producer has never seen it.

## Your tests (execute, do not opine)

1. **Math audit.** Recompute every derived figure in article.md from its
   stated assumptions (locations, exams/week, weeks, rates, per-exam value).
   Show your recomputation in findings.md. Every discrepancy is a finding.
2. **Source claim-match.** Pick at least 2 load-bearing claims from the
   article and enter them as spot_checks (url + exact figure text). The
   wrapper fetches the pages and verifies the figures appear verbatim.
3. **Folklore accuracy.** If the article busts a popular number, the ORIGIN
   story of that number must itself be sourced. An unsourced debunk is worse
   than the myth.
4. **Voice audit.** The bar: operator-with-receipts, not trade press. Quote
   any sentence in findings.md that sounds like a publication or a vendor.
   More than 3 such sentences = voice fails.
5. **Assumption honesty.** Every modeled number must be labeled an
   assumption in the article text. Find any unlabeled one.
6. **Teaser discipline.** One stat per teaser, never the full analysis, each
   teaser readable alone, join line on every channel. Quote violations.
7. **Holdback honesty.** The members-only extra promised in the article must
   be named concretely. Vague "more inside" fails.
8. **Voice pack compliance.** The producer standard is
   `/mnt/d_drive/repos/icargrow/content/20-20-brief/voice/voice-pack.md`.
   Read it. Render a per-rule-family verdict: hard bans, cadence, register,
   claims, structure. Each family is pass or fail with one quoted piece of
   evidence per failure. Any family fail = verdict at most `revise`.

## Kill criteria (any one = verdict fail)

- Any fabricated source, figure, or quote
- Math that does not survive recomputation presented as fact
- The central myth-bust or claim is itself unsourced
- Stat card numbers differ from the article body

## Verdict rules

- `fail`: any kill criterion hit
- `revise`: no kills, but named fixes required before Ankit review
- `pass`: ready for Ankit review as staged

## Output contract

Write ./verdict.json exactly in this schema:

```json
{
  "verdict": "pass|revise|fail",
  "confidence": 0,
  "scores": {"surprise": 0, "shareability": 0, "honesty": 0, "math_holds": true, "voice": 0},
  "findings": ["one line per finding"],
  "spot_checks": [{"url": "https://...", "claimed_figure": "exact figure text", "note": "why this claim is load-bearing"}],
  "kill_list": ["specific defects that must be fixed"]
}
```

And ./findings.md: your recomputations, quoted problem sentences, and
reasoning per test.
