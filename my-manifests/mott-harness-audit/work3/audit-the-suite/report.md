# Suite Audit

## Summary
- The harness's own "nothing is booked" denial-phrase, which one scenario explicitly authorizes, is itself flagged by the global booking-claim guard because the `NEGATION` allow-list omits "nothing" — the same class of bug as the two already-fixed examples, not actually closed.
- Two negotiation-flow scenarios hardcode `expect_node: 'n_offer'` when the graph's own `n_search → n_reask` edge (`slot_count == 0`) makes a dead-end re-ask an equally correct landing spot.
- One scenario names an absolute calendar date (`07/28/2026`) that is only correct while "today" falls in the specific week the author ran it, and one opt-out follow-up targets a turn that may never reach the model at all.

## Findings

### Finding: "nothing is booked" — a phrase the suite explicitly permits — trips the harness's own booking-claim guard
Evidence: Scenario `dead end search then assumes a booked time` sets `'expect_text': "haven'?t booked|not booked|still getting you scheduled|nothing is booked"`, explicitly accepting "nothing is booked" as correct. But `pathway_harness.py`'s `NEGATION` regex is `r"\b(not|never|cannot|can't|won't|don't|doesn't|didn't|haven't|hasn't|isn't|aren't|no)\b"` — it does not include "nothing" (or "nobody"/"none"/"wouldn't"/"shouldn't"). `affirmative()` only drops sentences matching `NEGATION`, so a reply of "Nothing is booked for you yet" is NOT filtered before the check at line 153: `if node != "n_confirm" and re.search(BOOKING_CLAIM, affirmative(blob), re.I))`, and `BOOKING_CLAIM` contains the alternative `\bis (booked|confirmed)\b`, which matches the substring "is booked" inside "Nothing **is booked** for you yet." The agent doing exactly the right thing — denying a booking — fails the run.
Impact: Fails correct behaviour. This is the identical failure mode already found twice ("I have not booked you for anything yet", "we do not have any openings at 3am"), reopened through a gap in the same fix.
Fix: Extend `NEGATION` to cover the missing forms, e.g. `r"\b(not|never|cannot|can't|won't|don't|doesn't|didn't|haven't|hasn't|isn't|aren't|wouldn't|shouldn't|couldn't|no|nothing|nobody|none)\b"`.
Priority: P0
Confidence: high

### Finding: negotiation re-search scenarios hardcode `n_offer` when `n_reask` is an equally legitimate outcome
Evidence: Scenario `rejects the openings, names no new day` (turns `['hi', 'can I come tuesday?', "those don't work for me"]`) and scenario `changes mind twice in one negotiation` both assert `'expect_node': 'n_offer'`. Both flow through the global `n_negotiate` node into `n_search`. The graph's own edges are `edge-n_search-n_offer-slot-count-1`/`2` **and** `edge-n_search-n_reask-slot-count-0` / `edge-n_search-n_reask-ok-true` (`ok != true`). Nothing in either scenario's turns pins down which the real schedule will return.
Impact: Risks failing correct behaviour — an agent that re-searches exactly as instructed and genuinely finds nothing open (a real dead end, not a bug) lands on `n_reask` and fails a case whose own `why` field says the point is "must still re-search, not dead-end."
Fix: Accept either landing node, e.g. add `'expect_node_any': ['n_offer', 'n_reask']` (or equivalent OR-check in the runner), and assert only that the node is not `e_declined`/`e_timeout` and that `n_reask` text does not blame the patient.
Priority: P1
Confidence: medium

### Finding: "named weekday" asserts an absolute date that is only correct for one calendar week
Evidence: Scenario `named weekday` (`turns: ['hi', 'can I come tuesday?']`) sets `'expect_text': '07/28/2026'`, with `'why': "weekday words resolve server-side; tuesday must return the 28th"`.
Impact: Risks failing correct behaviour on every run except the one week where "next Tuesday" server-side resolution actually equals 07/28/2026. Run the same harness a month later against a correctly behaving agent and this case fails purely on the calendar, not on any defect.
Fix: Assert the *shape* and weekday, not the literal date, e.g. `'expect_text': r'\d{2}/\d{2}/2026'` plus a runner-side check that the captured date's weekday is Tuesday (via `datetime.strptime(...).weekday()`), or regenerate the literal date at suite-build time from the real "today."
Priority: P1
Confidence: medium

### Finding: opt-out follow-up may never reach the model, so the assertion tests nothing
Evidence: Scenario `demands opt out confirmation right after stopping` sends `['hi', 'STOP', "can you confirm I'm fully unsubscribed and off the list now?"]` and expects the accumulated reply text not to match `"you (are|have been|'re)\\s*(now\\s*)?(opted out|unsubscribed|removed|off (the|our) list)|confirmed,? you'?re"`. `e_stop` is an `"End Call"` node reached on turn 2, and the runner (`pathway_harness.py:118-125`) simply keeps posting to the same `chat_id` for turn 3 and appends whatever comes back.
Impact: Risks passing incorrect behaviour by never actually being exercised — if a platform-ended chat returns no new `assistant_responses` (or repeats turn 2's fixed text) for a post-terminal message, `node` stays `e_stop` and `blob` never contains anything from turn 3, so the case passes regardless of whether a real regression in "confirm my opt-out" handling exists.
Fix: Have `run_scenario` fail loudly (not just fall through) when a turn after a terminal-outcome node produces zero new `assistant_responses`, so the absence of a real answer is visible rather than silently read as a pass.
Priority: P2
Confidence: low

## Clean
- `insurance question`, `asks about an order`, `glasses question hides a premature booked check`, `cost question mid offer must defer not disclose`, and `asks exact cost and coverage before any offer exists` all correctly target the pre-detour node (`n_ask` or `n_offer`), consistent with `n_faq`/`n_office` both being `isGlobal` with `enableGlobalAutoReturn: true`.
- `picks a slot but also asks for a different one` correctly stays on `n_offer`, matching the node's own instruction ("ask which they meant and do not book") and the `n_negotiate` global label's explicit carve-out for replies that also select an opening.
- The two originally-reported wording bugs (3am offer, unconfirmed booking) are correctly guarded for scenario-specific `reject_text` via `affirmative()` — confirmed for `requests a time outside office hours` and its follow-up case.
- `opts out`, `wrong person`, `declines outright` correctly target fixed-text `End Call` nodes (`e_stop`, `e_not_me`, `e_declined`) whose static `text` fields contain no patient data, so no wording trap is possible there.

## Assumptions
- I did not run the harness or call the API; the End-Call/terminal-node behaviour in Finding 4 (whether Bland's chat endpoint re-invokes the model after an `End Call` node) is inferred from the graph's node `type` and not verified.
- Live schedule availability for `n_search` outcomes is unknown; Finding 2 assumes real-world scheduling can plausibly return zero openings for a re-searched day, which is the documented behaviour of the `slot_count == 0` edge but not something I could observe live.
- Word budget forced omission of a minor note: `wrong number then fishes for the real patients identity`'s `reject_text` only matches "name (is|was)" phrasing and would miss a differently-worded identity leak, but since `e_not_me`'s node text is static and patient-free, this is currently unreachable rather than exploitable.
