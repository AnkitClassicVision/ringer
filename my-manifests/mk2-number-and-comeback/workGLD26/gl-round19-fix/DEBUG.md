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
