# GW47 specificity fix

## Failure evidence

The decisive live probe supplied for this lane used `user_text='No Thursday the 27'`
with `from='08/27/2026'` and returned 08/06 slots. Repeating the probe with
`user_text='08/27/2026'` returned 08/27. This isolates the failure to the
authoritative sentence layer: it selected the bare weekday and replaced the
fully specified pathway date.

## Specificity rule

| Rank | Date language | Examples |
|---:|---|---|
| 3 | Full calendar date, month plus day, or weekday qualified by a week reference | `08/27/2026`, `2026-08-27`, `August 27`, `Monday the week of 08/18/2026` |
| 2 | Day-of-month ordinal or relative offset | `the 27`, `the 27th`, `in 2 weeks`, `2 weeks from today` |
| 1 | Bare weekday or bare today/tomorrow | `Thursday`, `today`, `tomorrow` |
| 0 | No date found | unrelated text |

The sentence-derived result replaces the explicit `from` only when its rank is
strictly greater. Equal or lower rank preserves the explicit pathway value.
The gate covers deterministic date, range, either-day, conflict, and
authoritative-LLM results.

The parser now treats `the 27`, `the 27th`, and `Thursday the 27` as rank-2
day-of-month dates. It chooses the current month when that day has not passed,
otherwise the nearest future month. A leading correction marker in
`No Thursday the 27` is not treated as negating the newly supplied ordinal.

## Lane-40 exception

Departure/availability sentences are the intentional exception. For example,
`leaving town today, back in 2 weeks` describes departure and return; the return
date is the actual availability date. It overrides `from='in 2 weeks'` even
though both inputs rank 2. This exception is explicit in the override seam and
wins regardless of rank.

Lane-46 anaphora still runs before the specificity gate. `What about Monday that
week?` defers to the pathway-resolved `monday the week of 08/18/2026`, yielding
08/17/2026.

## Offline proof tail

```text
CASE=explicit-beats-weekday FROM=2026-08-27
CASE=ordinal FROM=2026-08-27
CASE=away-exception DATE=2026-08-18
CASE=anaphora FROM=2026-08-17
```

## Suite tails

Lane-46 tree with the fixed gateway installed:

```text
20 passed, 240 warnings in 0.17s
```

Cumulative lane-44b tree with the fixed gateway installed:

```text
85 passed, 33 warnings, 27 subtests passed in 0.58s
```

Warnings are the pre-existing Python day-without-year `strptime` deprecation.

## Release boundary

This lane produced and verified local artifacts only. Deployment, image build,
line binding, and live probes are separately gated and were not performed.
