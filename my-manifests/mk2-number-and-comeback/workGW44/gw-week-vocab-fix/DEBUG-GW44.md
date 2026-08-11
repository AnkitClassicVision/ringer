# GW44 weekday-qualified week vocabulary

## Evidence

- Production-equivalent base: `deployed-bland_gateway.py` (provided as byte-equal to lane 43).
- Measured defect: `monday next week` was unresolved and the availability request used its existing fallback window.
- Read-only harness reference: `pathway_harness.py` resolves a qualified weekday from the Monday of the next calendar week.
- No network, git, MCP, deployment, or external write was used.

## Change

- `fixed-bland_gateway.py:642` resolves a date phrase used as a Monday-anchored week.
- `fixed-bland_gateway.py:760` adds qualified `week of`, `next week`, and `this week` weekday forms. Context-dependent `that week` / `same week` forms remain unresolved.
- `fixed-bland_gateway.py:1772` marks explicit unresolved availability date text with the internal `from_unresolved` signal while preserving the existing fallback behavior.
- `fixed-bland_gateway.py:3131` removes that internal signal before CLI execution, and `fixed-bland_gateway.py:3445` exposes `result.from_unresolved=true` in a successful availability response.
- `gwtest/tests/test_bland_gateway.py:226` adds frozen-date vocabulary and regression coverage, including the response field and none/empty default behavior.
- `proof_week.py` is an offline standalone proof. Its four weekday-qualified cases inject `2026-08-04`; only the two-week regression reads the real Eastern date.

The installed cumulative-suite copy is byte-equal to the deliverable:

```text
CMP_FIXED_INSTALLED=0
```

## Proof output

```text
CASE=monday-next-week DATE=2026-08-10
CASE=monday-week-of DATE=2026-08-17
CASE=monday-week-of-18th DATE=2026-08-17
CASE=friday-this-week DATE=2026-08-07
CASE=regression-2weeks DATE=2026-08-18
```

## Full configured suite output tail

Command: `cd gwtest && python3 -m pytest -q`

```text
................................................ [ 58%]
..................................               [100%]
82 passed, 24 warnings, 24 subtests passed in 0.52s
```

The warnings are the suite's existing Python 3.14 yearless-date deprecation warnings. Syntax compilation also passed for the fixed gateway, installed suite gateway, and proof script.

## Deployment gate

Deployment was not performed. Promotion of `fixed-bland_gateway.py`, line/version binding, and live verification are separately gated coordinator/operator actions.
