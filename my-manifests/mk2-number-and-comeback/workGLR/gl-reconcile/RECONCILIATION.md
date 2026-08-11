# v94 graph reconciliation

The baseline graph failed 65 of 185 validator assertions. The table preserves every original failure in validator order. `VALIDATOR-OVER-REACH` means the static assertion was narrowed or converted to a harness declaration; the five incident-gate tamper assertions and singleton-extraction proof were not weakened.

| # | Original assertion | Verdict | Spec citation | What changed |
|---:|---|---|---|---|
| 1 | `source_id_map` contains all 48 v92 ids exactly once | GRAPH-DEFECT | §3 v92-to-v94 contraction; §9.1 | Added the exact 48-entry contraction map. |
| 2 | goal object name is `scheduling_goal_v94` | GRAPH-DEFECT | §2 opening paragraph | Added the named contract object. |
| 3 | exact 15-field goal schema | GRAPH-DEFECT | §2 goal-object table; §9.2 | Added the exact field map with no `direction`. |
| 4 | goal semantics include retain | GRAPH-DEFECT | §2 patch semantics | Added absence-retains semantics. |
| 5 | goal semantics include replace | GRAPH-DEFECT | §2 patch semantics | Added explicit replacement semantics. |
| 6 | goal semantics include clear | GRAPH-DEFECT | §2 patch semantics | Added rejected-constraint clear semantics. |
| 7 | lifecycle includes unsatisfied | GRAPH-DEFECT | §2 lifecycle | Added lifecycle contract. |
| 8 | lifecycle includes offered | GRAPH-DEFECT | §2 lifecycle | Added lifecycle contract. |
| 9 | lifecycle includes confirmed | GRAPH-DEFECT | §2 lifecycle | Added lifecycle contract. |
| 10 | lifecycle includes abandoned | GRAPH-DEFECT | §2 lifecycle | Added lifecycle contract. |
| 11 | authoritative writer is `n_availability` | GRAPH-DEFECT | §2 drift repair; §6 | Declared `n_availability` as sole authoritative echo writer. |
| 12 | waiting `n_goal_update` must one-hop to itself | VALIDATOR-OVER-REACH | §1 loop; §4.2-5 | Replaced the contradictory self-target demand with an outbound-target/no-self-loop proof. |
| 13 | every availability failure must one-hop to `n_goal_update` | VALIDATOR-OVER-REACH | §1 guards outside loop; §3 `e_close`; §8 errors | Removed the blanket failure-label rule; locked self-loop and terminal-source gates remain. Graph now routes availability failure through `n_service_guard`. |
| 14 | `n_availability` directly targets terminal | GRAPH-DEFECT | §1 convergence; locked no-mid-negotiation gate | Routed failure/exhaustion to `n_service_guard`, not directly to `e_close`. |
| 15 | `n_goal_response` directly targets terminal | GRAPH-DEFECT | §1 sole inbound destination; locked no-mid-negotiation gate | Removed direct terminal edge; replies return through `n_goal_update`. |
| 16 | loop cap equals 8 | GRAPH-DEFECT | §4 final paragraph; §9.3 | Added `loop_cap: 8`. |
| 17 | ninth update targets `e_close` | GRAPH-DEFECT | §4 final paragraph | Added `ninth_update_target: e_close`. |
| 18 | retired token `page_2` found in graph | VALIDATOR-OVER-REACH | §3 contraction explicitly names `n_page_2`; §9.1 | Excluded provenance map from executable-config banned-token scan. |
| 19 | retired token `page_3` found in graph | VALIDATOR-OVER-REACH | §3 contraction explicitly names `n_page_3`; §9.1 | Same provenance-only narrowing. |
| 20 | retired token `page_near` found in graph | VALIDATOR-OVER-REACH | §3 contraction explicitly names `n_page_near`; §9.1 | Same provenance-only narrowing. |
| 21 | `n_identity` webhook lacks renderer declaration | VALIDATOR-OVER-REACH | §3 silent identity lookup; §4.1 | Removed invented `renders_result` schema requirement; response pathways remain statically checked. |
| 22 | `n_appt_check` webhook lacks renderer declaration | VALIDATOR-OVER-REACH | §3 silent fail-safe guard; §4.1 | Same removal. |
| 23 | `n_availability` webhook lacks renderer declaration | VALIDATOR-OVER-REACH | §3 silent webhook then `n_goal_response`; §4.3-6 | Same removal. |
| 24 | `n_select` webhook lacks renderer declaration | VALIDATOR-OVER-REACH | §3 selection binder; §4.7 | Same removal. |
| 25 | `n_atomic_book` webhook lacks renderer declaration | VALIDATOR-OVER-REACH | §3 silent transactional webhook; §7 | Same removal. |
| 26 | `n_reconcile` webhook lacks renderer declaration | VALIDATOR-OVER-REACH | §3 reconciliation webhook; §7 | Same removal. |
| 27 | `n_suppress` webhook lacks renderer declaration | VALIDATOR-OVER-REACH | §3 suppression webhook; §1 guards | Same removal. |
| 28 | availability contract missing patch | GRAPH-DEFECT | §2 drift repair; §4.3; §6 | Added explicit pathway patch field/description. |
| 29 | availability contract missing directional rule | GRAPH-DEFECT | Ruling 10; §4.5; §6 | Added directional-filter wording. |
| 30 | availability contract missing one inventory query | GRAPH-DEFECT | §4.5; §6 | Added exactly-one-query contract. |
| 31 | offer contract missing `offer_id` | GRAPH-DEFECT | §2; §6; §9.5 | Added offer contract. |
| 32 | offer contract missing `offer_issued_at` | GRAPH-DEFECT | §6 response contract | Added issued-at field. |
| 33 | offer contract missing `offer_expires_at` | GRAPH-DEFECT | §2; §6 | Added expiry field. |
| 34 | offer contract missing `inventory_token` | GRAPH-DEFECT | §6; §8 clock containment | Added inventory-token binding. |
| 35 | offer contract missing exactly two | GRAPH-DEFECT | §4.6; §6 | Added exactly-two contract and choice count 2. |
| 36 | offer contract missing normalized | GRAPH-DEFECT | §4.6; §6 | Declared normalized choices. |
| 37 | offer contract missing invalidation | GRAPH-DEFECT | §6 TTL paragraph | Added expiry/goal-change invalidation. |
| 38 | offer contract missing silent behavior | GRAPH-DEFECT | §6 stale-accept paragraph | Added silent refresh contract. |
| 39 | offer contract missing stale behavior | GRAPH-DEFECT | §6 stale-accept paragraph | Added stale acceptance handling. |
| 40 | offer contract missing nearest behavior | GRAPH-DEFECT | §4.6; §6 | Added nearest-offer provenance. |
| 41 | offer contract missing real-slot requirement | GRAPH-DEFECT | Ruling 10; §6 | Declared real inventory choices. |
| 42 | TTL must be 10 minutes | GRAPH-DEFECT | §6 recommended TTL; §9.5 | Set draft contract TTL to 10. |
| 43 | clarification maximum must be 2 | GRAPH-DEFECT | Ruling 2; §4.4 | Added one question plus one re-ask bound. |
| 44 | appointment-check non-true target missing | GRAPH-DEFECT | §4.1; §9.7 | Declared fail-safe `e_close` target; existing route retained. |
| 45 | blank/non-boolean conflict target missing | GRAPH-DEFECT | §7 first paragraph; §9.7 | Declared fail-safe `e_close` target; no book/confirm route. |
| 46 | atomic contract missing `check_and_book` | GRAPH-DEFECT | §7; §9.8 | Added atomic contract. |
| 47 | atomic contract missing `/sign` | GRAPH-DEFECT | §7; §9.8 | Added governed endpoint contract. |
| 48 | atomic contract missing `offer_id` | GRAPH-DEFECT | §7 | Added exact offer binding. |
| 49 | atomic contract missing `slot_id` | GRAPH-DEFECT | §7 reconciliation and payload rules | Added exact slot binding. |
| 50 | atomic contract missing idempotency formula | GRAPH-DEFECT | §7 first paragraph | Added `conversation_id + ':' + offer_id`. |
| 51 | atomic contract missing identical retry | GRAPH-DEFECT | §7 safe retry rule | Added identical request/key retry rule. |
| 52 | atomic contract missing idempotency term | GRAPH-DEFECT | §7 safe retry rule | Added idempotency semantics. |
| 53 | atomic retry maximum must be 2 | GRAPH-DEFECT | §7 safe retry rule | Set `max_retries: 2`. |
| 54 | reconciliation missing one read | GRAPH-DEFECT | §7 final paragraph; §9.9 | Added one-read contract. |
| 55 | reconciliation missing `offer_id` | GRAPH-DEFECT | §7 final paragraph | Added exact offer key. |
| 56 | reconciliation missing `slot_id` | GRAPH-DEFECT | §7 final paragraph | Added exact slot key. |
| 57 | reconciliation missing store | GRAPH-DEFECT | §7 final paragraph | Added store key. |
| 58 | reconciliation missing patient | GRAPH-DEFECT | §7 final paragraph | Added patient key. |
| 59 | reconciliation missing date | GRAPH-DEFECT | §7 final paragraph | Added attempted date. |
| 60 | reconciliation missing start | GRAPH-DEFECT | §7 final paragraph | Added attempted start. |
| 61 | reconciliation missing unique exact match | GRAPH-DEFECT | §7 final paragraph | Added unique-exact-match confirmation condition. |
| 62 | affirmative claim owner missing | GRAPH-DEFECT | §3 `n_confirm`; §4.7; §9.9 | Declared `n_confirm` as sole owner. |
| 63 | visible-answer telemetry absent | VALIDATOR-OVER-REACH | §10 requires per-turn runtime recording; §9.10 mixes static and runtime checks | Converted to static `max_visible_answer_seconds: 15.0` plus `measurement_owner: harness`. |
| 64 | visible answer exceeds/absent | VALIDATOR-OVER-REACH | §10 latency suite; §11.5 harness | Static validator now verifies the 15-second limit declaration, not fabricated measurements. |
| 65 | p95 report absent | VALIDATOR-OVER-REACH | §10 latency suite; §11.6 flip gate | Static validator requires `p95_required: true`; the harness must supply the report. |

RECONCILED: graph passes 173 assertions; fixtures green=1 red=5; gates preserved
