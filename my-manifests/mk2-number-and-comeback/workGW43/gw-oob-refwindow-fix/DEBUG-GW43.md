# GW43: out-of-hours reference-window bounds

## Evidence

Lane 42 derived clock bounds from the request's own date window, then applied a
satisfiability override. The override cleared `out_of_hours=true` whenever a
returned slot happened to satisfy `after`, `before`, or `anchor`. That made a
03:00 AM request appear in-hours merely because ordinary daytime slots occur
after 03:00 AM.

## Change

- Build an unfiltered reference query for store-local today through today+13.
- Derive earliest start and latest end clocks only from those reference slots.
- Keep the request's date window and clock filtering out of the bounds query.
- Reuse the original unfiltered slot result when its CLI query is byte-for-byte
  the same as the reference query.
- Remove the satisfiability override completely.
- Do not substitute broad reference-window slots into the caller's requested
  result window.

## Offline proof

Command: `python3 proof_ref.py`

```text
CASE=partial-day-3pm OUT_OF_HOURS=false
CASE=3am-after OUT_OF_HOURS=true
CASE=2pm-anchor OUT_OF_HOURS=false
```

The regression suite also covers `before='11:00 pm' -> true` and
`anchor=03:00 -> true` using the same frozen synthetic 10:30 AM through 05:15 PM
reference bounds.

## Verification tails

Command: `python3 -m py_compile fixed-bland_gateway.py proof_ref.py`

```text
exit 0
```

Command: `cd gwtest && pytest -q`

```text
.....                                                       [100%]
77 passed, 21 warnings, 13 subtests passed in 0.53s
```

The 21 warnings are pre-existing Python date-parsing deprecation warnings in
`tests/test_bland_gateway.py`. The installed
`gwtest/container/bland_gateway.py` is byte-equal to
`fixed-bland_gateway.py`.

## Deployment gate

No network, git, deploy, MCP/App, or external write was performed. Deployment
and any live validation remain separately gated.
