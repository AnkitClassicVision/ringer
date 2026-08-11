# GW53 vocabulary round 3

## What changed

- Fortnight recognition now accepts an optional `in` and optional `a`, while the full-match boundary keeps `fortnightly` unresolved.
- Spelled day-of-month ordinals from first through thirty-first are normalized to numeric ordinals inside `resolve_relative_date`. They then use the existing numeric ordinal resolution and invalid-calendar-date handling.
- Numeric and spelled bare ordinals now select a strictly future occurrence. If the requested day is today or has passed, resolution advances to the next valid month.
- The existing end-of-month window recognizer now accepts the `tail end` prefix. Plain `the month` is treated as the current month, matching the requested phrase.

## Where

- `resolve_relative_date`: fortnight grammar, spelled-ordinal normalization, shared numeric-ordinal resolution.
- `extract_date_from_text`: tail-end month-window grammar.
- `gwtest/tests/test_vocab3.py`: seven tests covering the new forms and negative boundary.
- `proof_vocab3.py`: date-independent handler-seam proof.

## Known limitations

- Spelled ordinals are supported only for day-of-month values 1 through 31.
- These additions do not interpret recurrence phrases such as `fortnightly`; that word intentionally remains unresolved.
- End-of-month retains the existing window definition: day 24 through the calendar month's final day.
