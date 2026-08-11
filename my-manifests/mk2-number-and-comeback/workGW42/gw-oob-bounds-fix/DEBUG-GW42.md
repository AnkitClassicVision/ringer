# GW42: out-of-hours bounds correction

## Live evidence

Measured against the lane-41 production image before this fix: an availability request with
`from='today'` and `after='03:00 PM'` during the afternoon returned real slots beginning at
`03:30 PM`, but the envelope contained `out_of_hours=true` and
`requested_clock='03:00 PM'`. That flag routes the Mott pathway to its miss branch despite
satisfiable inventory.

## Code location and cause

The decision is in `add_out_of_hours_flag` near line 2460 of `deployed-bland_gateway.py`; its
caller is the `/availability` response path near line 3317. Lane 41 calculated bounds from
`raw_slots`, which was normally the already clock-filtered CLI result. It fetched the same
window without `after`, `before`, and `time_pref` only when that filtered result was empty.
Consequently, a nonempty partial day beginning at 03:30 PM made 03:30 PM appear to be opening
time, and a 03:00 PM request appeared out of hours.

## Change

`fixed-bland_gateway.py` now:

- retains the original clock-filtered slots as `filtered_raw`;
- fetches the full searched window without the request clock filter whenever an operative clock
  is present, using that unfiltered inventory only for operating bounds;
- preserves the lane-41 behavior of returning unfiltered alternatives when a clock-filtered query
  is empty;
- forces `out_of_hours=false` when the original filtered inventory contains a slot satisfying
  `after` or `before`, or a real same-window slot for an anchor;
- keeps `requested_clock` on genuine out-of-hours decisions.

The gateway was installed at `gwtest/container/bland_gateway.py`; `cmp` against
`fixed-bland_gateway.py` returned 0.

## Verification

Focused regression tail:

```text
....                                                                     [100%]
4 passed in 0.15s
```

Full isolated suite tail:

```text
........................................................... [ 78%]
................                                                         [100%]
75 passed, 21 warnings, 13 subtests passed in 0.57s
```

The 21 warnings are the pre-existing Python date-parsing deprecation warning at gateway line 760.

Standalone offline proof output:

```text
CASE=partial-day-3pm OUT_OF_HOURS=false
CASE=3am OUT_OF_HOURS=true
```

`python3 -m py_compile fixed-bland_gateway.py proof_bounds.py
gwtest/tests/test_out_of_hours_bounds.py` also completed successfully.

## Release boundary

This lane produced and verified local artifacts only. Deployment, image minting, and Bland line
binding are separately gated and were not performed.
