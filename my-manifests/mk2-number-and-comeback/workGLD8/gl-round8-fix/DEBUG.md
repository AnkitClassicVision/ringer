# Goal-loop round 8

## Scope

Round 8 repairs three defects measured on the live v103 Mott line. It preserves the round-7 gateway contract, frozen v96 scheduling extractors, direct user-wait-to-webhook topology, retry and skip settings, and booking reconciliation outcomes.

## Measured defects

1. Established-date clobber: after Tuesday 08/18/2026 openings were offered, the day-less question `What's the latest time I can come in?` re-extracted a bare `tuesday`. The gateway resolved the nearer Tuesday 08/11, losing the explicit offered date.
2. Clock-time gate mis-pick: with `05:15 pm` offered first and `05:00 pm` second, `Let's do 515` routed to `n_gate_2`. The two choice-edge labels described only first versus second and gave the router no clock-time cue.
3. Booked-message mismatch: the shared `n_confirm` had no branch-specific slot template. It generated `booked for 05:15 pm` after `n_book_2` had actually booked `05:00 pm`.

## Changes

- Added `n_goal_search_offered_latest`, cloned from the availability search with `from` and `to` both exactly `{{slot_1_start}}` and `time_pref` set to `latest`.
- Added `n_goal_search_offered_time`, with the same offered-date pins, `time_pref` set to `none`, and `after` left as `{{time_after}}`.
- Added the proven offered-date routing labels from `n_goal_response`. The generic latest route now applies only to a named day different from the offered date, preventing overlap with the offered-date latest route.
- Appended `including by naming that opening's clock time` to both choice-gate labels so a reply such as `515` can resolve against the actual offered clocks.
- Replaced shared `n_confirm` with `n_confirm_1` and `n_confirm_2`. Each Default node uses template-verbatim patient copy containing only its own `slot_N_day_name` and `slot_N_start`, plus the existing MK2 Optical phone close. Each book-success responsePathway and edge targets its matching confirm. Both confirms retain the former booked, silence, change-request, and other-request outcomes.
- Added validator assertion 8 for the offered-date request bodies and routes, the clock-time gate clause, the confirmation split, branch-specific templates, and book-success wiring. Assertions 1 through 7 remain active.

## Regeneration

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
```

`build_goalloop.py --fixtures` deterministically rewrites the draft, the conformant and mutation fixtures, and `fixture-v96-n-ask-extractors.json` from source copies stored in this directory.
