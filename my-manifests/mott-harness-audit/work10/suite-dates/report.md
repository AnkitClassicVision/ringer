# Suite Upgrade

## Summary

- Preserved all 30 scenarios and upgraded the five assertions governed by reviewer ruling R1.3.
- Added runtime checks for Monday-anchored resolved dates and minimum offered times.
- Made Sunday runs diagnostic-only and non-certifying, even if all scenarios pass.

## Assertions Changed

| Scenario | Binding assertion |
|---|---|
| vague week request | Requires `monday next week` through `friday next week`; offers must fall Monday-Friday of the owner-target week. |
| picks a slot but also asks for a different one | Requires `n_which_intent`; retains the clarification wording regex. |
| clock time with no day at all | Allows only the explicit offer nodes reached by this path and rejects every offered time before 3pm. |
| texting shorthand for next tuesday | Requires `tuesday next week` for both preference fields and the owner-target Tuesday. |
| requests a time outside office hours | Accepts both “don't have” and “do not have,” plus the existing alternatives. |
| other qualified-week cases | Added date targets to week-plus-time, Chinese next-Tuesday, cost-mid-offer, and repeated 3am cases; bare Tuesday uses `soonest`. |

## Runner Capabilities Added

| Capability | Behavior |
|---|---|
| Resolved-date comparator | Parses `MM/DD/YYYY` from `slot_N_start` variables and assistant responses before masking. It computes the target from the runtime date and fails offer dates outside the declared window. |
| Clock-floor comparator | Parses offered am/pm times from slot variables and assistant responses and fails any time below the scenario floor. |
| Missing evidence guard | Offer-node scenarios with a date expectation fail if no offered date is found; floor scenarios fail if no offered time is found. |
| Certification window | Monday-Saturday may certify. Sunday always prints a prominent diagnostic-only warning and exits nonzero. |

## What A Sunday Run Now Does

A Sunday run still executes for diagnosis, but it announces that its temporal results are unrepresentative. Its final exit status is nonzero regardless of whether the result is 30/30, so it cannot be mistaken for certification.

## Assumptions

- `next week` means the following Monday-Friday; `weekday next week` means that weekday in the following Monday-anchored calendar week.
- `soonest` derives its weekday from `expect_vars.preference_from`; a same-day occurrence is eligible.
- A non-offer scenario may legitimately contain no resolved date. If it does expose a date, that date must still satisfy its declared target.
- The harness run date is the machine's local `date.today()`, matching the existing runtime model.
