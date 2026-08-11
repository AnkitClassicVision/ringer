# GW50 context-date and anchor-route fix

CANARY: blue paperclip

## Evidence

- Base: `deployed-bland_gateway.py`, supplied as byte-equal to production image `mott-lane-49`.
- Ringer deliverable: `fixed-bland_gateway.py`, byte-equal to the tested base and `gwtest/container/bland_gateway.py`.
- Fixed test image: `gwtest/container/bland_gateway.py` is byte-equal to the fixed base file.
- Offline proof: `python3 proof_context.py` prints all six required contract lines.
- Regression suite: `cd gwtest && python3 -m pytest -q` reports `90 passed, 33 warnings, 27 subtests passed in 0.62s`.
- The warnings are pre-existing Python date-parser deprecation warnings at line 826; no test failed.

## Contract 1: `context_date`

`/availability` accepts optional `context_date`. A leading `MM/DD/YYYY` or `YYYY-MM-DD` is parsed even when followed by a clock. Only `that week` / `the same week` anaphora uses this context:

- A weekday plus anaphoric week phrase resolves to that weekday in the context date's Monday-anchored week.
- Bare `from="that week"` resolves to Monday through Friday of that week.
- Missing context, invalid context, and non-anaphoric/self-resolving `from` text retain prior behavior.
- `context_date` is gateway-only and never reaches the CLI.

Code: `deployed-bland_gateway.py:1630-1633` and `deployed-bland_gateway.py:1891-1931`.

## Contract 2: exclusive `anchor_route`

Anchor-form availability requests return exactly one `result.anchor_route`:

- `error`: response `ok` is not exactly `true`.
- `none`: successful response has zero slots.
- `exact`: slots exist and compatibility field `anchor_exact` is exactly `true`.
- `closest`: slots exist and the first slot is not the requested clock.

Non-anchor responses omit the field. Existing `anchor_exact` behavior remains unchanged.

Code: `deployed-bland_gateway.py:2795-2814`, response seam at `deployed-bland_gateway.py:3132-3136`, and request preference capture at `deployed-bland_gateway.py:3301-3304`.

## Output tails

```text
CASE=anaphora-context FROM=2026-08-17
CASE=bare-that-week FROM=2026-08-17 TO=2026-08-21
CASE=route-exact ROUTE=exact
CASE=route-closest ROUTE=closest
CASE=route-none ROUTE=none
CASE=route-error ROUTE=error
```

```text
............................................. [ 50%]
............................................. [100%]
90 passed, 33 warnings, 27 subtests passed in 0.62s
```

## Deployment gate

No network, git, MCP, app, skill, deployment, number rebind, or live action was used. Deployment remains a separate owner-approved action.
