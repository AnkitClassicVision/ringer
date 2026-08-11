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
