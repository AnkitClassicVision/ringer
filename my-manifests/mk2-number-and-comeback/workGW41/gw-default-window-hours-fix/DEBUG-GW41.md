# GW41 default-window and out-of-hours evidence

## Baseline failure

Measured against production `/availability` immediately before this lane:

- `from="none"` or an empty `from` returned HTTP 409 with `bad --from: unrecognized date none`.
- With a valid date, `after="03:00 am"` admitted the day's ordinary daytime slots and provided no signal that 3am was outside the slot-derived operating bounds.

The production-byte-equal baseline is `deployed-bland_gateway.py`. No network or production call was made in this worktree.

## Code locations and change

- `fixed-bland_gateway.py:1477`: `clamp_availability_range` owns availability date normalization.
- `fixed-bland_gateway.py:1719`: literal `none`, empty, or absent `from`/`to` now resolves to Eastern today through today + 13 days. Explicit parseable ranges retain the old path; genuinely unparseable values retain the old refusal/collapse behavior.
- `fixed-bland_gateway.py:2425`: extracts an operative `after`, `before`, or `time_pref` anchor clock.
- `fixed-bland_gateway.py:2439`: derives bounds only from the earliest returned slot start and latest returned slot end.
- `fixed-bland_gateway.py:2460`: adds `out_of_hours`; `requested_clock` is emitted only when true.
- `fixed-bland_gateway.py:3315`: the `/availability` response path annotates the normal slot envelope. If a clock filter returns zero slots, one unfiltered read of the same date window supplies real bounds and real alternative slots. Hours are not hardcoded and no slot is invented.

`gwtest` is a copy of the requested GW39b gateway tree with `fixed-bland_gateway.py` installed as `container/bland_gateway.py`. New tests are in `gwtest/tests/test_default_window_out_of_hours.py`.

## Verification

Focused test:

```text
$ pytest -q tests/test_default_window_out_of_hours.py
....                                                                  [100%]
4 passed, 3 subtests passed in 0.18s
```

Full copied suite tail:

```text
$ pytest -q
........................................................ [ 74%]
...................                                                      [100%]
75 passed, 21 warnings, 16 subtests passed in 0.50s
```

The 21 warnings are the existing Python date-without-year deprecation warning at gateway line 760.

Standalone proof, run on the real Eastern date with no network:

```text
$ python3 proof_window.py
CASE=default-window FROM=2026-08-04 TO=2026-08-17
CASE=oob-flag OUT_OF_HOURS=true REQUESTED=03:00 am
```

The default-window case exercises the real resolver clock. The out-of-hours case is offline-testable because the flagging code is a pure comparison against injected representative slot boundaries; it does not claim those fixture slots are live availability.

Syntax verification:

```text
$ python3 -m py_compile fixed-bland_gateway.py proof_window.py gwtest/container/bland_gateway.py
(no output; exit 0)
```

## Gate state

Local artifacts and tests only. Deployment, image publication, line changes, commits, and production verification are separately gated and were not performed.
