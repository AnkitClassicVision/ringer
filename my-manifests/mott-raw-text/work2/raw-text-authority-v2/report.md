# Raw-Text Authority round 2

## Fixed

- “I cannot do July 28; Wednesday is better”: same-segment negation kills July 28; the next clause’s Wednesday survives.
- “no not friday, monday works”: comma-segment scoping kills Friday but permits Monday.
- “Not the 5th, the 8th”: negation kills the first bare ordinal; last-surviving bare ordinal wins.
- “Anything but Friday”: the `anything but` negator kills Friday, leaving no candidate.
- “June 5 is my birthday; I need next Tuesday”: history kills the birthday clause; next Tuesday survives.
- Renewed/birthday/paid/last-time historical references: clause-level history terms kill every date candidate in that clause.
- May 5th Avenue and unit 12/5 on a road: clause-level address terms kill date-like address values.
- Attached emoji after “tomorrow”: unsupported characters normalize to spaces before tokenization.
- Raw-text wiring now uses a positive, whitespace/case-normalized Mott tenant gate and skips fetching when `first_available` is true.
- Conversation fetching now requires an API key, validates at least eight alphanumerics in the ID, refuses redirects, uses one retry deadline, retains two-second request timeouts, and caps reads at 512 KB.
- Conversation resolution uses the newest `created_at` USER message when all USER timestamps exist, otherwise the last USER message, and parses at most 2,000 characters.

## Verify

`CHECK PASSED: flag-off byte-identical to ORIGINAL (153 phrases, computed live); flag-on zero drift on 120 legacy; 12 new month-day phrases resolve; 8 compound phrases resolve; 13 over-broad/malformed inputs stay None; CVC inert under the tenant guard even with the flag on; source diff is additions only.`

`12 passed, 7 warnings in 0.14s`

All ten review sentences were also replayed directly and matched their required results.

## Residual risks

- Intent classification is deterministic vocabulary matching; unseen history, address, correction, or negation wording may need new terms.
- Python emits an existing deprecation warning for yearless `strptime` parsing; tests pass, but that parser should be revised before Python 3.15 changes its behavior.
