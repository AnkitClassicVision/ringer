# GW49: exact anchor availability flag

## Contract

For a valid `time_pref` in the form `anchor=<clock>`, the availability envelope now includes:

- `anchor_exact`: `true` only when the first returned slot's parsed clock equals the parsed requested clock.
- `anchor_requested`: the requested clock normalized as `hh:mm am/pm` (for example, `10:45 am`).

A valid off-grid anchor returns `anchor_exact: false` and preserves the existing nearest-slot-first ordering. A malformed anchor returns `anchor_exact: false` without raising and omits `anchor_requested`. Non-anchor preferences never return `anchor_exact: true`.

No ordering, `out_of_hours`, `from_unresolved`, fallback, or other availability behavior was changed.

## Code location

- `deployed-bland_gateway.py`: `_normalized_anchor_clock`, `_slot_clock_minutes`, and the final envelope assembly in `availability_envelope`.
- `gwtest/tests/test_anchor_exact.py`: frozen-today handler-level `/availability` cases.
- `proof_exact.py`: standalone offline contract proof.

The fixed gateway is installed at `gwtest/container/bland_gateway.py`.

## Verification output tails

`python3 proof_exact.py`:

```text
CASE=exact ANCHOR_EXACT=true FIRST=10:45 am
CASE=offgrid ANCHOR_EXACT=false
CASE=latest ANCHOR_EXACT=false
CASE=none ANCHOR_EXACT=false
```

`python3 -m pytest -q gwtest/tests/test_anchor_exact.py`:

```text
.....                                                                    [100%]
5 passed in 0.17s
```

Full suite, run from `./gwtest` so its frozen `pytest.ini` collection rule applies:

```text
............................................. [ 50%]
.............................................                            [100%]
90 passed, 33 warnings, 27 subtests passed in 0.59s
```

The warnings are the suite's existing Python date-parsing deprecation warnings.

## Release gate

This directory contains local artifacts and passing offline tests only. Deployment, line/version changes, and other production actions remain separately gated and were not performed.
