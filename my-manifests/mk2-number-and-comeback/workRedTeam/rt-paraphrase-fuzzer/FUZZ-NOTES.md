# Mott intent-routing fuzz notes

## Source audit

The draft contains 64 unique edge labels. Thirty-one are patient-language routing labels. Thirty-three are state, webhook, reconciliation, delivery, or timeout conditions. Patient turns can exercise the former; the latter require controlled fixtures or elapsed time. Treating `slot_count == 0`, for example, as a paraphrase class would give false coverage because wording cannot guarantee inventory.

The 37 reconciled scenarios were compared by both name and normalized turn text. This corpus avoids their exact patient turns and pushes beyond their main forms with slang, misspellings/run-ons, implicit references, numeric clocks, competing clauses, and calendar arithmetic.

## Patient-language taxonomy and scenario mapping

Each label below has at least two non-obvious mapped scenarios. Several scenarios intentionally cover more than one label.

| Exact edge label | Fuzz scenarios |
|---|---|
| `says any day, weekday, date, week, weekend, or time preference - including Saturday, this weekend, next week, or a month and day - or asks for the first available, soonest, earliest, or whenever opening - or gives only a time preference when no date has been offered yet - including agreement-phrased times like 3pm works for me when no opening has been offered yet` | `weekend-ish-whenever`, `end-next-month`, `day-after-tomorrow-late-morning`, `first-thing-not-first-choice`, `after-one-unsuffixed` |
| `asks for a time near, around, or close to a specific clock time` | `around-five-unsuffixed`, `near-tenish`, `quarter-past-three`, `numeric-nine-thirty` |
| `wants late, latest, last appointment, or end of day` | `latest-sometime-next-week`, `closing-time-friday` |
| `after an opening has been offered, gives only a time preference on the already offered date, excluding late, latest, last appointment, or end of day - or asks for the earliest, soonest, or first available time on that date` | `offered-day-after-one`, `offered-day-earliest` |
| `after an opening has been offered, wants late, latest, last appointment, or end of day on the offered date` | `offered-day-latest-slang`, `offered-day-last-appt` |
| `names a specific clock time to take, including bare digit forms like 1115, 11 15, or 11:15, rather than replying 1 or 2` | `named-offered-clock-colon`, `named-offered-clock-runon`, `named-offered-clock-spaced` |
| `takes only the first opening offered, including by naming that opening's clock time` | `choose-earlier-words`, `choose-top-option`, `named-offered-clock-colon` |
| `takes only the second opening offered, including by naming that opening's clock time` | `choose-later-words`, `choose-bottom-one` |
| `takes the opening offered, including replying 1, yes, or naming its clock time` | `decline-single-anchor-offer`'s preceding anchor selection context, `single-offer-latest-switch`'s preceding anchor context; direct safe selection equivalents are `named-offered-clock-colon` and `named-offered-clock-spaced` |
| `confirms they want the first offered opening, including by naming its clock time` | `choose-earlier-words`, `choose-top-option` |
| `confirms they want the second offered opening, including by naming its clock time` | `choose-later-words`, `choose-bottom-one` |
| `both selects an opening and asks for a different day or time` | `mixed-earlier-but-wednesday`, `mixed-later-plus-after-four`, `mixed-clock-or-next-week`, `mixed-take-it-search-late`, `mixed-bottom-but-not-date`, `mixed-sure-but-around-three` |
| `corrects or replaces the offered date with a different specific day, date, or weekday - including replies beginning with no, actually, or I meant` | `correction-no-week-after`, `correction-meant-twentyseventh`, `correction-not-this-monday`, `correction-date-time-runon` |
| `states a NEW day, date, week, or time preference different from the offered date` | `same-week-anaphora-tuesday`, `monday-in-that-week-colloquial`, `correction-no-week-after` |
| `states a new day, date, or time preference` | `single-offer-new-preference`, `correction-date-time-runon` |
| `wants a different day, date, or time than the one offered` | `decline-both-new-time`, `single-offer-new-preference` |
| `says no or wants other times` | `decline-current-offer-soft`, `gate-mismatch-clock` |
| `declines both choices` | `decline-both-new-time`, `decline-both-no-preference` |
| `declines this offer` | `decline-single-anchor-offer`, `single-offer-new-preference` |
| `declines scheduling` | `decline-scheduling-now`, `decline-scheduling-cant-commit` |
| `opt-out language` | `optout-lose-my-number`, `optout-no-more-pings` |
| `patient asks to speak to someone` | `human-call-me-instead`, `human-front-desk` |
| `patient does not provide any usable day, weekday, or date` | `ambiguous-that-weekend`, `ambiguous-next-one`, `ambiguous-eleven` |
| `patient provides any usable day, weekday, or date, including either conflicting option or a new replacement date` | `clarify-then-usable-relative`, `clarify-then-usable-month-end` |
| `the patient names a date or time that does not match the opening being confirmed` | `gate-mismatch-date`, `gate-mismatch-clock` |
| `wants a different day, date, or time than the one offered` | `correction-not-this-monday`, `decline-current-offer-soft` |
| `change requested after confirmation` | Not safely reachable in a 2-4 patient-message sequence without completing a real booking. Nearest fail-closed pre-booking probes: `gate-mismatch-date`, `gate-mismatch-clock`. |
| `anything else requested after booking` | Not safely reachable without completing a real booking. Human-support paraphrases are isolated in `human-call-me-instead`, `human-front-desk`. |
| `confirms yes to the first opening` | The safe, non-banned confirmation paraphrases would be `go ahead and book that earlier one` and `lock in the first one`; omitted as live-booking actions because the deliverable has no booked outcome kind. |
| `confirms yes to the second opening` | The safe, non-banned confirmation paraphrases would be `go ahead with the later one` and `lock in the bottom option`; omitted as live-booking actions because the deliverable has no booked outcome kind. |

## State and webhook edge taxonomy

These exact labels are enumerated for completeness. They cannot honestly be guaranteed twice by paraphrasing alone; they need fixture controls, gateway stubs, delivery outcomes, or elapsed time.

- Timing/delivery: `72-hour silence after booking`, `72-hour timeout`, `confirmation delivered`, `office direction delivered`.
- Identity/input gates: `recall_cell == `, `recall_patient_id == `, `store == `, `conflict_reason != `, `date_conflict_detected == conflict`, `from_unresolved == true`.
- Availability/search results: `ok != true`, `out_of_hours == true`, `slot_conflict == `, `slot_conflict == false`, `slot_conflict == true`, `slot_count == 0`, `slot_count == 1`, `slot_count >= 1`, `slot_count >= 2`, `anchor_exact == true`, `anchor_exact != true`.
- Generic branch counts: `count == 0`, `count == 1`, `count >= 2`.
- Booking/reconciliation: `appt_count == 0`, `appt_count >= 1`, `book_error == slot_conflict`, `book_success == true`, `book_success != true`, `recon_count == 0`, `recon_count >= 1`, `recon_ok != true`.
- Suppression: `suppression_ok == true`, `suppression_ok != true`.
- Conflict retry: `after the one allowed re-ask, always continue to search using the best extracted date; never remain on this node`.

The `honest_miss` cases (`at-seven-unsuffixed`, `out-of-hours-midnight`, `out-of-hours-seven-evening`) are wording probes for the out-of-hours response, but actual `out_of_hours == true` coverage still depends on the gateway fixture. Likewise, all `offer` versus `single_offer` expectations depend on controlled slot inventory for exact response-path coverage.

## Coverage checks

- 65 scenarios total.
- All sequences contain 2-4 patient messages and start with `hi`.
- No turn is exactly `1`, `2`, `yes`, or `YES`.
- Six explicit two-intent messages: all scenarios prefixed `mixed-`.
- At least four ask-before-act probes: `ambiguous-that-weekend`, `ambiguous-eleven`, `ambiguous-next-one`, `conflicting-weekday-date`, and `conflicting-correction-still-conflicts`.
- Numeric and relative forms include `930`, `445`, `1045`, `11 15`, day after tomorrow, a week from Friday, fortnight, return in 11 days, same-week anaphora, and end of next month.
