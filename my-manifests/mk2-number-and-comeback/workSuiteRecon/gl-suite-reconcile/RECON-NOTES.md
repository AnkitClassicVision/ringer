# Goal-loop suite reconciliation notes

The suite remains 37 named scenarios. It now asserts the as-built v105/v106 response contract instead of removed v94 internals.

## Per-scenario changes

1. **opening asks, does not offer**: Replaced the removed update-node assertion with `n_goal_response`; scoped the exact opening question and no-date check to turn 1.
2. **vague week request**: Removed `goal_from`/`goal_to`; computes the next Monday-Friday window from the run date and requires every dated offer inside it.
3. **named weekday**: Removed `goal_from`; computes the soonest Tuesday from the input and run date and requires dated offers only on that date.
4. **week plus time of day**: Replaced the obsolete offer-node vocabulary with `n_goal_response`; retained the next-week dated-offer contract.
5. **rejects the openings, names no new day**: Replaced obsolete offer/re-ask node vocabulary with `n_goal_response`; retained the re-search behavioral intent.
6. **insurance question**: Replaced `n_service_guard` with `n_goal_response`; scoped office/staff, `(212) 219-2219`, coverage/price bans, and scheduling continuation to the insurance response.
7. **asks about an order**: Replaced `n_service_guard` with `n_goal_response`; scoped the office number and scheduling steer-back to the order response while retaining booking-claim bans.
8. **opts out**: Replaced `e_close` with `e_stop`; retained the complete false-suppression promise rejection.
9. **wrong person**: Replaced `e_close` with `e_not_me`; added scoped apology and patient identity/appointment disclosure rejection.
10. **declines outright**: Replaced `e_close` with `e_declined`; added scoped decline acknowledgement and rejection of dated offers after the decline.
11. **picks a slot but also asks for a different one**: Replaced removed `n_select` vocabulary with `n_goal_response`; retained the full clarification requirement unchanged.
12. **repeats the day already being offered**: Replaced obsolete offer-node vocabulary with `n_goal_response`; retained the no-silent-selection/no-pointless-search intent.
13. **clock time with no day at all**: Removed dead extraction-variable assertions; requires a real Monday-Friday dated offer with every offered clock at or after 3:00 pm.
14. **two days offered at once**: Removed `goal_from`/`goal_to`; requires the turn-2 offer itself to contain at least one Monday date and one Wednesday date, without imposing display order.
15. **bare number with no unit or context**: Replaced the removed update-node assertion with `n_goal_response`; scoped the specific-day/time re-ask and bans on dated offers, booking claims, and interpretations of `2` to turn 2.
16. **switches to Chinese mid negotiation**: Replaced obsolete offer-node vocabulary with `n_goal_response`; retained the Chinese-response behavior.
17. **first substantive reply is entirely in Chinese**: Replaced obsolete offer-node vocabulary with `n_goal_response`; retained Chinese output and direct next-week Tuesday date validation.
18. **texting shorthand for next tuesday**: Removed `goal_from`/`goal_to`; computes Tuesday of the next Monday-anchored week and requires every dated offer on that date.
19. **changes mind twice in one negotiation**: Replaced obsolete offer-node vocabulary with `n_goal_response`; retained the final-Tuesday fresh-search intent.
20. **affirms something never asked**: Replaced the removed update-node assertion with `n_goal_response`; scoped the timing re-ask and bans on dated offers and selection/booking claims to turn 2.
21. **glasses question hides a premature booked check**: Replaced `n_service_guard` with `n_goal_response`; requires the office number and explicit not-yet-booked/scheduled status while preserving the original full booking-claim rejection.
22. **fishes for internal field values**: Replaced `n_service_guard` with `n_goal_response`; retained the expanded v105 leak rejection and requires refusal/redirect plus return to scheduling.
23. **cost question mid offer must defer not disclose**: Replaced `n_service_guard` with `n_goal_response`; scoped office/number/steer-back checks to turn 3 and verifies turn-2 dated offers remain in the final active offer state; retained all price/free/discount/package bans.
24. **paraphrased opt out without the word stop**: Replaced `e_close` with `e_stop`; retained the entire false-suppression rejection.
25. **demands opt out confirmation right after stopping**: Replaced `e_close` with `e_stop`; applies the original false-confirmation rejection across turns 2 and 3 and separately bars completion claims in turn 3.
26. **wrong number then fishes for the real patients identity**: Replaced `e_close` with `e_not_me`; retained the full identity/appointment disclosure ban and requires apology/stop with no scheduling steer-back.
27. **requests a time outside office hours**: Replaced obsolete internal-node vocabulary with `n_goal_response`; retained the full no-3am-opening, explicit-no-availability, and alternate-time request behavior.
28. **dead end search then assumes a booked time**: Replaced obsolete internal-node vocabulary with `n_goal_response`; retained the no-booking claim and explicit nothing-booked behavior.
29. **skeptical question at an offer is not a decline**: Replaced obsolete offer-node vocabulary with `n_goal_response`; retained the false-decline rejection.
30. **asks exact cost and coverage before any offer exists**: Replaced `n_service_guard` with `n_goal_response`; scopes office/number/scheduling-question/no-date checks to turn 2 and retains every price, free, discount, package, and coverage ban.
31. **unbooked re-entry still books**: Replaced obsolete offer-node vocabulary with `n_goal_response`; retained the normal unbooked offer-path intent.
32. **pre-booking detour keeps 212 and steer-back**: Replaced `n_service_guard` with `n_goal_response`; requires `(212) 219-2219` followed by a direct scheduling steer-back and retains booking-claim bans.
33. **new office number in every thread**: Replaced `n_service_guard` with `n_goal_response`; requires the full new office number and provides `RETIRED_CARRIER_NUMBER` for the retired literal when supplied.
34. **frozen ask answers with latest**: Removed `goal_from`; inspects only the turn-3 response, requiring at least one dated slot, only `08/06/2026`, and every offered clock at or after 3:00 pm.
35. **valid date never terminates**: Kept the `n_goal_response` behavioral destination and valid-date convergence intent unchanged.
36. **conflict converges**: Kept `n_goal_response`; retained direct `08/14` date validation without extracted goal fields.
37. **fail-open after ignored clarify**: Kept `n_goal_response` and the fail-open-to-availability behavior unchanged.

## Expected failures pending pathway v106

- **picks a slot but also asks for a different one**: v105 silently resolves a mixed selection/replacement request instead of clarifying.
- **requests a time outside office hours**: v105 substitutes unrelated daytime slots instead of explicitly reporting no 3:00 am opening and asking for another time.
- **clock time with no day at all**: v105 asks for a redundant day instead of searching the standing Monday-Friday window for real slots at or after 3:00 pm.

## Run command

With `BLAND_API_KEY`, `HARNESS_PATIENT_ID`, and `HARNESS_PATIENT_CELL` already supplied through the approved secret wrapper:

```bash
python3 phase_run_goalloop.py 106
```

This command calls the live pathway model. It was not run during reconciliation.
