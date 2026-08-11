# Mott lane 39 relative-date parser fix

## Defect

On 2026-08-04, production `/availability` resolved `in 2 weeks` correctly but did not recognize `2 weeks from today`, `two weeks from today`, or bare `2 weeks`. The downstream date handling could therefore retain the anchor word `today` or pass an unresolved phrase to the CLI, producing same-day availability or HTTP 409.

## Parser location

- `/availability` enters date normalization in `gw/container/bland_gateway.py:2190-2200` (`build_argv` calls `clamp_availability_range`).
- `from` and `to` are resolved in `gw/container/bland_gateway.py:1668-1700`.
- The phrase parser is `resolve_relative_date` in `gw/container/bland_gateway.py:610-778`.
- The new relative-offset precedence block is `gw/container/bland_gateway.py:639-667`.

## Change

Added one full-match relative-offset rule before simple anchor words. It accepts numeric and small spelled-out counts for singular/plural days, weeks, and months, including:

- `N unit(s) from today|now`
- `in N unit(s)`
- bare `N unit(s)`
- the already-working `... from now` and `... out` forms

Days and weeks use `timedelta`. Months preserve the store-timezone day where possible and clamp to the last valid day in shorter months. The parser still obtains `today` from `_eastern_today()`, so the offset is based on the store timezone. Existing branches for `today`, `tomorrow`, weekdays, following weekdays, explicit dates, yearless month-day forms, and other vocabulary remain in place.

Regression coverage is in `gw/tests/test_bland_gateway.py:206-223`, with `_eastern_today` injected as 2026-08-04. It covers all requested phrases and expected dates.

`proof_parse.py` imports the real parser from `./gw`, uses the real current Eastern date, accepts argv phrases, and performs no network calls.

## Snapshot prerequisites discovered

The copied snapshot was not independently test-runnable as supplied:

1. `container/bland_gateway.py` and the Dockerfile reference `container/eyecloud_capabilities.v1.json`, but the file was absent from both the copied working tree and its `HEAD`. A minimal manifest matching the existing `insurance.get` tests was restored locally at that required path.
2. `tests/test_webhook_capabilities.py` expected empty, unpadded availability slots even though the deployed source explicitly pads to two slots and adds `day_name`. Those stale assertions were aligned with the deployed behavior. No gateway availability-envelope behavior was changed.
3. Root-level `test_id_pinned_search_regression.py` says it is deliberately written to fail against the current gateway and is not part of the maintained `tests/` suite. It also resolves `container/bland_gateway.py` from the parent of `gw`, so collecting it from this copied layout fails before any assertion runs. It remains unchanged. `gw/pytest.ini` now points normal pytest discovery at the repository's existing `tests/` layout, making `python3 -m pytest -q` the full maintained-suite command while leaving the separate patient-search diagnostic available when explicitly named.

## Verification

Focused parser tests:

```text
$ cd gw && python3 -m pytest -q tests/test_bland_gateway.py -k 'RelativeDateResolutionTests'
.......                                                          [100%]
7 passed, 24 deselected, 18 warnings, 8 subtests passed in 0.18s
```

Full maintained test suite:

```text
$ cd gw && python3 -m pytest -q
................................................................ [ 91%]
......                                                                   [100%]
70 passed, 21 warnings, 8 subtests passed in 0.82s
```

Standalone proof using the real current date (2026-08-04 Eastern):

```text
$ python3 proof_parse.py
PHRASE=2 weeks from today DATE=2026-08-18
PHRASE=two weeks from today DATE=2026-08-18
PHRASE=in 2 weeks DATE=2026-08-18
PHRASE=2 weeks DATE=2026-08-18
PHRASE=10 days from now DATE=2026-08-14
```

Diff hygiene:

```text
$ git -C gw diff --check
(no output; exit 0)
```

## Deployment boundary

Deploy is deliberately **not** part of this task. All changes are local and uncommitted for coordinator review. No network, commit, push, or deploy action was performed.
