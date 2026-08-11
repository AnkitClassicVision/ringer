# GW40: authoritative availability sentence semantics

## A/B evidence

Production was probed immediately before this lane against `/availability`, holding the explicit request field constant at `from="in 2 weeks"`:

- `user_text="in 2 weeks"` returned 08/18/2026 slots.
- `user_text="I'm leaving town today and won't be back for 2 weeks about then?"` returned 08/04/2026 slots.

This isolates the remaining fault to the gateway's authoritative free-text interpretation. The pathway extraction was already sending the correct explicit `from`; no precedence change is part of GW40.

## Authoritative interpreter path

Locations in `fixed-bland_gateway.py`:

- Lines 1477-1547: `clamp_availability_range()` reads authoritative `user_text`, selects the current message, and calls `resolve_from_conversation()`.
- Lines 1338-1373: `resolve_from_conversation()` passes the latest user sentence to `extract_date_from_text()`.
- Lines 925-1313: `extract_date_from_text()` interprets dates from free text. Its general scanner previously selected the departure word `today` from the canonical sentence.
- Lines 1691-1693: a deterministic raw-text result overwrites both `body["from"]` and `body["to"]`, which explains why the explicit `from` lost the A/B probe.

## Change

Lines 968-991 add a departure/unavailability pre-pass inside `extract_date_from_text()`:

- It activates only for departure/unavailability constructions such as leaving, going away, out of town, gone, return, and not-back/not-around/not-available language.
- `until <date>` sends only `<date>` back through the existing sentence date interpreter. This preserves the established ordinal, explicit-date, weekday, and relative-date rules.
- `(for|in) N days/weeks/months` sends the captured duration to the existing `resolve_relative_date()` offset logic. Offset arithmetic is not duplicated.
- A detected departure construction without a resolvable return period returns no authoritative date, so its departure date cannot be selected.
- Sentences without a departure construction continue directly into the unchanged existing parser.

The production-equal base remains untouched as `deployed-bland_gateway.py`. The candidate is `fixed-bland_gateway.py`, and it is byte-equal to `gwtest/container/bland_gateway.py`.

## Tests and proof

Focused tests, from `gwtest/`:

```text
$ python3 -m pytest -q tests/test_availability_semantics.py
..                                                               [100%]
2 passed, 17 warnings, 8 subtests passed in 0.15s
```

Full copied lane-39 suite, from `gwtest/`:

```text
$ python3 -m pytest -q
................................................... [ 69%]
......................                                                   [100%]
73 passed, 38 warnings, 21 subtests passed in 0.51s
```

The 38 warnings are the suite's existing Python date-parsing deprecation warnings. There are no test failures.

Standalone proof, from this directory:

```text
$ python3 proof_intent.py
CASE=away-sentence DATE=2026-08-18
CASE=until-18th DATE=2026-08-18
CASE=gone-10-days DATE=2026-08-14
CASE=plain-today DATE=2026-08-04
CASE=thursday DATE=2026-08-06
```

Additional checks:

```text
$ cmp -s fixed-bland_gateway.py gwtest/container/bland_gateway.py
SCRATCH_GATEWAY_BYTE_EQUAL=yes
$ python3 -m py_compile fixed-bland_gateway.py proof_intent.py gwtest/tests/test_availability_semantics.py
# exit 0
```

## Gate

No network access, deploy, commit, push, MCP/App/skill action, or production write was performed. Deployment is separately gated.
