# Weekday + Conflict

## Changes

- Added weekday names to the availability summary and every returned slot, with invalid dates mapped to an empty string.
- Added Mott raw-text conflict tuples for distinct surviving date expressions, including weekday descriptions, while preserving negation and correction behavior.
- Added clamp wiring that exposes `date_conflict` without replacing model-derived `from` or `to` values.

## Tests

```text
.......                                                                  [100%]
7 passed, 9 warnings in 0.23s
```

Temporal compatibility check:

```text
CHECK PASSED: flag-off byte-identical to ORIGINAL (153 phrases, computed live); flag-on zero drift on 120 legacy; 12 new month-day phrases resolve; 8 compound phrases resolve; 13 over-broad/malformed inputs stay None; CVC inert under the tenant guard even with the flag on; source diff is additions only.
```
