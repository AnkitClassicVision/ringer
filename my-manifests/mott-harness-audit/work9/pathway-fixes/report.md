# Scenario Fixes

## Summary

- Added a dedicated clarification route when one reply both selects an opening and requests a different time.
- Added an explicit unsatisfied-time route so an impossible clock request cannot be answered with unrelated openings.
- Normalized weekday texting shorthand and retired two assertions against intentionally removed scheduler fields.

## Fixed

| Failure | Root cause | Change made |
|---|---|---|
| Picks a slot but also asks for a different one | Mixed intent competed directly with clean slot-selection routes, allowing the selected slot to win. | Added `n_which_intent` as the first route from every offer node. It asks whether the patient meant the selected opening or the different request. Only the patient's clarified answer can then reach a confirmation gate or a new search. |
| Requests a time outside office hours | The scheduler ignores time filters, so `3am` was discarded and ordinary openings were presented as matches. | Added the routing-only `outside` classification and routed it before all slot-count offer routes to `n_miss_time`. That node names the miss and asks for another day without showing unrelated openings. |
| Texting shorthand for next Tuesday | Extraction passed `tues nxt wk` verbatim to a scheduler with a closed accepted vocabulary. | Expanded extraction rules for common weekday and week shorthand. The known failing phrase now normalizes to the accepted `tuesday` form instead of reaching the scheduler verbatim. |
| Dead-end search then assumes a booked time | This was downstream of the same substitution path as the `3am` failure. | The `n_miss_time` route also fixes this case. It remains waiting after stating the miss, and its booking prohibition requires it to say that nothing has been booked when challenged. |

## Retired

`week plus time of day` no longer asserts `time_pref`. `clock time with no day at all` no longer asserts `preference_after`, but still checks the legitimate Monday-to-Friday default window and offer landing. Those fields were deliberately removed because the scheduler accepted and ignored them. Restoring or asserting them would encourage values to enter unsupported slots without changing scheduler behavior.

## Nodes Added

- `n_which_intent`: resolves selected-opening versus different-time ambiguity before either confirmation gate.
- `n_miss_time`: states that the requested clock time is unavailable and asks for another day.

## Assumptions

- The live node classifier evaluates outgoing routes in graph order, as relied on elsewhere in this pathway. Mixed-intent and outside-time routes are therefore placed before clean selection and ordinary offer routes.
- `3am` and `11pm` are safely outside normal clinic hours. The new `outside` value is internal routing state only and is never added to the scheduler request.
- Static checks can prove structure but not model classification behavior. The required follow-up is the live 30-scenario run against this graph.
