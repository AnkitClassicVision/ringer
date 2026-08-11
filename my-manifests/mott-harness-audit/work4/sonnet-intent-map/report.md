# Intent Coverage

## Summary

- The two live failures the brief calls out by name — "the latest I can come in" and "later than that on any other day" — are still structurally unfixed in v49: `n_search_late` still slices fixed positions `slots[16]`/`slots[15]`, and no path widens `preference_from`/`preference_to` off the day already searched. Neither has a scenario.
- "Afternoon"/"evening" are the only `time_pref` values that trigger a positional-index webhook leg (`n_search_pm`, `n_search_late`); given the documented gateway defect that `time_pref`/`after`/`before` are accepted and ignored, a thin day can make the graph falsely claim nothing is available. No scenario exercises either value.
- "Earlier than an offered time" has no dedicated edge or node at all — it is the mirror of the one intent (`later`) that got a fix; it silently falls back to `n_negotiate`'s generic re-search, which inherits the multi-field capture problem and a gateway field that is ignored regardless.

## Findings

| # | Intent | Covered by a scenario | Served by the graph |
|---|---|---|---|
| 1 | Day, no time | Yes (`named weekday`, `texting shorthand for next tuesday`) | Yes |
| 2 | Time, no day | Yes (`clock time with no day at all`) | Partial — capture is stochastic |
| 3 | Part of the day | No | No (afternoon/evening) |
| 4 | After/before an hour | Partial (capture only) | Partial — gateway ignores the field |
| 5 | Earliest available | Partial (`skeptical question at an offer is not a decline`) | Yes, by list order |
| 6 | Latest available | No | No |
| 7 | Later than offered | No | No |
| 8 | Earlier than offered | No | No |
| 9 | Different day, unnamed | Partial (`rejects the openings, names no new day`) | Partial — may repeat the rejected day |
| 10 | Any day, time suits | No | Partial — same default mechanism as #9 |
| 11 | Two candidate days | Yes (`two days offered at once`) | Yes |
| 12 | Day practice is closed | No | Yes |
| 13 | Date beyond 14-day window | No | No |
| 14 | Changes mind after choosing | No | Yes (atomic turn / office handoff) |
| 15 | What's available, no commitment | Yes (`picks a slot but also asks for a different one`, `repeats the day already being offered`) | Yes |
| 16 | How busy is a day | No | Yes, if the model self-counts |

### Finding: Afternoon and evening requests route through a positional-index heuristic that can falsely report no availability
Evidence: `n_search` sends `time_pref == afternoon` to `n_search_pm` (reads `slots[8]`/`slots[9]`) and `time_pref == evening` to `n_search_late` (reads `slots[16]`/`slots[15]`). ARCHITECTURE-BRIEF's gateway contract states `time_pref`/`after`/`before` are accepted and then ignored — the gateway always returns the full chronological day list. No scenario sets `time_pref` to `afternoon` or `evening` (only `week plus time of day` sets `morning`, which does not hit this branch).
Impact: on a day with fewer than 9 (afternoon) or 17 (evening) total openings, `slot_1_start` at that index is empty, so `n_search_pm`/`n_search_late` route to `n_reask`, which apologizes and asks for a new day — even when real afternoon/evening openings exist lower in the list. This violates the brief's own rule that no node may claim no availability unless it can actually see that.
Fix: stop gating on a fixed index; either compute the branch from `slot_count` returned per request, or drop the position-8/16 gate entirely and let `n_offer`, which already receives the whole list, do the filtering it already does successfully for other requests.
Priority: P0
Confidence: high

### Finding: "Later than that on any other day" is still unfixed in v49
Evidence: the only outbound edge from `n_offer` for this intent is `edge-n_offer-n_search_late-asks-for-a-later-or-the-last-time-that-day`, and `n_search_late` re-runs `/availability` with the unchanged `preference_from`/`preference_to` from the last search — no step recaptures a wider day range before this call. This is the exact conversation quoted in ARCHITECTURE-BRIEF ("Do have anything later than that on any other day?" → "I only have availability for Tuesday, July 28th").
Impact: a patient asking to widen the day gets an answer scoped to the same single day, repeating the live failure.
Fix: give `n_offer` a distinct edge for "later, and open to other days" that routes through `n_negotiate` (which does recapture `preference_from`/`preference_to`) rather than through `n_search_late`, which never touches those fields.
Priority: P0
Confidence: high

### Finding: "Earlier than an offered time" has no route symmetric to "later"
Evidence: `n_offer`'s outbound edges are only `n_verify`, `n_negotiate`, `e_declined`, `e_timeout`, and `n_search_late`; none of these is worded for "earlier," and no comparable early-side node exists in the graph. An "earlier" ask must fall to `n_negotiate`'s global label ("asks for a different date, time or range"), which re-extracts `preference_before` from free text — and ARCHITECTURE-BRIEF states `before` reaches the gateway and is ignored.
Impact: even a perfect capture of "before 2pm" into `preference_before` produces an identical, unfiltered result from the gateway; the patient is answered from the same list with no actual narrowing, and nothing in the graph tells them that.
Fix: treat "earlier" the same way v49 already treats "later" for the same day — answer from `all_starts`/`all_slots` already in `n_offer`'s own context, since that data is already correct and complete; only fall to `n_negotiate` when a new day is actually named.
Priority: P1
Confidence: high

### Finding: re-searching after a decline can resurface the same rejected day
Evidence: `n_negotiate`'s `preference_from`/`preference_to` extraction defaults to `monday`/`friday` "when in doubt," with no field carrying which day was just declined. Scenario `rejects the openings, names no new day` only asserts `expect_node: ['n_offer', 'n_reask']`, not that the returned openings differ from the ones just turned down.
Impact: "a different day entirely" and "any day at all" (intents 9 and 10) both rely on this same default; a patient who declines Tuesday without naming a new day can be re-offered Tuesday.
Fix: carry the last-declined day/store forward (even as a single variable) and use it as an excluded value in `n_negotiate`'s prompt, or widen the routing so an unqualified "different day" always searches the remaining days in the current window rather than the full default span.
Priority: P1
Confidence: medium

### Finding: the "time with no day" capture is measured stochastic, and the scenario tests only one run
Evidence: MEASURED-EVIDENCE records "after 3pm" landing the literal string in both date fields in earlier runs, and "next week in the morning" failing in 2 of 6 identical runs on version 38. Scenario `clock time with no day at all` runs the equivalent phrasing exactly once and asserts a single expected outcome.
Impact: a scenario suite built from single-shot assertions cannot detect a ~30% capture failure rate; version 49 could still fail this intent at the same rate the brief measured on earlier versions and the suite would report green.
Fix: for any scenario tied to a documented stochastic failure, run it multiple times (the brief's own six-run method) and assert on the failure rate, not a single pass.
Priority: P2
Confidence: high

### Finding: a span wider than the gateway's 14-day cap fails silently into a generic re-ask
Evidence: ARCHITECTURE-BRIEF states spans are capped at 14 days; `n_search`'s only failure edge for a rejected call is `ok != true` → `n_reask`, and `n_reask`'s prompt explicitly forbids mentioning "searching, systems, errors" or naming any day/time-of-day as empty. No scenario sends a wide-span request.
Impact: a patient who names a far-out range gets the same content-free "give me a day" reply as any other failed search, with no signal that the range itself was the problem, which can repeat the same rejected range.
Fix: distinguish a capped-span rejection from a true zero-result search at the routing layer, and have `n_reask` ask for a narrower range specifically in that case.
Priority: P2
Confidence: medium

## Clean

- A day with no time, and two candidate days in one message, both work and are both scenario-covered (`named weekday`, `texting shorthand for next tuesday`, `two days offered at once`).
- A closed day (a real `slot_count == 0`) is handled honestly: `n_search` routes to `n_reask` without inventing an opening, satisfying the brief's non-negotiable rule. It simply has no scenario.
- "Asking what's available without committing" is well covered by the ambiguity scenarios (`picks a slot but also asks for a different one`, `repeats the day already being offered`), which both hinge on the same distinction: `chosen_start` stays empty at `n_offer` until an explicit pick is copied out of `all_slots`.
- "Changing their mind after choosing" has no unsafe window: `n_verify` and `n_book` are silent (`skipUserResponse`) with no user wait in between, so a patient cannot interject mid-write; post-confirmation change requests are explicitly handed to `n_office` rather than re-verified or re-booked, which matches the rule that only `n_confirm` may ever say a booking exists.

## Assumptions

- "Earliest available" is assumed workable because `all_starts` is documented as chronological ("in order, earliest first") and `n_offer`'s prompt reasons over the whole list; no scenario asserts the actual time content returned, so this is inferred from the prompt text and the JSONPath evidence in ARCHITECTURE-BRIEF, not from a passing test.
- "How busy is a day" is assumed servable because `n_offer` holds the full `all_slots` array and could count it, but nothing in the graph or scenarios exercises this, so whether the model reliably does this without leaking an internal count field is unverified.
- `time_pref_relaxed` is captured by `n_search`, `n_search_pm`, and `n_search_late` but is never referenced in any prompt or routing condition found in the graph; its intended purpose could not be confirmed from the provided files.
- Whether `n_negotiate`'s six extraction fields fail at the same rate on v49 as measured on versions 38/41 is assumed to be plausible but unconfirmed — MEASURED-EVIDENCE predates v49 and no v49-specific repeated-run data was provided.
