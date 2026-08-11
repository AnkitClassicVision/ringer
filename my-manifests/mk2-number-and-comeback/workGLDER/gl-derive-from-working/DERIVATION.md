# Production-derived goal loop

## Sources and invariants

- Node configuration source: `workV93/build-v93/pathway-v93-draft.json`, served as v96.
- Topology source: `workV94d4/amend-reference-point/SPEC-v94-draft4.md`.
- The derivation is offline and deterministic. `derive_goalloop.py` reads the production graph, builds the three loop nodes, reconnects edges, proves every locked node equals its source JSON object, and prints `KEPT_VERBATIM=31 nodes`.
- No attach, mint, deploy, network, MCP, skill, or git action is performed.

## Per-node fate

| Source node | Fate | Target / basis |
|---|---|---|
| `n_identity` | kept-verbatim | same id and config |
| `n_appt_check` | kept-verbatim | same id and config |
| `n_ask` | collapsed-into-X | `n_goal_update`; extraction copied verbatim, opening moved unchanged to first `n_goal_response` path |
| `n_date_conflict` | kept-verbatim | same id and config; outbound search target reconnected through UPDATE |
| `n_date_conflict_retry` | kept-verbatim | same id and config; outbound search target reconnected through UPDATE |
| `n_miss_empty` | collapsed-into-X | `n_goal_response` |
| `n_miss_unread` | collapsed-into-X | `n_goal_response` |
| `n_miss_thin` | collapsed-into-X | `n_goal_response` |
| `n_miss_unbookable` | collapsed-into-X | `n_goal_response` |
| `n_clarify` | collapsed-into-X | `n_goal_response` |
| `n_miss_time` | collapsed-into-X | `n_goal_response` |
| `n_offer` | derived-from-Y-with-trims | `n_goal_response`; production offer config/prompt, waiting-promise clause removed, opening appended |
| `n_offer_2` | collapsed-into-X | `n_goal_response` |
| `n_offer_3` | collapsed-into-X | `n_goal_response` |
| `n_offer_near` | collapsed-into-X | `n_goal_response` |
| `n_which_intent` | collapsed-into-X | `n_goal_update` |
| `n_gate_1` | kept-verbatim | same id and config |
| `n_gate_2` | kept-verbatim | same id and config |
| `n_negotiate` | collapsed-into-X | `n_goal_update` |
| `n_search` | derived-from-Y-with-trims | `n_goal_search`; endpoint/options/response schema retained, request parameterized with goal relation, anchor, and bounds |
| `n_page_2` | collapsed-into-X | `n_goal_search` |
| `n_page_3` | collapsed-into-X | `n_goal_search` |
| `n_page_near` | collapsed-into-X | `n_goal_search` |
| `n_verify_1` | kept-verbatim | same id and config |
| `n_book_1` | kept-verbatim | same id and config |
| `n_verify_2` | kept-verbatim | same id and config |
| `n_book_2` | kept-verbatim | same id and config |
| `n_recheck` | collapsed-into-X | `n_goal_update` |
| `n_confirm` | kept-verbatim | same id and config |
| `n_help` | kept-verbatim | same id and config |
| `n_office` | kept-verbatim | same id and config |
| `n_faq` | kept-verbatim | same id and config |
| `e_safe_identity` | kept-verbatim | same id and config |
| `e_safe_failure` | kept-verbatim | same id and config |
| `e_booking_failed` | kept-verbatim | same id and config |
| `e_booked` | kept-verbatim | same id and config |
| `e_office` | kept-verbatim | same id and config |
| `e_declined` | kept-verbatim | same id and config |
| `n_suppress_stop` | kept-verbatim | same id and config |
| `e_stop` | kept-verbatim | same id and config |
| `n_suppress_not_me` | kept-verbatim | same id and config |
| `e_not_me` | kept-verbatim | same id and config |
| `e_existing` | kept-verbatim | same id and config |
| `e_timeout` | kept-verbatim | same id and config |
| `e_defer` | kept-verbatim | same id and config |
| `n_reconcile_1` | kept-verbatim | same id and config |
| `n_reconcile_2` | kept-verbatim | same id and config |
| `e_booked_recovered` | kept-verbatim | same id and config |
| `e_book_unknown` | kept-verbatim | same id and config |
| (new) `n_goal_update` | derived-from-Y-with-trims | silent shell and exact model options from `n_appt_check`; full `n_ask.extractVars` plus spec anchor/relation/time bounds |

## Edge derivation

Edges whose endpoints both survive are copied byte-for-byte. New and reconnected edges use the production custom-edge object shape. Webhook routes use executable labels such as `slot_count == 1`, never prose labels. The only unavoidable D6 edge change is its retired `n_search` target: it now goes through `n_goal_update`, which auto-advances to the sole `n_goal_search` webhook.

## Validator amendments

1. Replaced the generated 13-node identity set with the required 31 locked nodes plus three derived loop nodes.
2. Replaced the 48-to-13 contraction map assertion with direct source-object equality for all 31 locked nodes.
3. Changed exact loop adjacency to `n_goal_update -> n_goal_search -> n_goal_response -> n_goal_update`.
4. Retained the no-self-loop/fail-stay, mid-negotiation terminal, promise, clock-containment, singleton goal extraction, executable webhook-condition, and placeholder-producer gates.
5. Allowed only production-proven terminal sources already present in the locked graph. Fixture B still proves a new UPDATE-to-terminal edge fails.
6. D6's two locked nodes contain narrow local date `extractVars`. They are excluded only from the singleton *full scheduling-goal extraction* count; adding another goal extractor still fails fixture E.
7. Several locked production prompts contain the historical waiting sentence. Removing it would violate byte identity. The promise gate therefore covers all three derived nodes, while locked nodes are governed by exact source equality. `n_goal_response` trims that sentence, so derived patient-facing behavior introduces zero banned promises.
8. Fixtures were rebased onto the derived topology. Their behavior is unchanged: conformant is green; A self-loop, B negotiation terminal, C promise, D clock, and E duplicate extraction are red.

## Verification commands

```text
python3 derive_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
for f in fixture-*.json; do python3 check_goalloop_graph.py --draft "$f"; done
```
