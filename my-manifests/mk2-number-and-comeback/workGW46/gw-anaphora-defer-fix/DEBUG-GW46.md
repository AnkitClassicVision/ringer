# GW46: defer authoritative `user_text` on unanchored anaphora

## Evidence and decision

Production-equivalent lane 45 behavior parsed `What about Monday that week?` as the bare weekday `08/10/2026`, then replaced the pathway's context-aware `from=monday the week of 08/18/2026`. The latter resolves directly to `08/17/2026`.

The decision point is `fixed-bland_gateway.py:1648-1649` (classify the current text), `:1680-1684` (do not invoke the authoritative LLM fallback), and `:1759-1762` (do not write deterministic `raw_from/raw_to` over the pathway fields).

The defer predicate is at `fixed-bland_gateway.py:1395-1421`. It requires one of:

- `that week`
- `the same week`
- `that day`
- `those days`
- `the week we discussed`
- `the week we talked about`

It defers only when the same sentence has no absolute anchor: numeric date, month-day, ordinal day, weekday with a `this`/`next`/`following week` qualifier, relative day/week/month offset, or today/tomorrow anchor. Anchored sentences retain lane-40 authoritative behavior.

## Verification

Commands were run offline from this directory:

```text
$ python3 -m py_compile fixed-bland_gateway.py proof_defer.py
exit 0

$ python3 proof_defer.py
...
CASE=anaphora-week FROM=2026-08-17
CASE=anaphora-day FROM=2026-08-17
CASE=away-override DATE=2026-08-18
```

`proof_defer.py` freezes today at `2026-08-04` and calls `clamp_availability_range`, the handler-level resolution seam. It also asserts that `No I said two weeks not today` resolves to `2026-08-18`, and checks all six anaphora patterns plus anchored counterexamples.

## Local suite status

The external lane-44b directory was not read because this task forbids work outside the CWD. A self-contained `./gwtest` harness now installs `fixed-bland_gateway.py` as `gwtest/bland_gateway.py` and exercises the same `clamp_availability_range` handler-level seam.

```text
$ cd gwtest && python3 -m pytest -q
...............                                                          [100%]
15 passed, 177 warnings in 0.15s
```

The warnings are the gateway's pre-existing Python date-parser deprecation warning; no test failed.

## Release boundary

Local artifact only. No git, network, deployment, or production action was taken. Deployment remains separately gated.
