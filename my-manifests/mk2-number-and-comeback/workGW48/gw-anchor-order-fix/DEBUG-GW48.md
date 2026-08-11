# GW48: restore anchor slot ordering

## Live probe evidence

The decisive production probe immediately before this lane held store and date fixed at store 711 on 08/07/2026. These three requests returned the same order:

- `time_pref="anchor=11:15 AM"`
- `time_pref="anchor=11:15 am"`
- `time_pref="none"`

All three returned `11:00 am`, `11:15 am`, `11:30 am`, `11:45 am`. Therefore the anchor presentation branch was not taking effect. No network probe was repeated in this worker.

## Regression analysis

The most likely regression is the slot-ordering rewrite carried into lanes 41 through 43. The production-equal lane-47 base recognized anchors only with this condition at the old lines 2584-2585:

```python
anchor = re.fullmatch(r"anchor=([01]\d|2[0-3]):([0-5]\d)", pref)
if anchor:
```

That accepts only a zero-padded 24-hour clock such as `anchor=14:00`. It rejects the pathway's `anchor=11:15 AM`, `anchor=11:15 am`, and `anchor=2 pm`. Rejection falls through to `return slots`, now at `deployed-bland_gateway.py:2602`, which explains why both anchor probes were byte-for-byte equivalent in ordering to `none`. The earlier lane-38 evidence could still pass when its anchor happened to be normalized to the strict `HH:MM` shape; the regression is the narrowed input contract at the ordering boundary, not the distance calculation itself.

## Change

`deployed-bland_gateway.py:2584-2601` now:

- recognizes the `anchor=` prefix and parses its clock with the existing tolerant `_clock_minutes()` parser;
- accepts `11:15 AM`, `11:15 am`, `2 pm`, and `14:00`;
- returns the existing input order when the clock is malformed;
- sorts valid slots by absolute minute distance from the anchor, then by earlier clock minute for ties;
- leaves the existing `latest` branch and plain/`none` fallthrough unchanged.

The fixed file is installed byte-equally at `gwtest/bland_gateway.py` and `gwtest/container/bland_gateway.py`.

## Suite construction and counts

The cumulative `gwtest` started as the requested lane-44b copy: 88 files. Two missing lane-47 test modules, `test_anaphora_defer.py` and `test_specificity.py`, were copied beside their lane-47 loader and gateway support files. After adding the four-case GW48 module and test outputs, the working tree contains 99 files. Test-result counts are 4 focused tests and 85 full-suite tests, plus 27 subtests.

The lane-47 loader initially shadowed the cumulative suite's real `capability_registry`, producing 78 passes and 7 harness failures. It was corrected to load `gwtest/container/capability_registry.py`; no gateway behavior was changed for that harness repair.

## Verification tails

Focused test:

```text
$ cd gwtest && python3 -m pytest -q test_anchor_ordering.py
....                                                                     [100%]
4 passed in 0.13s
```

Full cumulative suite:

```text
$ cd gwtest && python3 -m pytest -q
............................................. [ 52%]
........................................                                 [100%]
85 passed, 33 warnings, 27 subtests passed in 0.61s
```

The 33 warnings are existing Python date-parsing deprecation warnings from `tests/test_bland_gateway.py`.

Standalone proof:

```text
$ python3 proof_anchor.py
CASE=anchor-1115 FIRST=11:15 am
CASE=anchor-2pm FIRST=02:00 pm
CASE=latest FIRST=02:00 pm
CASE=none FIRST=11:00 am
```

Compilation and installation checks:

```text
$ python3 -m py_compile deployed-bland_gateway.py proof_anchor.py gwtest/test_anchor_ordering.py
# exit 0
$ cmp -s deployed-bland_gateway.py gwtest/bland_gateway.py
# exit 0
$ cmp -s deployed-bland_gateway.py gwtest/container/bland_gateway.py
# exit 0
```

## Gate

No network, git, MCP/App/skill action, deployment, or production write was performed. Deployment is separately gated.
