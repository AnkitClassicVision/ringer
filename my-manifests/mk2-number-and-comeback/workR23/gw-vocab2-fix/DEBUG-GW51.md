# GW51: meridiem inference and vocabulary round 2

## Result

Local artifact only. The lane-50 gateway was patched in place and copied byte-for-byte to `gwtest/container/bland_gateway.py`. Deployment remains a separate owner gate; no network, deploy, git, or external writes were used.

## Evidence and locations

- `deployed-bland_gateway.py`: expanded English number vocabulary and fortnight resolution in `resolve_relative_date`.
- `deployed-bland_gateway.py`: direct conversational `end of this/next month` detection emits a 24th-through-month-end range.
- `deployed-bland_gateway.py`: `clamp_availability_range` resolves end-of-month windows and context-anchored `the/a week after that` Monday-Friday windows.
- `deployed-bland_gateway.py`: `_clock_minutes` is the shared explicit/bare clock parser. `build_argv`, anchor ordering/labels, and out-of-hours checks use it.
- `fixed-bland_gateway.py`: required Ringer handoff artifact; byte-identical to the tested top-level gateway.
- `gwtest/tests/test_vocab2.py`: frozen-today regression coverage for all new forms.
- `proof_vocab2.py`: standalone offline acceptance output.

## Meridiem rule table

| Input | Resolution |
|---|---|
| Explicit `am`/`pm` | Explicit suffix always wins |
| `midnight`, `12am` | `00:00`; out of hours against normal reference bounds |
| Bare `1` through `7` | Prefer PM when that reading is within reference bounds |
| Bare `8` through `11` | Prefer AM when that reading is within reference bounds |
| Bare `12` | Noon |
| Both readings in bounds | Reading nearest the reference-window midpoint |
| Explicit 24-hour clock such as `14:00` | Preserved as 24-hour time |

## Verification output tails

```text
CASE=around-five ANCHOR=17:00
CASE=at-seven ANCHOR=19:00
CASE=nine-thirty-bare ANCHOR=09:30
CASE=midnight OOB=true
CASE=fortnight DATE=2026-08-19
CASE=eleven-days DATE=2026-08-16
CASE=week-after-that FROM=2026-08-24
CASE=end-next-month WINDOW=true
```

```text
............................................. [ 49%]
.............................................. [100%]
91 passed, 33 warnings, 27 subtests passed in 0.61s
```

The warnings are the pre-existing Python date-without-year deprecation warning in the legacy suite. Syntax compilation passed. `cmp` and SHA-256 confirmed `fixed-bland_gateway.py` is byte-identical to `deployed-bland_gateway.py`; the tested suite gateway remains byte-identical as well.
