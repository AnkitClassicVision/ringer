# Round 26 - closed-day ask copy and Chinese routing vocabulary

## Prompt diff

Added `CLOSED-DAY:` to `n_goal_ask`, matching the response-node guard at the point where zero-result searches actually land. When `closed_day` is true, the ask node says the office is closed that day, states that the office is not open on weekends, and asks what weekday works. It replies in English or, when the patient wrote Chinese, in Chinese. It must never call a closed day unavailable or imply that it was booked out.

## Label diff

Extended the existing single `n_goal_response -> n_goal_search_offered_time` edge label and description with the literal Chinese qualifiers `下午`, `早上`, `晚上`, `中午`, and `晚一点`. The label explicitly says these route to the offered-date-time search even when written alone as a single word. The inherited round-24 `even if` and `after` wording remains intact. No edge was added, and the response node still has eight outbound edges.

## Validator

Assertion 26 requires both the `CLOSED-DAY:` marker in `n_goal_ask` and `下午` in the offered-time edge label or description. Assertions 1 through 25 remain intact.

Observed proof:

- New round-26 draft: `PASS: 545 assertions`.
- Untouched round-25 draft: exit 1 with assertion 26 naming the missing `n_goal_ask` `CLOSED-DAY:` marker and missing offered-time `下午` vocabulary.
- Node IDs: identical, 42 nodes.
- Edge IDs and source/target endpoints: identical, 122 edges; `n_goal_response` retains eight outbound edges.
- Every graph `extractVars` value: identical to round 25.
- All required guard markers remain present, including the inherited `CLOSED-DAY:` marker on `n_goal_response`.
- `frozen-extractors.json`: byte-identical to round 25, SHA-256 `aab8d90e52c0763ac4738771a8d91d4a7d1992b2cd696dd74a36e7d5aa92a616`.
- Prompt lengths remain within unchanged validator ceilings: `n_goal_ask` 2,200 characters; `n_goal_response` 5,698 characters.

# Round 25 - closed-day honest miss copy

## Mapping diff

Every availability webhook node that already maps `out_of_hours` now also maps `closed_day` from `$.result.closed_day`, using the same response-data mechanism and naming convention. No response pathway, edge, node, request body, or extractor changed.

## Prompt diff

`n_goal_response` now includes the `CLOSED-DAY:` marker. When `closed_day` is true, it says the office is closed that day and explains that the office is not open on weekends, then asks which weekday works. It must not imply that a closed day was booked out or name availability on that day. When `closed_day` is false or absent, the inherited honest-miss copy is unchanged.

## Validator

Assertion 25 checks that every availability webhook mapping `out_of_hours` also maps `closed_day`, and that `n_goal_response` contains `CLOSED-DAY:`. Assertions 1 through 24 remain intact.

The authorized prompt addition raises the existing `n_goal_response` length ceiling from 5,400 to 5,700 characters; the generated prompt measures 5,621 characters.

Observed proof:

- New round-25 draft: `PASS: 544 assertions`.
- Untouched round-24 draft: exit 1 with assertion 25 naming all six missing `closed_day` mappings and the missing `CLOSED-DAY:` prompt marker.
- Node IDs: identical, 42 nodes.
- Edges: identical JSON, 122 edges.
- Every graph `extractVars` value: identical to round 24.
- `frozen-extractors.json`: byte-identical to round 24, SHA-256 `aab8d90e52c0763ac4738771a8d91d4a7d1992b2cd696dd74a36e7d5aa92a616`.

# Round 24 - negative claims require a search

## Measured defect

On live v120, `n_goal_response` offered Friday 08/07/2026 at 11:00 am or 11:15 am. The reply `later one, unless u have after 4 instead` stayed on that node and no webhook ran, but the response fabricated that nothing was available after 4 pm. The standing slot variables cannot prove that negative claim.

## Edge and label diffs

- Expanded the single `n_goal_response -> n_goal_search_offered_time` edge to cover every offered-day time qualifier: after, before, around, later-than, from-hour, earliest/soonest, and evening wording. It explicitly applies **even if** the same message references an offered option such as `the later one`, `option 2`, or `that one`.
- Tightened both gate labels so first/second selection matches only when no clock-time or after/before/around/later-than/evening qualifier is present.
- Tightened the named-time-pick edge through its retained exclusion of after/before windows. Tightened the mixed-intent edge to different-day selection conflicts and excluded offered-day time qualifiers.
- Removed only the `n_goal_response -> e_declined` edge to keep `n_goal_response` at the required maximum of eight outbound edges. No node was deleted; other decline routes remain unchanged. The single correction/new-preference edge to `n_goal_search`, the single offered-time edge, and the human-request edge required by assertion 23 remain.

## Exact prompt guard

```text
NEGATIVE-REQUIRES-SEARCH: Never state or imply that a time, day, or window has no availability unless the immediately preceding webhook result for that exact constraint shows it. When a patient asks about a different time and no such result exists, the ONLY valid move is routing to a search - answer nothing about availability inline.
```

The `ROUTING` paragraph also says a selection is accepted only without a clock/window qualifier and sends any offered-day time qualifier to `n_goal_search_offered_time`.

## Validator and proof

Assertion 24 requires exactly one `n_goal_response -> n_goal_search_offered_time` edge whose label or description contains both `even if` and `after`, plus the `NEGATIVE-REQUIRES-SEARCH:` prompt marker. Assertions 1 through 23 remain active.

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workR23/gl-round23-fix/pathway-goalloop-draft.json
```

Observed: the new draft and conformant fixture each pass 543 assertions. The untouched round-23 draft fails and explicitly cites assertion 24 for both missing mixed-reference qualifier wording and the missing prompt marker.

Frozen extractor proof: `frozen-extractors.json` retains SHA-256 `aab8d90e52c0763ac4738771a8d91d4a7d1992b2cd696dd74a36e7d5aa92a616`, identical to round 23. Every graph `extractVars` value also compares equal to its round-23 counterpart. Webhook bodies compare equal, and the node ID set is unchanged.

# Round 21: offered-date hour refinement and negative-claim guard

## Live v117 evidence and defects

With Thursday 08/06 offers at 10:30 am and 10:45 am still standing, the patient asked `How about after 1`. Extraction succeeded with `time_after = 01:00 PM`, but no edge fired: the slot variables and `BlandStatusCode` remained unchanged from the prior turn, proving no availability search ran. `n_goal_response` then fabricated `I do not have anything after 1:00 pm on Thursday 08/06/2026`. That claim was false because the day had 1:00 pm, 2:00 pm, 2:15 pm, and later openings; only 1:30-2:00 pm was taken.

There were two separate defects. The offered-date time-refinement edge did not name after-hour, before-hour, later-than, or from-hour language, so `after 1` did not route. The response prompt also lacked a hard rule against asserting unavailability for a constraint that had not just been searched.

## Changes

- Extended the existing `n_goal_response -> n_goal_search_offered_time` label, and its mirrored `ROUTING` description, with after, before, later-than, and from-hour refinements on the offered date, including `after 1`, `after 3pm`, `before noon`, and `later in the day`. Existing offer-conditioning and earliest/soonest/first-available coverage remain intact.
- Added `NO-NEGATIVE-CLAIM:` to `n_goal_response`. A time, window, day, or date may be called unavailable only when the most recent search used that exact constraint and returned no matching slots. An unsearched window must route to a fresh search, never be answered from memory.
- Added assertion 21 while retaining assertions 1 through 20 and the graph-wide compound-condition ban from round 20b. It checks the offered-time edge wording and `after 1` example, the mirrored prompt wording, and the `NO-NEGATIVE-CLAIM:` marker.
- Everything inherited from rounds 6 through 20b is otherwise unchanged. The extract/prompt/compress-context design remains intact: extraction stays on user-wait nodes, the pre-offer and post-offer prompt split remains, and compression does not replace deterministic routing.

## Regenerate and validate round 21

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD28/gl-round20b-fix/pathway-goalloop-draft.json
```

The round-21 draft and conformant fixture must pass. The untouched round-20b draft must fail with structured `assertion 21` citations. The compound-condition rule remains an independent fail-closed graph-wide check.

# Round 20b: responsePathway conditions use simple triples

## Live v116 evidence and root cause

The named-time route reached the offered-date anchor search, and the availability gateway returned `anchor_exact: true` with the correct `08/13 10:45 am` opening held. The flow nevertheless entered `n_time_pick_offer` instead of `n_gate_1`.

Round 20 encoded `['anchor_exact', '==', 'true AND slot_count >= 1']`. Bland treats the third responsePathway item as one literal value, so `true` cannot equal `true AND slot_count >= 1`; the paired `!=` fallback consequently matched. Durable convention: every Bland responsePathway condition is one simple `[field, operator, literal value]` triple. Compound logic is represented by ordered rows, never by putting `AND` or `OR` in the value.

## Rows changed and audit result

- `n_goal_search_offered_anchor` row 2: `['anchor_exact', '==', 'true AND slot_count >= 1'] -> n_gate_1` became `['anchor_exact', '==', 'true'] -> n_gate_1`.
- `n_goal_search_offered_anchor` row 3: `['anchor_exact', '!=', 'true AND slot_count >= 1'] -> n_time_pick_offer` became `['anchor_exact', '!=', 'true'] -> n_time_pick_offer`.
- The corresponding graph edge labels and descriptions now read `anchor_exact == true` and `anchor_exact != true`.
- A graph-wide audit found no other responsePathway value containing `AND` or `OR`, so no other rows required splitting.

Ordering remains the control logic: `ok != true` first, then `slot_count == 0`, then the exact and non-exact anchor rows. Assertion 20 checks the two simple triples, and the validator has a general compound-condition rule that reports the offending node and row. Assertions 1 through 19 remain active.

Validator regression repair: assertion 12 accepts both the historical compound representation and the round-20b simple representation so it remains a backward-compatible routing check. The new condition-shape requirement belongs to assertion 20 plus the graph-wide `compound-condition rule`. Compound-rule failures retain an assertion-19 compatibility tag because the inherited round-19 harness requires its historical negative control to cite assertion 19.

The inherited extract/prompt/compress-context design remains intact: extraction stays on user-wait nodes, the pre-offer and post-offer prompt split is unchanged, and the deterministic routing decision remains isolated in the webhook.

## Regenerate and validate round 20b

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD27/gl-round20-fix/pathway-goalloop-draft.json
```

The round-20b draft and conformant fixture must pass. The untouched round-20 draft must fail with a structured `compound-condition rule` citation naming `n_goal_search_offered_anchor` and each offending row.

# Round 20: offered-date-pinned named times and one confirmation

## Live v115 transcript evidence

The patient asked `How about next Thursday?` and received openings for `08/13`. They then typed `1045`. The unpinned named-time anchor search re-resolved the bare weekday and returned `08/06`, so the flow offered, confirmed, and booked a date one week earlier than the established offer.

The same `1045` turn also produced two consent steps: first `I have ... 10:45 am. Reply 1 to take it`, then `To confirm ... Reply YES to book it`. Ankit's ruling is that a patient-named time proven to exist on the established offered date must go straight to the single booking confirmation.

## Graph fix

- Added `n_goal_search_offered_anchor`, cloned from `n_goal_search_anchor`. Its `from` and `to` are both exactly `{{slot_1_start}}`, while `time_pref` remains `anchor={{goal_anchor}}`. Its JSON body contains only the ten availability gateway fields.
- Copied the anchor response mappings and added `anchor_exact` from `$.result.anchor_exact` plus `anchor_requested` from `$.result.anchor_requested`.
- Retargeted only the `n_goal_response` named-time edge, including bare digit forms, to the offered-date-pinned anchor. The `n_goal_ask` pre-offer near/around-time edge still targets the unpinned `n_goal_search_anchor` because no offered date exists there.
- An executable exact result, `anchor_exact == true AND slot_count >= 1`, routes directly to `n_gate_1`. A non-exact result with an opening routes to `n_time_pick_offer`. Zero results and gateway failure route to `n_goal_ask`.
- `n_gate_1`, its `BOOKING-INTEGRITY:` rule, and its verbatim `{{slot_1_day_name}} {{slot_1_start}}` confirmation copy are unchanged. Everything inherited from rounds 6 through 19 is otherwise unchanged.
- Added assertion 20 while retaining assertions 1 through 19. It checks the pinned, contract-clean webhook and gateway mappings; post-offer and pre-offer routing separation; and exact, non-exact, zero-result, and failure pathways.

The existing extract/prompt/compress-context design remains intact: extraction stays on user-wait nodes, the pre-offer and post-offer prompt split is unchanged, and the new deterministic decision is isolated in a webhook rather than prompt priority.

## Regenerate and validate

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD26/gl-round19-fix/pathway-goalloop-draft.json
```

The round-20 draft and conformant fixture must pass. The untouched round-19 draft must fail with a structured `assertion 20` citation.

# Round 19: dedicated named-time single-slot offer

## Live v114 evidence and diagnosis

The patient asked `How about around 2`. The anchor route worked: `goal_anchor` was `02:15 PM`, and the anchor search returned `slot_1 = 02:15 pm`. The shared response still rendered `I have Monday 08/10/2026 02:15 pm or Monday 08/10/2026 02:00 pm... Reply 1 or 2`. After the patient typed `215` again, it rendered another two-option offer whose second option was on a different day.

Round 18 put `SINGLE-SLOT:` into `n_goal_response`, but that prompt already carried five competing policy blocks and its dominant two-slot template won. Prompt priority is not a reliable control boundary. This matches the earlier ask/response split: behavior that must be deterministic needs a separate graph node.

## Node-based fix

- Added `n_time_pick_offer`, a user-wait Default named `Named-time offer`. It renders exactly one `slot_1` opening and never references `slot_2`. A match asks for reply `1`; a mismatch says the named time is unavailable, identifies the returned first slot as the closest opening, and asks whether the patient wants it.
- The anchor search now sends `slot_count >= 1` only to `n_time_pick_offer`. Its error, conflict, unresolved-day, out-of-hours, and zero-result paths are unchanged. The other four availability searches still reach `n_goal_response`.
- The new node has five outbound edges: take the opening to `n_gate_1`, another preference to `n_goal_search`, latest/end-of-day to `n_goal_search_latest`, decline, and timeout. It has no `n_gate_2` edge and carries the frozen extractor set verbatim.
- Removed the dead `SINGLE-SLOT:` block from `n_goal_response`. `TIME-GRID:`, `OFFER-INTEGRITY:`, `NO-BOOKING-CLAIM:`, booking-integrity-adjacent routing, and the response-to-anchor named-time edge remain intact.
- Added assertion 19 while retaining assertions 1-18. Assertion 19 checks the dedicated user-wait node, exact one-slot template, absence of every `slot_2` reference, anchor success routing, edge containment, booking-claim guard, frozen extractors, and removal of the old response prompt block.

The existing extract/prompt/compress-context design remains intact: extraction stays on user-wait nodes, pre-offer and shared two-option response prompts remain separate, and the dedicated one-option behavior is isolated in a small prompt under 1,500 characters.

## Regenerate and validate

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD25/gl-round18-fix/pathway-goalloop-draft.json
```

The round-19 draft and conformant fixture must pass. The untouched round-18 draft must fail with a structured `assertion 19` citation.

# Round 18: deterministic single-slot named-time picks

## Live evidence and decision

On live v113, the offered openings were 11:15 am (slot 1) and 11:30 am (slot 2). The patient typed `1115`, but the semantic gate router selected 11:30. `BOOKING-INTEGRITY:` caught the later correction (`I said 1115`) and re-stated 11:15, so the wrong opening was not booked, but the patient had to repeat the choice.

Ankit's fixed decision is deterministic routing: a named clock-time pick, including bare forms such as `1115`, `11 15`, and `11:15`, goes through the existing anchor search. That search orders openings nearest to `anchor={{goal_anchor}}`; the response then offers one matching first slot for a single `1` confirmation.

## Round-18 changes

- Added the mirrored `n_goal_response -> n_goal_search_anchor` named-time-pick edge. The existing `reply 1` and `reply 2` gate edges and unambiguous named-time gate behavior remain intact; the new bare named-time route takes precedence.
- Extended only the shared `goal_anchor` extractor description to normalize bare 3-4 digit forms such as `1115`, `1015`, and `930` to HH:MM am/pm. The identical definition is applied to every wait node carrying `goal_anchor`. The frozen five-extractor file is otherwise unchanged.
- Added `SINGLE-SLOT:` to `n_goal_response`. A matching anchored first slot is the only opening offered, using literal `{{slot_1_day_name}} {{slot_1_start}}`, with reply `1` requested. A non-match reports the exact named time unavailable and falls back to the two literal returned slots. `TIME-GRID:`, `OFFER-INTEGRITY:`, `NO-BOOKING-CLAIM:`, the anchor body, gates, confirms, post-booking behavior, and all earlier guards remain intact.
- Added assertion 18 while retaining assertions 1-17. It checks the named-time anchor edge and mirrored label, the bare-digit example, `SINGLE-SLOT:`, identical bare-time extractor coverage, the pinned anchor body, and both anchor success paths back to `n_goal_response`. The existing response prompt and edge-count ceilings were raised only to admit this authorized block and route.
- The response prompt ceiling is 5,000 characters. The existing extract/prompt/compress split remains: frozen production extractors plus `goal_anchor`, separate pre-offer and post-offer prompts, and compact graph-local policy blocks.

## Round-18 regenerate and validate

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD24/gl-round17-fix/pathway-goalloop-draft.json
```

The round-18 draft and conformant fixture must pass. The untouched round-17 draft must fail with structured `assertion 18` citations for the missing named-time anchor route, `SINGLE-SLOT:` rule, and bare-digit `goal_anchor` contract.

## Prior round-17 record

# Goal-loop round 17: no invented times or false booking claims

## Live v112 evidence

Real availability for Friday 08/28 was `10:30 am` and `10:45 am`. The patient typed `Lets do 1040`. The bot invented a nonexistent off-grid opening and replied: `I have Friday 08/28/2026 10:40 am at MK2 Optical. Reply 1 to take it`. The strict practice grid permits only `:00`, `:15`, `:30`, and `:45`.

The patient then typed `I will take it`. The bot falsely replied: `Great, I have got you down for Friday 08/28/2026 at 10:40 am. We will see you then!` No booking webhook fired: `book_success` and `new_appt_id` were null, the conversation ended on `n_goal_ask`, and the practice system contained zero appointments. The two defects were therefore an invented time that does not exist and a booking confirmation for an appointment that was never booked.

## Round-17 changes

- Every patient-facing wait node now contains a `NO-BOOKING-CLAIM:` block: `n_goal_ask`, `n_goal_response`, `n_mixed_intent`, `n_gate_1`, `n_gate_2`, `n_post_booking`, `n_date_conflict`, and `n_date_conflict_retry`. All pre-booking stages say nothing is booked yet and prohibit booked, held, confirmed, reserved, set, or see-you-then claims. `n_post_booking` preserves the existing appointment but prohibits any new or changed booking claim and sends changes to the office.
- `n_goal_response` now contains `TIME-GRID:`. It may state only the literal rendered slot pairs, rejects every off-grid minute including `10:40`, restates the real values verbatim, and asks which real opening the patient wants. Its existing `OFFER-INTEGRITY:` and gate `BOOKING-INTEGRITY:` blocks remain intact.
- `n_goal_ask` contains no slot templates and cannot state, render, infer, repeat, or estimate any clock time, including the patient's requested clock.
- Confirmation containment is explicit: `n_confirm_1` accepts inbound flow only from `n_book_1` or its matching `n_reconcile_1` recovery path; branch 2 is identical. The generated graph currently has only the matching `n_book_N` success inbound edges.
- Assertion 17 checks all eight markers, `TIME-GRID:`, retained `OFFER-INTEGRITY:`, absence of slot templates in `n_goal_ask`, and the confirm inbound allowlist. Assertions 1 through 16 remain active. The authorized `n_goal_response` prompt ceiling is now 4,600 characters.

Round 17 does not change the frozen five-extractor contract, extraction behavior, prompt split/compression design, or inherited `compress-context` notes. `fixture-conformant.json` is regenerated from the same deterministic build.

## Regeneration and round-17 proof

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD23/gl-round16-fix/pathway-goalloop-draft.json
```

The round-17 draft and conformant fixture must pass. The untouched round-16 draft must fail with structured `assertion 17` citations for the missing claim and grid guards.

# Goal-loop round 16: booking integrity fails closed

## Live wrong-date booking evidence

On v110, the patient was told `booked for Thursday 08/27/2026 04:30 pm`, while the booking gateway actually wrote Thursday 08/06/2026 at 04:30 pm. The same defect class remained in the v111 round-15 draft: the booking webhook uses `{{slot_2_start}}`, and those slot variables still contained the old 08/06 search results even though the response text had drifted to the requested 08/27 date.

Two measured defects contributed:

- Correction routing failed. With 08/06 offers standing, `No Thursday the 27` did not trigger a fresh lookup. A controlled replay re-offered stale 08/06 results twice; the live response later spoke 08/27 while the variables remained 08/06.
- The graph had no comparison between the appointment spoken/agreed with the patient and the slot values about to be confirmed and booked. A drifted response could therefore pass through a gate to a real booking.

## Round-16 changes

- Added a dedicated `n_goal_response -> n_goal_search` correction edge for a patient who `corrects or replaces the offered date with a different specific day, date, or weekday - including replies beginning with no, actually, or I meant`. The same wording is mirrored in the response prompt and edge description. The existing new-preference edge remains unchanged beside it.
- Both `n_gate_1` and `n_gate_2` retain their existing branch-specific literal confirmation copy using only `{{slot_N_day_name}} {{slot_N_start}}`.
- Both gate prompts now carry a `BOOKING-INTEGRITY:` fail-closed rule. If the patient's agreed date or time differs from the slot being confirmed, the gate must not confirm or proceed to booking; it asks to re-check the date and routes to a fresh search.
- Each gate has a separate `n_goal_search` edge labeled `the patient names a date or time that does not match the opening being confirmed`. Existing `says no or wants other times` edges remain unchanged.
- Assertion 16 checks the exact correction edge and mirrored prompt/description, both gate markers, and both structural mismatch routes. Assertions 1 through 15 remain active; the round-12 post-offer routing cap is nine because the required correction route sits alongside the prior eight routes.

Round 16 does not change the frozen five-extractor contract, inherited `extract` behavior, prompt-splitting/compression design, or `compress-context` notes and budgets from round 13.

## Regeneration and round-16 proof

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD21/gl-round15-fix/pathway-goalloop-draft.json
```

The round-16 draft and conformant fixture must pass. The untouched round-15 draft must fail with structured `assertion 16` citations for the absent correction route, gate rule blocks, and gate mismatch routes.

## Inherited round-15 evidence

# Goal-loop round 15: post-booking conversations stay alive

## Measured v110 defect and design ruling

Minutes before this round, the live v110 thread booked successfully. The patient then wrote `Wait can I change?`, received the office referral, and the conversation ended at the `e_defer` End node with `ended_by_end_call_node=true`. A later patient text received no response and produced no new conversation record. The line had `restart_after_end_call=true`, so the measurement proves that flag did not recover this pathway termination.

Soft outcomes must not end the thread. Only true terminals may end it: opt-out (`e_stop`), wrong-person (`e_not_me`), declined (`e_declined`), no-reply (`e_timeout`), and safety ends.

## Round-15 changes

- Added `n_post_booking`, the user-wait Default `Booked - support`. Its branch-agnostic prompt confirms the appointment is set, refers every change/cancel/reschedule request to `(212) 219-2219`, continues answering politely, contains no slot templates or extractors, and forbids claiming it can modify or rebook.
- `n_post_booking` has only opt-out and 72-hour timeout exits. It has no route to availability, signing, gates, or booking.
- Every former `e_defer` edge and response pathway now reaches `n_post_booking`; both booking-confirmation branches continue there. The former soft `e_booked` confirmation exit is also replaced: confirmation delivery enters support and only 72-hour silence reaches `e_timeout`. The unreferenced `e_defer` node is removed.
- Assertion 15 checks the node contract, office referral, prompt budget, absence of extractors and slot templates, bounded terminal-only exits, no transitive path to `/availability` or `/sign`, both confirm routes, and complete removal of `e_defer` references.
- Added `post_booking_probe.py` for a later coordinator-run gated live task. It deliberately books, proves both post-booking turns answer with the office referral and without rebooking claims, then cancels all upcoming harness appointments and verifies zero remain. It was not run in this build task.

Round 15 does not alter the frozen extraction contract, scheduling hot-node prompts, or inherited prompt compression. The round-13 `extract` / prompt / `compress-context` notes and budgets below remain applicable.

## Regeneration and round-15 proof

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD20/gl-round14-fix/pathway-goalloop-draft.json
```

The round-15 draft and conformant fixture must pass. The untouched round-14 draft must fail with an `assertion 15` citation because it lacks `n_post_booking` and still references `e_defer`.

## Inherited round-14 evidence

## Measured v109 defect and deterministic fix

With Monday 08/17 offers standing, the live ask "What is the earliest I can do that day?" routed to the preference-based search. Extraction inconsistently emitted bare `monday`, which resolved to Monday 08/10 instead of the standing offered date, Monday 08/17. The offered-date search already pins its request `from` and `to` to the standing offer, so routing this ask there answers correctly regardless of extract output.

The `n_goal_response` to `n_goal_search_offered_time` edge label, and its mirrored description, now append exactly: ` - or asks for the earliest, soonest, or first available time on that date`.

Assertion 14 requires that offered-time edge label to contain `earliest`. Assertions 1 through 13 remain intact. No prompt compression changed this round; `compress-context` is inherited from round 13.

## Regeneration and round-14 proof

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD17/gl-round13-fix/pathway-goalloop-draft.json
```

The round-14 draft and conformant fixture must pass. The untouched round-13 draft must fail with an `assertion 14` citation because its offered-time edge label lacks `earliest`.

## Inherited round-13 evidence

## Live v108 defects and ground truth

Ankit's live phone test established Tuesday 08/18 offers, then asked, "What about Monday that week?" The extractor emitted `monday next week`, losing the reference to the already-discussed week. The intended date was Monday 08/17, the Monday in the week containing Tuesday 08/18.

The next message, "What is the earliest I can do that day?", produced spoken offers for Monday 08/10/2026 at 09:00 am and 09:15 am. Gateway ground truth shows those times do not exist; real 08/10 inventory begins at 11:15 am. The final slot variables still held 08/05 values, proving the response model composed dates and times outside the rendered slot templates.

## Round-13 changes

- Only the `preference_from` and `preference_to` descriptions in the frozen five-extractor set are extended. Relative forms such as `monday that week`, `the monday of that week`, and `monday the same week` now resolve against an established date and emit `monday the week of MM/DD/YYYY`. The canonical 08/18/2026 example is included. The identical set feeds `n_goal_ask`, `n_goal_response`, `n_mixed_intent`, `n_date_conflict`, `n_date_conflict_retry`, `n_gate_1`, and `n_gate_2`. The other three extractor descriptions remain unchanged.
- `n_goal_response` contains the `OFFER-INTEGRITY:` rule. Every offered date or clock time must be a literal rendered slot value; the response may not invent a value to answer the patient's request.
- All five availability webhooks map `from_unresolved` from `$.result.from_unresolved` and route true results to `n_goal_ask`. Both wait-stage prompts prohibit trusting or speaking returned slots when the requested start text was unresolved and ask plainly for the day.
- Assertion 13 checks both date extractor descriptions on every feeder, the offer-integrity marker, and every availability mapping. Assertions 1 through 12 remain active with their gateway and prompt-budget expectations updated for the round-13 contract.
- Round 13 preserves round 12's prompt-compression split rather than recombining the pre-offer and post-offer policies. The new unresolved-input sentence increases compressed `n_goal_ask` from 2,165 to 2,189 characters, still below its 2,200-character budget. The offer-integrity and unresolved-day paragraphs increase compressed `n_goal_response` from 2,517 to 3,017 characters, still below its expanded 4,100-character budget. `n_goal_ask` continues to contain no slot templates, while `n_goal_response` retains the protected offer templates and the existing bans on promises, waiting copy, and invented or non-slot clock times.

Prompt budgets after regeneration are measured by the validator: `n_goal_ask` is at most 2,200 characters and `n_goal_response` is at most 4,100 characters.

## Regeneration and proof

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD15/gl-round12-fix/pathway-goalloop-draft.json
```

The first command deterministically rewrites the draft, frozen extractor file, and fixtures from local snapshots. The round-13 draft and conformant fixture must pass. The untouched round-12 draft must fail with `assertion 13` citations because it lacks the anaphoric-week descriptions, `OFFER-INTEGRITY:` marker, and `from_unresolved` mappings.
# Round 23 - request-a-human routing

## Evidence and change

Fuzz messages such as `Can someone just call me instead?` and `Can I talk to the front desk?` stayed in scheduling because neither goal-loop wait node had a human-request route. Added the same explicit edge from `n_goal_ask` and `n_goal_response` to the existing `n_office` handoff, covering requests to speak with a person, call the office, talk to front-desk staff, or receive a phone call instead of texting.

`n_office` retains its `TIME-SILENT:` rule and its `(212) 219-2219` office number. `n_goal_response` now has nine outbound edges. The ninth edge is intentional: merging human handoff into correction, mixed-intent, decline, or another scheduling route would weaken disjointness and could reproduce the reported failure.

Assertion 23 retains assertions 1-22 and requires both exact human-request edges plus the office number and `TIME-SILENT:` marker in `n_office`. The assertion-22 response-edge ceiling is relaxed from eight to nine only for this added route.

Extraction remains on the current user-wait nodes. The established prompt split/compression and frozen extractor architecture are unchanged.

## Regeneration and proof

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD31/gl-round22-fix/pathway-goalloop-draft.json
```

Expected: the round-23 draft and conformant fixture pass. The untouched round-22 draft fails and cites `assertion 23` because both human-request edges are absent.

# Round 22 - adversarial-audit consolidation

## Audit disposition

1. Main offer router ambiguity: fixed. `n_goal_response` now has eight outbound edges. The correction and new-preference routes are one edge; gate labels accept only the first or second opening without clock-time clauses; named clocks use the offered-date anchor search; window, latest, named-time, correction, mixed-intent, decline, and selection labels are explicitly separated. The local timeout edge was removed to meet the hard eight-edge cap while retaining every patient-message intent route.
2. Time-unsafe support prompts: fixed. `n_mixed_intent`, `n_office`, and `n_faq` contain the literal `TIME-SILENT:` marker, contain no slot templates, and cannot state a clock time or date. Mixed intent says `the opening you selected`; office and FAQ return to scheduling with a question only.
3. Offered-anchor response ambiguity: fixed against the lane-50 gateway contract. `n_goal_search_offered_anchor` maps `$.result.anchor_route` and has exactly four exclusive equality rows: `exact` to `n_gate_1`, `closest` to `n_time_pick_offer`, and `none` or `error` to `n_goal_ask`. The `anchor_exact` response mapping remains only as reference; no routing row uses it.
4. Opt-out/wrong-person reachability: downgraded as a false positive. `n_suppress_stop` and `n_suppress_not_me` are Bland global nodes (`isGlobal: true`) and are reachable from anywhere without explicit incoming edges. Adding local edges would duplicate global behavior, so none were added.
5. Pre-offer overlap: fixed. The broad `n_goal_ask` search label excludes latest/end-of-day and near/named-clock asks.
6. Named-time offer overlap: fixed. `n_time_pick_offer` separates a different day/date from a different time on the offered date; its latter branch excludes latest/end-of-day, while acceptance requires `1`, `yes`, or the exact rendered time.
7. Confirmation catch-all overlap: downgraded as inherited production behavior outside the round-22 scheduling-router contract. No confirmation behavior changed.
8. Office/FAQ continuation: partially hardened within scope. Both prompts are now time-silent and ask to resume scheduling without reconstructing slots. Their inherited topology remains unchanged because round 22 did not authorize a support-router redesign.

## Contract and validator changes

- Every availability webhook body now has exactly eleven fields and adds only `"context_date":"{{slot_1_start}}"`. This lets the gateway resolve raw anaphoric extraction such as `Monday that week` against the standing offered week.
- Assertion 22 retains assertions 1-21 and checks the eleven-field contract, exclusive `anchor_route` table, absence of legacy `anchor_exact` rows, the eight-edge response cap, the single merged fresh-search edge, clock-free gate labels, and time-silent support prompts.
- Extraction remains distributed on the current user-wait node. Prompt splitting and compression remain as established in earlier rounds; no extractor, prompt/compress-context architecture, or frozen guard block was recombined.

## Regeneration and proof

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD29/gl-round21-fix/pathway-goalloop-draft.json
```

Expected: the round-22 draft and `fixture-conformant.json` pass. The untouched round-21 draft fails and cites `assertion 22`.
