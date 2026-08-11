# Wayfinder map — Mott scheduling structural fix

Label: `wayfinder:map` (local-markdown tracker — no issue tracker configured for this repo).
Charted 2026-08-03 by the diagnosis session; worked by fresh sessions per the protocol in
`/home/ankit114/.claude/plans/1-shoudl-we-jsut-floating-wigderson.md` (the approved plan — read it
first, it holds the full context, evidence, and Ankit's four locked rulings).

## Destination

A pathway version live on 509 where dates resolve correctly including corrections ("the following
Thursday"); clock times can never be stated without fresh slot variables (validator-enforced);
every answer reaches the handset in ≤15s measured end-to-end; "last slot of the day" gets a
truthful answer — all proven by the live harness plus the 33-scenario regression suite, and every
decision recorded so CVC re-applies it without redesign.

## Notes

- Fable as brain; ALL execution through Ringer (`run_name` `mk2-number-and-comeback`).
- Standing gates: unattached mints only; Ankit flips; no booking retry ever; no sustained harness
  load against the live gateway during business hours (Mon 11:00–17:30 ET, Tue–Fri 10:30–17:30).
- One ticket per session (research tickets may run in parallel as Ringer lanes).
- Tickets live as sections in `WAYFINDER-TICKETS.md` beside this file; claim by writing your
  session date on the ticket's `claimed:` line; close by moving its gist to Decisions-so-far here.

## Decisions so far

- Baseline (2026-08-03 evening, fable-chief session): 33-scenario regression vs live v92 = 32/33.
  Sole failure "texting shorthand for next tuesday" is DETERMINISTIC (3/3 probe reruns):
  preference_to extracts 'friday next week' instead of 'tuesday next week'; offered slots were the
  correct Tuesday, so patient-invisible. Introduced v88–v92 (v87 was 33/33 same-day). v93 must
  either restore point extraction for single-day shorthand or Ankit re-rules the expectation.
  Evidence: workC92/regression-v92-phase1/transcript.txt, workC92flake/*/probe.txt.
- Ruling: interpretation stays HYBRID (pathway extracts + gateway re-interprets) — Ankit 2026-08-03.
- T2 RULED (Ankit, 2026-08-03 late): clarify-on-week-disagreement table APPROVED — agree/one-answers
  → proceed; week-level disagreement → ONE clarifying question with both dates; day-part-only →
  search whole day; raw unreadable → pathway fallback; all abstain → clarify. Max one clarify per
  conversation. Implementation stays EXPLORATION-ONLY for now (Ankit: change nothing yet);
  wiring study running as workT2x → feeds T3 spec. T3 now unblocked for spec-writing.
- Ruling: invention-proofing = structural containment + validator AND a Bland node-model bakeoff.
- Ruling: latency budget ≤15s end-to-end, accuracy kept (filler message dies).
- Ruling: scope = Mott now, CVC-ready; CVC execution out of scope.

## Not yet specified

- Prompt-rewrite scope across ~20 conversational nodes (waits on T3's containment rule).
- Whether n_page_near's band should differ from n_page_2's afternoon duplicate.
- Chinese copy parity for new/changed sentences.
- CVC re-application plan (graduates only after the destination ships).

## Out of scope

- CVC execution; voice channel; booking retry/idempotency (no idempotency key exists — refused);
  resident EMR client rewrite (CPU fix already took calls 8s→2s).

- T1 CLOSED (2026-08-03): "following Thursday"→08/06 is BOTH a resolver vocabulary gap (no
  `following <weekday>` pattern — proven on prod and snapshot) AND the deployed extractor dropping
  the negation (proven by controlled live replay: fresh chat ending "No the following Thursday"
  resolved 08/06 over a Friday sentinel). Deployed image runs OLDER extractor code than the 07-29
  snapshot — deploy-provenance drift; T9 must ship current source. Fix set + 12-case eval
  extension in workT1r3/t1-final-analysis/. T5 (interpreter bakeoff) now unblocked.
- GATEWAY FIX SHIPPED (2026-08-03 ~20:15 ET, Ankit-approved): T1's fix set + offer-relative
  correction semantics deployed to production as image mott-lane-36 / taskdef
  mott-booking-gateway:51 (cloned from :50, CPU upgrade preserved; service stable 1/1).
  Method: prod file extracted from ECR layers (no local runtime existed), three fixes + the
  correction rule rebased onto the byte-exact prod base, proofs green (12/12 corpus, zero
  unintended diffs vs prod behavior, incident replay 08/13), image assembled via ECR API with
  base layers untouched, pushed file BYTE-VERIFIED by re-extraction before deploy. Live-verified:
  following thursday→08/13, plain thursday→08/06 unchanged, following friday→08/14, exact
  incident correction replay→08/13 (no 08/06); gate_booked fresh-proven on v92 (e_defer,
  cleanup 0). Full production delta: 103 diff lines (workGWdeploy/img-verify/full_delta.diff).
  ROLLBACK: aws ecs update-service --cluster stack2 --service mott-booking-gateway
  --task-definition mott-booking-gateway:50. Semantic ruling made by the session (T2 may
  overrule): correction "no (the) following X" = offered X + 7 days, calendar fallback.
  Post-ship 33-scenario regression: 32/33 — IDENTICAL to the pre-ship baseline, same sole
  known extraction quirk, zero new failures. Deploy fully validated.
  Provenance: RESOLVED — prod-as-extracted + shipped fix committed (1d0db1f, 7e20fb1) and pushed
  to github.com/AnkitClassicVision/cvc-booking-gateway branch prod-truth-2026-08-03 with the
  deploy record doc; reconciling that branch vs the repo's stale main is a named T8/T9 follow-up.
- GATEWAY LANE-37 SHIPPED (2026-08-04 ~00:00 ET): weekday-ordinal compound rule live as taskdef
  :52 (byte-verified chain; rollback :51). Live convergence gate green: the full incident
  sequence runs clarify → "Friday the 14th" → 08/14 offer, no second question. Commit 3rd on
  prod-truth-2026-08-03 branch.
- PATHWAY v94 MINT FLIP-READY (2026-08-04): D6 conflict-convergence draft green under the
  deliberately amended validator ([35] fail-stay illegal, [36] n_search pinned to two
  conflict-display entries); fail-open proven; regression 32/33 = live baseline; live
  convergence proven with lane-37 gateway. AWAITS ANKIT'S DASHBOARD FLIP (92 → 94).
  Quarantined mints: Bland v93 (filler-test) and nothing else; rollback = flip back to 92.
- T7 RULED + GENERALIZED (Ankit, 2026-08-04): reference-point search is the primitive — goal
  carries anchor (day-open/day-close/noon/any clock time) + relation (nearest/before/after);
  one gateway ordering rule returns the top two slots by anchor distance. Subsumes latest-slot,
  first-appointment, around-noon, before/after-X; band machinery becomes anchor presets and the
  "before":"none" gap dies with it. Ships with the goal-loop build; v94's interim office-punt
  stands until then (safe, known).
- GOAL-LOOP DAY-1 OUTCOME (2026-08-04 ~12:30 ET): five debug rounds, five runtime-convention
  classes found and encoded as validator assertions (executable edge conditions; silent
  processors; no generated guards; template-literal offers; slot-variable producers). Round-5
  smoke RED - the derived search webhook does not execute/populate at runtime (literal
  {{slot_1_start}} reached a test patient; hallucinated 2018/2024 dates elsewhere) - HARD STOP
  honored, evening flip CALLED OFF, no round 6 same-day. Line floor: v96 + lane-38 (all gateway
  capabilities proven live incl. booked-slot exclusion). Next session: platform-level response
  diff (live v96 n_search turn vs loop mint turn, full raw envelopes) BEFORE any further fix -
  see the handoff doc in the session scratchpad and workGLMS5/workGLD3 artifacts.
- GOAL-LOOP BUILD APPROVED AND STARTED (Ankit, 2026-08-04 ~09:15 ET, "approved plan"): v96 stays
  live as today's floor (referral beats ghosting; monitor active); the goal-loop build runs from
  SPEC-v94-draft4 via three parallel builders (its own validator with incident-derived gates
  incl. no-terminal-from-valid-state and SEMANTIC promise ban; deterministic graph generator;
  37+ scenario harness encoding this week's four live incidents). Unattached mint via T8
  discipline, full ladder after 17:30, Ankit flips tonight. Morning incidents driving it:
  Tuesday-the-18th terminated by the D7 terminal (design error: exits honest, entries unnarrowed)
  and the model paraphrasing a banned promise ("Checking availability for...") — exact-string
  bans don't hold against generative copy; the new validator bans the semantic class.
- ARCHITECTURE RULED (Ankit, 2026-08-04): persistent-GOAL loop replaces scenario routing —
  goal refines, never resets, until satisfied. SPEC-v94-draft2 (workV94goal): 14 nodes from 48,
  UPDATE→ATTEMPT→RESPOND spine, structural convergence, 3 open questions w/ defaults. Awaits
  Ankit's spec review; build is the next cycle, not tonight.
- T5 CLOSED (2026-08-03): interpreter bakeoff verdict — model swap KEEP-OUT for the
  following-<weekday> defect class. Raw 4/12 (weekday-dependent incoherence); Haiku 0/12 @983ms;
  Sonnet-4-6 0/12 @1092ms — the zero is structural (picked phrases feed resolve_relative_date,
  which lacks the pattern; a perfect pick still resolves NONE). Prod runs LLM intent
  AUTHORITATIVE (taskdef :50) yet its NONE falls through to raw — full incident mechanism now
  coherent. Ship T1's fix; re-run the same manifest post-fix if picker quality still matters.
- T4 CLOSED (2026-08-03): node-model bakeoff verdict KEEP-OUT. No documented API path to a named
  model (11 citations); the one lever (`use_candidate_model` on chat create) produced identical
  routing, identical offers, and noise-level latency deltas on all 3 frozen misroute cases.
  Misroute cures live in prompts/gateway (T1/T3), not the node model. Named-Sonnet = Bland-rep
  conversation if Ankit wants it. Bonus: second filler variant "Let me check that for you."
  found (T9 strips both); chat-mode correction already clarifies with the right example date
  (input to T2).
- T6 MEASURED (2026-08-03): real-conversation waterfall proves the filler lands 10.5–11.8s after
  the patient's text, 0.33s before the real answer — pure waste (median 7.7s, p95 12.2s record-
  side; carrier hop unmeasured). Filler stripped (REMOVED=20), minted unattached as v93-test,
  A/B parity proven (identical routing/offers). Production strip ships via T9 with a deliberate
  update to the pinned ABSOLUTE-RULE paragraph assertion; post-flip SMS re-measure goes in the
  flip packet.

## Frontier (open, unblocked)

T2 grilling (HITL) · T4 bakeoff · T5 interpreter bakeoff · T6 latency task · T7 grilling (HITL) · T8 guard task

## Blocked

T3 containment spec (by T2) · T9 build v93 (by T3; T1 research done, its fix ships in T9)

Full ticket bodies: `WAYFINDER-TICKETS.md`.
