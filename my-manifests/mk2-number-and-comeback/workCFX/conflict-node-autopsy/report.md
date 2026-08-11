# BREAK_POINT

BREAK_POINT: `edge-n_date_conflict-n_search-patient-chooses-one-conflicting-date` is too narrow and there is no fallback outbound edge, so a fresh third date cannot leave `n_date_conflict`.

`n_search` enters `n_date_conflict` through `edge-n_search-n_date_conflict-date-conflict-detected-conflict` when `date_conflict_detected == conflict`. The node then has exactly one outbound edge, `edge-n_date_conflict-n_search-patient-chooses-one-conflicting-date`, whose label and description both require that the “patient chooses one conflicting date.” The node's five extractors do consume the next message, and the incident proves `preference_from` became `friday the 14th`, but the graph has no outbound condition for a new date that is neither original conflicting option and no catch-all/fallback. Bland therefore has no selected destination, stays on the `Default` node `n_date_conflict`, re-renders its fixed prompt, and makes no new `n_search` webhook call. This contradicts SPEC-v91 assertion 14's intended invariant that “`n_date_conflict` routes back to `n_search`”; the assertion checks adjacency, not whether the edge condition covers every usable clarification.

# EDGE INVENTORY

`n_date_conflict` is a `Default` node with `userWait: true`, no `modelOptions`, and this full prompt:

> The patient gave two dates that disagree. Ask them to choose. Say: I want to make sure I get the right day. Did you mean {{conflict_option_1}} or {{conflict_option_2}}? Do not name any other date.

Its `extractVars` are `user_verbatim`, `preference_from`, `day_part`, `time_after`, and `preference_to`. There is no explicit extraction flag triple on this node in v92 and no retry/counter variable. The `preference_from` and `preference_to` extractors accept a patient-proposed weekday/date; for a single named day, `preference_to` should mirror it. Thus “Friday the 14th” is usable search input even though it does not select either offered conflict option.

| Direction | Edge id | Label / condition | Result for “Friday the 14th” |
|---|---|---|---|
| In | `edge-n_search-n_date_conflict-date-conflict-detected-conflict` | `date_conflict_detected == conflict` | Does not apply to the reply. It was satisfied by the prior availability response and is what entered `n_date_conflict`. |
| Out | `edge-n_date_conflict-n_search-patient-chooses-one-conflicting-date` | `patient chooses one conflicting date` | Fails. The two carried alternatives were 08/07 and 08/17; 08/14 is a fresh third date, not a choice of either conflicting date. Although extraction sets `preference_from` to `friday the 14th`, the edge classifier has no condition based on “any valid new date” or on nonempty/changed `preference_from`. |

There are no other inbound or outbound edges. In particular, there is no invalid/irrelevant-answer re-ask edge, no second-attempt node, and no fallback edge. The node that should receive a usable fresh answer is `n_search`, because its request body sends `{{preference_from}}`, `{{preference_to}}`, `{{time_after}}`, `{{lastUserMessage}}`, and `{{user_verbatim}}` to `/availability`; its response pathways then produce an offer, a miss flow, another detected conflict, or a safe failure.

# CONFLICT QUESTION ASSEMBLY

`n_search.responseData` maps gateway tuple fields as follows:

- `$.result.date_conflict[0]` → `date_conflict_detected`, used by the inbound condition `date_conflict_detected == conflict`.
- `$.result.date_conflict[3]` → `conflict_option_1`.
- `$.result.date_conflict[4]` → `conflict_option_2`.

`n_date_conflict.data.prompt` interpolates `{{conflict_option_1}}` and `{{conflict_option_2}}` verbatim. In the incident, tuple elements 3 and 4 already contained explanatory fragments, “next friday Friday the 7th” and “the 17th Monday the 17th”; the prompt then wrapped those raw internals in “Did you mean … or …?”, causing the duplicated, unnatural copy. The node has no resolved-display-date fields and no formatting layer.

# MINIMAL V93 CHANGE SET

1. Broaden the existing outbound edge rather than depending on selection of an original option. Keep its source and target, but rename its id to `edge-n_date_conflict-n_search-patient-provides-usable-date` and set label to `patient provides any usable day, weekday, or date, including either conflicting option or a new replacement date`; set the description to the matching house form. “Friday the 14th” must select this edge and invoke `n_search` once with the newly extracted values.
2. Add one bounded re-ask node, `n_date_conflict_retry`, of type `Default`, with `userWait: true` and the same five extraction variables. Its prompt must say this is the last clarification and ask for one specific day/date. Do not loop it to itself or back to `n_date_conflict`.
3. Add `edge-n_date_conflict-n_date_conflict_retry-no-usable-date` with label `patient does not provide any usable day, weekday, or date`. This is the only re-ask route. Order/evaluate the usable-date route ahead of it so valid input cannot be captured by the negative branch.
4. Add a single unconditional/fallback edge `edge-n_date_conflict_retry-n_search-after-one-reask` from `n_date_conflict_retry` to `n_search`, labeled `after the one allowed re-ask, always continue to search using the best extracted date; never remain on this node`. This implements fail-open-to-search. If Bland does not support a true catch-all edge, use an exhaustive pair from the retry node: usable date → `n_search`; no usable date → `n_search`. There must be no retry-node self-loop and no route back to the first conflict node.
5. Make the retry extraction deterministic for ignored answers: retain the existing extractor defaults so `preference_from`/`preference_to` resolve to the last usable working day rather than null. Add prompt language that on an irrelevant second reply the assistant must not claim certainty; it should silently continue with the best extracted date and let the returned offer expose the actual date.
6. Add a graph validator assertion that adjacency(`n_date_conflict`) is exactly `{n_search, n_date_conflict_retry}`, adjacency(`n_date_conflict_retry`) is exactly `{n_search}`, and every possible reply reaches `n_search` after zero or one re-ask. Reject any self-loop or fail-stay path.
7. Replace the raw tuple display fields as described below. Do not alter the gateway conflict detection or `n_search` request contract for this repair.

# COPY FIX

The gateway/pathway should expose or derive two display-only values from the resolved ISO dates in tuple positions 1 and 2, not pass tuple explanation fragments from positions 3 and 4 to the patient. Preferred variables: `conflict_date_1_display = Friday 08/07` and `conflict_date_2_display = Monday 08/17`.

English draft: `I want to make sure I get the right day. Did you mean Friday 08/07 or Monday 08/17? You can also reply with a different date.`

Chinese parity: use the same two resolved dates and weekdays, in the same order, with no tuple prose or internal field names: `我想确认一下正确的日期。您是指 08/07 星期五，还是 08/17 星期一？您也可以回复其他日期。` Preserve the thread's established language; do not send both languages in the same clarification.

# DOUBLE GREETING

Inconclusive from the graph alone. `n_identity` is the sole start node (`isStart: true`) and is silent (`text: ""`) with `modelOptions: {"retryAttempts": 0, "skipUserResponse": true}`. On a unique identity it auto-advances to `n_appt_check`; that webhook is also silent with the same model options and routes either `appt_count == 0` or `ok != true` to `n_ask`. `n_ask` is the only examined node containing the recall greeting and has no `skipUserResponse`; one execution of either `n_appt_check` branch should enter it once. The graph contains two possible conditions targeting `n_ask`, but they are response-path alternatives, not evidence that both fired. Nothing in the static JSON establishes whether the runtime evaluated both, started the pathway twice, retried message delivery, or duplicated an event. The two timestamps therefore require execution/event logs or harness instrumentation to attribute; the graph alone does not justify a root-cause claim.

# TEST PLAN

Instrument the chat harness to record visited node ids, every outbound edge selected, every webhook request, and every patient-facing message with timestamps. Assertions must fail on an extra clarification, repeated node residence, duplicate greeting, or missing search call.

1. **Conflict → replacement answer → offer.** Seed the conflict response equivalent to `('conflict','08/07/2026','08/17/2026',...)`; assert one clean clarification. Reply `Friday the 14th`. Assert extraction yields `preference_from = friday the 14th` and matching `preference_to`; edge `edge-n_date_conflict-n_search-patient-provides-usable-date` fires; exactly one new `/availability` call occurs; the next patient-facing node is an offer (fixture `slot_count >= 1`); `n_date_conflict_retry` is never visited; the original clarification is not repeated.
2. **Conflict → choose first option → offer.** Reply `Friday the 7th`; assert the same direct edge and exactly one search call. This protects the original intended case.
3. **Conflict → ignore → one re-ask → search anyway.** Reply with irrelevant text. Assert transition to `n_date_conflict_retry` and exactly one final clarification. Reply irrelevantly again. Assert transition to `n_search`, exactly one `/availability` call using non-null best extracted date values, and no third clarification. With an availability fixture, assert an offer follows.
4. **Conflict → ignore → valid answer on re-ask.** First reply irrelevant, then `Friday the 14th`; assert one re-ask, then `n_search`, then offer. Assert neither conflict node is revisited.
5. **Greeting cardinality.** Run the start flow for both `appt_count == 0` and appointment-check failure fixtures. Assert `n_identity` and `n_appt_check` emit zero messages, `n_ask` emits exactly one recall greeting, and only one `n_ask` visit/message exists per inbound start event. Log event/call correlation ids so a duplicate start can be distinguished from duplicate rendering.
