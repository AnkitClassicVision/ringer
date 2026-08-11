# GW58: relative offer floors and Chinese day-parts

## What changed

`fixed-bland_gateway.py` now restores an extraction-dropped relative time constraint from the clock in `context_date`. A later request sets `after` to the offered time plus one minute, which makes the existing inclusive `--after` behavior strictly later. An earlier request sets `before` to the offered time; the availability filter's existing before boundary remains the ceiling.

The lane-56 verbatim day-part authority now recognizes Chinese substrings: `早上` and `上午` map to before noon; `下午` maps to after noon; `晚上` and `傍晚` map to after 4:00 pm; `中午` maps to 11:00 am through 2:00 pm. The English-only `good <daypart>` greeting guard is unchanged.

## Handler seam and triggers

Both changes run in `clamp_availability_range`, beside the other verbatim authorities and before date resolution and CLI argument construction.

- Later: `\b(?:something\s+later|any\s+other\s+later|later\s+than\s+that|later)\b(?!\s+(?:this\s+(?:week|month)|next)\b)|晚一点|更晚`
- Earlier: `\b(?:anything\s+earlier|earlier|sooner)\b|早一点|更早`
- Latest exclusion: `\b(?:latest|last\s+appointment)\b`
- Explicit clock exclusion: `at|around|about` plus an hour, any `h:mm` clock, or an hour with `am` / `pm`
- Chinese day-parts use substring alternatives without word boundaries.

## Precedence

| Priority | Authority | Result |
|---:|---|---|
| 1 | Existing explicit `after` / `before` | Preserved byte-for-byte |
| 2 | Existing clock anchor or clock-window authority | Preserved; relative authority sees a non-dropped extraction and stops |
| 3 | Verbatim day-part, including Chinese | Applies its window; relative authority then stops |
| 4 | `latest` time preference or `latest` / `last appointment` wording | Existing latest path wins; no relative floor |
| 5 | Relative later / earlier plus parseable timed `context_date` | Restores an exclusive later floor or earlier ceiling |

## Known limitations

- Context parsing intentionally accepts the gateway's scheduler timestamp shape, `MM/DD/YYYY h:mm am/pm`. A date without a clock, malformed timestamp, or other timestamp dialect does not trigger.
- The later floor adds one minute rather than assuming a scheduler grid size. This is correct with the gateway's inclusive `after` semantics and remains valid if slot grids change.
- Relative phrases outside the specified English and Chinese vocabulary are left to extraction.
