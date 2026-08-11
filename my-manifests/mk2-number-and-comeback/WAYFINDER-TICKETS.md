# Wayfinder tickets — Mott scheduling structural fix

Child tickets of `WAYFINDER-MAP.md`. Claim by filling `claimed:`; close by posting `## Resolution`
under the ticket and adding a one-line gist to the map's Decisions-so-far.

---

## T1 · wayfinder:research (AFK) — Why did raw_resolve produce 08/06 for "No the following Thursday"?
claimed: 2026-08-03 fable-chief session
blocked-by: —

### Question
Reproduce against the deployed resolver with the exact message sequence of conversation
`782f4dce-5e90-446f-a886-c000f1c240b7` (2026-08-03 20:40–21:02Z; gateway logged
`raw_fetch msgs=11 → raw_resolve from=08/06/2026 → date_source=raw` at 20:58:06Z while pathway
extraction correctly held `preference_from="thursday next week"`). Is the defect in phrase-picking
(LLM chooses "thursday" over the correction) or resolver vocabulary ("the following <weekday>"
missing)? Extend the eval corpus with the `following <weekday>` family and correction-after-offer
cases. Sources: `../mott-raw-text/work2/raw-text-authority-v2/bland_gateway.py`,
`../mott-llm-intent/work2/llm-intent-v2/`, log group `/ecs/mott-booking-gateway`.

### Resolution (2026-08-03, fable-chief session — all evidence executed under Ringer)
**Verdict: BOTH layers, plus a deployment-provenance drift.**
1. **Resolver vocabulary gap (proven on prod AND snapshot):** deployed `/availability` rejects
   `from="the following thursday"` as unrecognized (HTTP 409) while `thursday`→08/06 and
   `thursday next week`→08/13; snapshot isolation table identical (STAGE2 lines). No pattern for
   `(the) following <weekday>` exists — falls to bare-weekday.
2. **Deployed extractor drops the negation (proven by controlled live replay):** a fresh chat
   ending in exactly "No the following Thursday", resolved by the deployed raw authority via
   callID, returned count=26 dates=08/06/2026 over a Friday sentinel (workT1race/*/race.txt).
   The 07-29 snapshot's `extract_date_from_text` instead returns NONE for that text (negation
   guard) — so the ECS image runs OLDER extractor code than the snapshot. Incident mechanism:
   extractor reduced the correction to bare "thursday" → 08/06 → raw authority silently won.
3. **Fix set** (workT1r3/t1-final-analysis/report.md): add `(?:the )?following (<weekday>)` →
   `calendar_weekday(weekday, 1)` before the bare-weekday branch (~line 600); make multi-token
   matches occupy their span before one-token windows in `extract_date_from_text`; narrow
   correction-context negation (`^no\s+(?:the\s+)?following\s+<weekday>$`) without unguarding
   `no Friday works`. Eval extension: 12 cases incl. the incident (eval_cases.json, check-passed).
4. **Flag for T9/deploy:** rebuild+redeploy must ship the CURRENT gateway source; the image
   predates the snapshot's negation guard — some July fixes are plausibly not live.
claimed-status: CLOSED (research complete; fix lands via T9 build + gateway deploy)

---

## T2 · wayfinder:grilling (HITL, Ankit) — The hybrid agreement protocol
claimed:
blocked-by: —

### Question
Ankit ruled interpretation stays hybrid. When pathway extraction and gateway authority disagree on
the resolved date, who wins — and when does the system instead ask the patient ONE clarifying
question (the restored n_date_conflict pattern) rather than silently picking? Tonight the
authority silently won and was wrong. Deliverable: a decision table (agree → proceed; disagree on
week → clarify; disagree on day-part → X; authority unreadable → Y) that T3's prompts and the
gateway change implement.

---

## T3 · wayfinder:prototype (HITL) — Time-authority containment spec
claimed:
blocked-by: T2

### Question
Which nodes may state clock times (offer nodes fed by fresh slot variables — enumerate them), what
do all other prompts say instead (route time questions to search: fail-open-to-search, never
fail-stay), and what are the validator assertions + harness fuzz scenarios ("morning-only reply"
must reach search; invented-time detector: every clock time in any agent message must exist in the
gateway inventory for the queried window)? Produces the spec section and check code that T9 builds
against. Root incident: agent invented "9:30 AM" for 08/12 (first real slot 10:45) with no
availability call — conversational node held a time question the router never moved.

---

## T4 · wayfinder:research (AFK) — Bland node-model bakeoff
claimed: 2026-08-03 fable-chief session
blocked-by: —

### Question
Current Bland node model vs available smarter options (Sonnet-class) on the measured misroute
cases — time-of-day-only replies, ASAP phrasing ("the first available time works"), corrections
("No the following Thursday") — scored on routing accuracy AND per-turn latency. Run as a Ringer
bakeoff per the model-bakeoff gate (frozen scenarios, anonymized scoring, first-try rates). Output:
promote/keep-out verdict for the node model, with numbers.

### Resolution (2026-08-03, fable-chief session)
**Verdict: KEEP-OUT — no measurable win from the only API-reachable smarter model.**
- Feasibility first (workT4docs, 11 quoted citations): Bland documents NO named model field on
  pathway versions, nodes, or SMS config; the production graph confirms it (modelOptions carry
  only retryAttempts/skipUserResponse/newTemperature). The only documented lever is
  `use_candidate_model: true` on pathway-chat create — an unnamed "experimental model version";
  SMS enablement is Enterprise/rep-gated. Named Sonnet-class = a Bland-rep conversation, Ankit's
  call, not an API field.
- Operational-lane bakeoff, current vs candidate, 3 frozen misroute cases × both (workT4run):
  IDENTICAL routing (daypart → n_ask→n_offer_2; asap → n_offer first-available 08/04 10:45;
  correction → clarify question at n_offer), identical offers, copy differs by one phrase,
  latency within noise (22.4 vs 22.5s / 11.9 vs 11.2s / 16.8 vs 17.6s). Caveat stated honestly:
  the flag was accepted (candidate=1 on record) but nothing external verifies the model actually
  switched — either way, no measurable benefit exists to promote.
- The misroute cures live in prompts/gateway (T1 fix, T3 containment), not in a smarter node
  model. Sample: 1 run per cell, chat-mode; sufficient for keep-out given zero deltas, would not
  be sufficient for a promote.
- Bonus findings for T9: a SECOND filler variant "Let me check that for you." exists in the graph
  (1 occurrence, survived the T6 strip — strip both variants); chat-mode correction handling asks
  a clarifying question whose example ("August 13") is the correct date — direct input for T2's
  clarify-vs-pick table.
claimed-status: CLOSED (keep-out; revisit only if Bland exposes a named model or Ankit opens the rep conversation)

---

## T5 · wayfinder:research (AFK) — Gateway interpreter bakeoff (Haiku vs Sonnet)
claimed: 2026-08-03 fable-chief session (unblocked by T1 closure; running as workT5)
blocked-by: — (was T1, closed)

### Question
On the T1-extended corpus, does Sonnet beat Haiku 4.5 (`ECP_LLM_MODEL_ID`) at phrase-picking
(never date arithmetic — the deterministic resolver computes)? Include latency and cost deltas per
call. Answers Ankit's "maybe sonnet resolves this" with evidence; a model swap is one env var.

### Interim (2026-08-03, fable-chief session) — instrument ready, LLM lanes blocked on IAM
- Eval harness built and proven (workT5/t5-eval-builder/eval_ext.py: raw path executed offline in
  the check; replays the 12-case T1 corpus through resolve_from_conversation, Haiku pick, Sonnet
  pick with per-case correctness + Bedrock latency; silent-failure guard = median-latency floor).
- **Raw path (deployed style): 4/12 on the correction/following-family corpus** — the quantified
  "main issue" (workT5r3/t5-eval-haiku3/haiku.txt).
- Production config discovered (workGWenv): taskdef mott-booking-gateway:50, image
  eyecloud-fargate-runner:mott-lane-35, ECP_LLM_INTENT=**authoritative**, model Haiku 4.5,
  ECP_RAW_TEXT_DATES=1 — THREE interpreters live; incident turn logged date_source=raw, so the
  raw authority outranked the authoritative LLM layer. Key input for T2.
- BLOCKED: every local AWS identity (mybcat-account-readonly, SSO connect_full via `admin`
  profile) lacks bedrock:InvokeModel (AccessDeniedException on record, workBRprobe + workT5r3).
  Bedrock catalog confirms us.anthropic.claude-sonnet-5 / claude-sonnet-4-6 profiles exist.
  Needs Ankit: grant bedrock:InvokeModel on the Anthropic inference profiles to a local identity,
  then rerun manifest-t5-r3.json unchanged.
claimed-status: CLOSED — see final resolution below.

### Final resolution (2026-08-03, after Ankit's Bedrock grant; workT5r4, real calls proven by latency floor)
**Verdict: MODEL SWAP KEEP-OUT for this defect class — the resolver vocabulary is the binding
constraint, not the picker model.**
- Raw path: 4/12. Per-case record shows the incoherence: following Monday/Tuesday/Wednesday/
  Saturday resolve to NEXT week (correct) while following Thursday/Friday/Sunday resolve to THIS
  week (wrong) — same phrasing family, weekday-dependent outcomes.
- Haiku 4.5: 0/12, median 983ms/pick. Sonnet (us.anthropic.claude-sonnet-4-6): 0/12, median
  1092ms/pick. Both are REAL calls (latency floor enforced). The zero is structural: the eval —
  like the production pipeline — feeds the picked phrase into resolve_relative_date, which has no
  `following <weekday>` pattern, so a PERFECT pick still resolves to NONE. No picker model can
  rescue a vocabulary gap downstream of it.
- Production coherence: prod runs ECP_LLM_INTENT=authoritative (Haiku) — its NONE on this family
  falls through to the raw authority, which then decides (date_source=raw) and is wrong on the
  Thursday-type cases. Exactly the incident.
- Cost/latency: the LLM pick layer adds ~1s per turn regardless of model; Sonnet is not faster.
- Answer to "should we just use Sonnet?": NO for this bug — ship T1's resolver+extractor fix
  first. Re-run this same corpus post-fix (manifest-t5-r3.json, one command) if a picker-quality
  question remains; sonnet-5 responded to a direct probe but the eval's model-probe fell back to
  sonnet-4-6 (transient; immaterial to the verdict).

---

## T6 · wayfinder:task (AFK) — End-to-end latency instrumentation + streamline
claimed: 2026-08-03 fable-chief session
blocked-by: —

### Question
Measure send→handset-delivery per message class to decompose Ankit's experienced ~40s truthfully
(server-side turns measured 3–12s; suspects: two-message "Let me check…" pattern = two LLM
generations + two SMS, carrier delivery). Then remove the filler message (one answer per turn) and
re-measure against the ≤15s budget. Any turn still over budget gets an itemized breakdown.

### Resolution (2026-08-03, fable-chief session — measurement complete; build ships via T9)
1. **Waterfall of the real conversation** (workT6run/t6-timing-run/): single-answer turns
   3.3–4.6s; filler+answer turns 10.5–11.8s to the FIRST message with the real answer only 0.33s
   behind it — the filler reassures nobody and costs a second SMS. TWO_MSG_TURNS=3/6; SUMMARY
   median 7.7s, p95 12.2s (record-side). UNMEASURED, stated honestly: gateway per-turn (chat id
   absent from CloudWatch lines) and carrier delivery to handset.
2. **Filler stripped deterministically**: 20 occurrences of "One moment while I check the
   schedule for you." removed (workT6mint/t6-strip-builder, REMOVED=20, structure asserted);
   minted UNATTACHED as version 93 (nothing points at it).
3. **A/B parity proven** (workT6m3): identical routing and identical offers on v92 vs the
   stripped mint across the scripted turns; chat mode shows no two-message pattern on either side,
   so the SMS latency/message-count delta is only provable post-flip — the flip packet must
   include a live SMS re-measure (same waterfall script, fresh conversation).
4. **Quarantine + T9 requirement**: the canonical validator correctly rejects the strip because
   the filler sentence sits inside the pinned v86 "ABSOLUTE RULE ON TIMES" paragraph (assertion
   [30] × many nodes). Production v93 must be built through the transform chain
   (transform_v92 + strip step) with a DELIBERATE assertion-text update — an Ankit-visible
   canonical-copy change, not a validator bypass. Version-93-test is measurement-only.
claimed-status: MEASURED (production build + assertion update land in T9; post-flip SMS re-measure in flip packet)

---

## T7 · wayfinder:grilling (HITL, Ankit) — "Last slot of the day" capability
claimed:
blocked-by: —

### Question
How should "what's the last slot on <day>" answer — the true last slot of the day, or the last two
of the late band — with what copy, and does the earliest-in-band-then-page offer progression stay
as the default flow? Incident: asked for the last slot on 08/06, agent offered 3:00/3:15 (first of
late band); true last was 5:15 pm.

### Resolution (2026-08-04, Ankit ruling via AskUserQuestion)
**RULED: TRUE LATEST SLOTS.** The patient gets the day's actual last two slots in the standard
reply-1-or-2 pattern ("The latest I have Friday 08/14 is 5:15 pm, and before that 5:00 pm.
Reply 1 or 2 to take one, or tell me another day or time."). Earliest-in-band-then-page stays the
default flow for ordinary asks; last/latest phrasings set the goal object's direction=latest and
the availability funnel returns latest-first. Implementation: small gateway ordering flag + the
direction field in the goal-loop spec (SPEC-v94-draft3); ships with the goal-loop build. Field
evidence: Ankit hit the v94 office-punt live on 2026-08-04 (~03:25Z, conversation 20b70337…);
punt confirmed safer-than-wrong but leaks bookings to phone staff — hence option A.
claimed-status: RULED (build lands with the goal-loop pathway)

### Generalization (Ankit, 2026-08-04, minutes after the ruling)
The same must hold for ANY temporal reference point — "first appointment", "around noon",
"closest to 2", "before my shift at 10" — not just latest. Model: the goal object carries
anchor (day-open | day-close | noon | any clock time) + relation (nearest | before | after);
ONE gateway ordering primitive sorts real slots by distance from the anchor with the directional
filter and returns the top two. Consequences: T7's direction field is subsumed; the
morning/afternoon/late band machinery becomes three anchor presets; the paging-compensation
nodes and the hard-coded "before":"none" gap die together. Folded into SPEC-v94 at the draft-3
review pass.

---

## T8 · wayfinder:task (AFK) — Canonical-graph guard
claimed:
blocked-by: —

### Question
Wire the existing pieces (graph exports in this directory, `checks/check_v91_graph.py`'s 35
assertions, `mott-v21-snap/scripts/mint_graph_version.py`) into ONE enforced pre-mint path so a
v87-style silent fork (150 diffs, 113 lost fixes, discovered only by archaeology) cannot recur.
Deliverable: the documented, single command that validates-then-mints, and a refusal path when
validation is skipped.

---

## T9 · wayfinder:task (AFK) — Build v93
claimed:
blocked-by: T3, T1

### Question
Same machinery as v91/v92: spec revision (T2 protocol + T3 containment + T1 resolver fix + T6
streamline + T7 capability) → Ringer codex build → extended validator (red-proven) → mint
unattached → live harness (4 existing modes + T3 fuzz + latency capture + "following Thursday"
correction scenario + last-slot scenario) → 33-scenario regression → flip packet to Ankit.
