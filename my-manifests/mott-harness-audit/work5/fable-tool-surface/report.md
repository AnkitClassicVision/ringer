# Gateway Tool Surface

## Summary

- The complete surface is 18 tools — one per catalog operation, not per endpoint and not a smaller parameterised set — because the platform's fixed body templates (an unfilled variable becomes a JSON null the gateway rejects) make every distinct body shape its own tool, and single-variable routing forces flat, per-tool extracted variables.
- 9 operations are reads, 8 are writes, 1 is an external send. Only 5 reads and the 2 `/sign` book tools are usable today; everything else is blocked, missing (404), or legacy — and the reviewed state gates ALL production use (`workflow_gate: BLOCK`), so the surface ships dark until that lifts.
- The live graph violates the catalog contract in three places (booking success routed on HTTP status not `$.success`; conflict check keyed on a non-catalog JSONPath; fixed-offset paging that breaks on multi-day windows) — fix these in the surface, don't copy them.

## Findings

### Finding: Legacy direct-write endpoints are still gateway-exposed and must be denylisted from any generated surface
Evidence: reviewed state lists `/book`, `/reschedule`, `/cancel` as `legacy-exposed-not-live-probed` and `/book-new-patient` as route-present; catalog `disallowed_endpoints` bans all four; release blocker "Remove or edge-deny direct external write routes."
Impact: a surface built by enumerating gateway endpoints (14 public) rather than catalog operations (18) would hand the agent ungoverned EyeCloud writes bypassing conductor scope and the kill switch.
Fix: generate tools only from catalog operation ids; hard-denylist the four paths at build time (only `patient.book_new` resolves to one, and it stays unexposed).
Priority: P0
Confidence: high

### Finding: Booking nodes detect success by HTTP status instead of the signer's $.success flag
Evidence: `n_book_1` and `n_book_2` extract `$.http_status`, `$.error`, `$.new_appt_id`, `$.status` but never `$.success`; they route `book_http_status == 200/201 → n_confirm`. Catalog `appointment.book.slot_1` defines `book_success ← $.success` and warns "Only send patient-facing confirmation after book_success equals true" and that `$.status` is error-only.
Impact: a signer response where transport status and write outcome diverge confirms an appointment that was never written — the false-confirmation class the catalog forbids.
Fix: book tools extract `book_success ← $.success` as the sole success route; `book_error == "slot_conflict"` routes to refresh, everything else to failure.
Priority: P1
Confidence: high

### Finding: Conflict-check nodes route on a JSONPath the catalog does not define
Evidence: `n_verify_1`/`n_verify_2` extract `$.result.overlapping_appt_id` (`overlap_id`) and route on it; catalog `availability.conflict_check` defines only `$.ok`, `$.result.conflict`, `$.result.reason` — the cataloged boolean `slot_conflict` is never read.
Impact: routing "free and clear" on an empty string from an uncataloged field means a contract change or absent field silently reads as "no conflict" and the flow proceeds to the write.
Fix: the conflict tool extracts `slot_conflict ← $.result.conflict` and routes `== true → refresh availability`, `== false → continue`; `conflict_reason ← $.result.reason` is diagnostic only.
Priority: P1
Confidence: high

### Finding: Fixed-offset paging (slots[8], slots[16]) assumes a single-day result and breaks on any date span
Evidence: `n_page_2` reads `$.result.slots[8].*`, `n_page_3` reads `$.result.slots[16].*`; the measured offsets (0=morning, 8=early afternoon, 16=late) hold per single weekday, but `n_search` sends `from`/`to` from patient preference, and TEMPORAL-BRIEF measured a Monday–Friday range returning 126 slots in time order.
Impact: a patient asking for "afternoon next week" gets slot index 8 of a multi-day list — plausibly Monday morning — presented by `n_offer_2` as an afternoon opening.
Fix: paging variants of the availability tool are valid only when `from == to`; part-of-day service over a span needs per-day queries or the gateway `time_pref` fix.
Priority: P1
Confidence: high

### Finding: STOP and wrong-number suppression cannot be exposed because the endpoint returns 404
Evidence: catalog `suppression.stop` and `suppression.wrong_number` are `status: missing` ("credentialed probe returned 404"); reviewed state lists `/sms-suppression` as `missing/unimplemented`; the graph handles STOP with end node `e_stop`, which only tells the patient to call the office.
Impact: the surface has no truthful way to persist an opt-out; exposing these tools now would let the agent confirm a suppression that was never saved (`suppression_ok` never true).
Fix: keep both tools marked blocked, gated on the release blocker "Implement and prove authenticated idempotent SMS suppression"; until then STOP routes to `e_stop`-style honest deflection, never a persistence claim.
Priority: P1
Confidence: high

### Finding: n_identity evaluates match-count pathways before the gateway-failure pathway
Evidence: `n_identity.responsePathways` order is empty-input checks, then `count == 1/0/>= 2`, with `ok != true` last; catalog `patient.lookup.recall` lists the `gw_ok != true` pathway first.
Impact: a failed response still carrying `count: 0` matches `count == 0` first and exits via `e_safe_identity` instead of `e_safe_failure`, mislabeling an outage as an identity failure.
Fix: every tool's routing contract puts `gw_ok != true` first; first-match-wins ordering is part of the tool spec, not left to node authors.
Priority: P2
Confidence: medium

### Finding: after, before and time_pref are accepted then ignored, so no tool may present them as functional filters
Evidence: TEMPORAL-BRIEF measured 27 slots returned unfiltered regardless of these parameters (filed defect, assume unfixed); `n_search` hardcodes all three to the `"none"` sentinel; catalog `availability.specific_date` still templates `time_pref` and exposes `time_pref_relaxed ← $.result.time_pref_relaxed`.
Impact: a schema advertising `time_pref` invites the caller to believe filtering happened and to tell the patient a part of day is empty when it was never filtered.
Fix: keep `time_pref` in the body (`"none"` sentinel when unset), mark it inert, and require callers to check `time_pref_relaxed` before claiming any time-of-day result.
Priority: P2
Confidence: high

## Clean

- `n_search`, `n_page_2`, `n_page_3` route `ok != true` first — correct ordering.
- Write path structure is sound: `n_gate_1 → n_verify_1 → n_book_1` (and the `_2` twins) makes confirmation and conflict-check structurally unskippable before the write.
- All write nodes set `retryAttempts: 0` and no node sends `allow_conflict`, per catalog warnings.
- Every value in `n_book_1`/`n_book_2` payloads interpolates a gateway-extracted or campaign-pinned variable; nothing model-composed reaches `/sign`.
- `e_stop` and `e_not_me` never claim an opt-out was persisted — honest given the missing endpoint.

## Assumptions

- The catalog (`mott-aws-webhooks.json`) is the sole source of truth for operations, fields and JSONPaths; its 4 disallowed routes are excluded regardless of gateway exposure.
- `workflow_gate: BLOCK` / `production_authorized: false` means "usable today" describes readiness once the gate lifts, not current authorization.
- The `after`/`before`/`time_pref` defect stays unfixed; measured date-form accept/reject lists and the 14-day span cap hold.
- Routing stays one variable vs one string literal, first match wins; `"none"` is the only safe "not specified" sentinel in a fixed template.

## Tool Catalog

Granularity: **one tool per catalog operation (18)**. Not one per endpoint — `/patient-search` needs three body shapes and `/sign` four verbs, and a merged tool with optional fields is impossible because an unfilled template variable becomes a JSON null the gateway rejects. Not fewer parameterised tools — with no AND in routing and no variable-indexed extraction, each tool must emit its own flat variables (`gw_ok`, `match_count`, `slot_1_start`…) for single-variable conditions to route on. Per-ordinal book tools stay split for the same reason: the slot index must be a literal in the graph. Every tool: POST, bearer auth per catalog, `retry_attempts: 0`, timeout 10s. Failure detection for reads: `gw_ok ← $.ok != true`, routed first. Safety classes: **A** = autonomous read; **W** = governed write, human (patient) confirmation required; **X** = blocked, do not expose yet.

**Reads**

1. `patient.lookup.recall` — `/patient-search`, read_phi, ready. **A** (inputs are campaign-pinned, not conversational). In: `to`\*, `recall_patient_id`\* (both from campaign feed, never model-generated). Out: `gw_ok←$.ok`, `match_count←$.result.count`, `patient_id←$.result.patients[0].patient_id`, `patient_first←$.result.patients[0].name_first`, `patient_last←$.result.patients[0].name_last`, `returned_store←$.result.patients[0].home_store`, `exam_type_id←$.result.exam_type_id`. Routes: `gw_ok!=true`→safe exit; `match_count ==1`→continue / `>1`→ask texter / `==0`→no-match handoff.
2. `patient.search.name_dob` — `/patient-search`, read_phi, **X** (test-mode filter; unblock requires approved identity gate). In: `patient_last`\*, `patient_dob`\* (identity-collection nodes). Out: `gw_ok←$.ok`, `match_count←$.result.count`, `patient_id←$.result.patients[0].patient_id`, `patient_first←$.result.patients[0].name_first`. Routes: `gw_ok!=true`→exit; `match_count ==1`→continue, `!=1`→human handoff.
3. `patient.disambiguate.first_name` — `/patient-search`, read_phi, **X** until zero/one/multi-match proven on synthetic records. In: `to`\*, `provided_first_name`\* (dedicated extraction from the texter's reply, never a prior search result). Out: `gw_ok←$.ok`, `match_count←$.result.count`, `patient_id←$.result.patients[0].patient_id`, `patient_first←$.result.patients[0].name_first`, `returned_store←$.result.patients[0].home_store`, `exam_type_id←$.result.exam_type_id`. Routes as tool 2.
4. `availability.first_available` — `/availability`, read_scheduler, ready. **A**. In: `store`\* (pinned lookup/config; body fixes `first_available:"1"`, `slot_minutes:"15"`). Out: `gw_ok←$.ok`, `slot_count←$.result.count`, `slot_start←$.result.first_start`, `slot_end←$.result.first_end`, `slot_doctor←$.result.first_doctor`, `slot_2_start←$.result.slots[1].start`, `slot_2_end←$.result.slots[1].end`, `slot_2_doctor←$.result.slots[1].doctor_id`, `slot_3_start←$.result.slots[2].start`, `slot_3_end←$.result.slots[2].end`, `slot_3_doctor←$.result.slots[2].doctor_id`, `alt_store←$.result.alt_store`, `alt_count←$.result.alt_count`, `alt_first_start←$.result.alt_first_start`, `returned_store←$.result.slots[0].store_id` (diagnostic; never mapped back to `store`). Routes: `gw_ok!=true`→exit; `slot_count ==1`/`>=2`→offer; `<1`→ask preference.
5. `availability.specific_date` — `/availability`, read_scheduler, ready. **A**. In: `store`\*, `appt_date`\* (accepted date forms only; spans capped 14 days), `time_pref` (optional, `"none"` sentinel, **inert** — see finding). Out: `gw_ok←$.ok`, `slot_count←$.result.count`, `slot_start←$.result.first_start`, `slot_end←$.result.first_end`, `slot_doctor←$.result.first_doctor`, `slot_2_start←$.result.slots[1].start`, `slot_2_end←$.result.slots[1].end`, `slot_2_doctor←$.result.slots[1].doctor_id`, `time_pref_relaxed←$.result.time_pref_relaxed`. Routes: `gw_ok!=true`→exit; `slot_count >=1`→offer; `<1`→ask again. Paging variants (offsets 8/16 as in `n_page_2`/`n_page_3`) are extraction variants of this tool, valid only when `from == to`.
6. `availability.conflict_check` — `/conflict-check`, read_scheduler, ready. **A**; mandatory precursor to any book/reschedule write (advisory — the signer re-checks). In: `store`\*, `slot_doctor`\*, `slot_start`\*, `slot_end`\* (all from an availability response). Out: `gw_ok←$.ok`, `slot_conflict←$.result.conflict`, `conflict_reason←$.result.reason`. Routes: `gw_ok!=true`→exit; `slot_conflict ==true`→refresh availability; `==false`→continue to confirmation/write.
7. `appointment.list` — `/appt-list`, read_phi, ready. **A**. In: `patient_id`\* (one-match lookup), `store` (optional filter — omission needs a template without the key, not a null). Out: `gw_ok←$.ok`, `appt_count←$.result.count`, `appt_id←$.result.appointments[0].appointment_id`, `appt_start←…[0].start`, `appt_end←…[0].end`, `appt_doctor←…[0].doctor_id`, `appt_store←…[0].store_id`, `appt_status←…[0].status`. Routes: `gw_ok!=true`→exit; `appt_count ==0`/`==1`/`>1`.
8. `hours.state` — `/hours-state`, read_config, **X** (Mott hours config empty → unknown-store failure). In: `store`\*. Out: `hours_ok←$.ok`, `hours_state←$.state`, `closes_at←$.closes_at`, `first_am_start←$.first_am_start` (top-level envelope, not `$.result`). Routes: `hours_ok!=true`→conservative handoff; `hours_state =="open"`/`!="open"`.
9. `urgent.availability` — `/urgent-availability`, read_scheduler_high_risk, **X** (config absent; not clinical triage). In: `store`\*, `urgent_slot_mode`\* (from an approved deterministic triage gate, never free-form model judgment). Out: `urgent_ok←$.ok`, `urgent_slot_count←$.result.count`, `urgent_slot_start←$.result.slot_start`, `urgent_slot_end←$.result.slot_end`, `urgent_slot_doctor←$.result.slot_doctor`, `urgent_double_book←$.result.double_book`. Routes: `urgent_ok!=true`→human/doctor escalation; `urgent_double_book ==true`→human approval, never auto-book; `urgent_slot_count >=1`→offer.

**Writes** — all through the governed `/sign` route only (except suppression); success is `$.success == true`, error is `book/cancel/…_error←$.error` with `error_status←$.status` never used to route success; `slot_conflict` error routes to refresh, everything else to staff handoff; no retries ever.

10./11. `appointment.book.slot_1` / `appointment.book.slot_2` — `/sign` verb `appt.book`, write_eyecloud, limited (test-patient allowlist). **W**. In (all required, all provenance-bound): `patient_id` (one-match lookup), `store` (lookup/config), `slot_[2_]doctor`, `slot_[2_]start`, `slot_[2_]end` (same fresh availability response), `exam_type_id` (server-side lookup context — the v19 nodes still hardcode type; prove the extraction first per catalog warning). Out: `book_success←$.success`, `new_appt_id←$.new_appt_id`, `book_action←$.action`, `book_http_status←$.http_status`, `book_error←$.error`, `error_status←$.status`. Preconditions: conductor scope re-verified, conflict check passed, explicit patient YES to the exact interpolated time (`n_gate_1`/`n_gate_2` pattern).
12. `appointment.cancel.governed` — `/sign` verb `appt.cancel`, **X** (conductor grant excludes cancel). In: `appt_id`\*, `appt_store`\*, `appt_day`\* — all from an `appointment.list` response plus patient confirmation. Out: `cancel_success←$.success`, `cancel_error←$.error`, `error_status←$.status`.
13. `appointment.reschedule.governed` — `/sign` verb `appt.reschedule`, **X** (grant excludes it; same-store only). In: `appt_id`\*, `appt_store`\*, `appt_day`\* (appointment list) plus `slot_start`\*, `slot_end`\*, `slot_doctor`\* (fresh availability). Out: `reschedule_success←$.success`, `reschedule_error←$.error` (`slot_conflict`→refresh), `error_status←$.status`.
14. `appointment.modify.governed` — `/sign` verb `appt.modify`, **X** (grant excludes it). In: `appt_id`\*, `appt_store`\*, `appt_day`\*; at least one of `exam_type_id` (approved type map) / `slot_doctor` (verified schedule) — but with fixed templates, "optional" means two body variants, not a nullable field. Out: `modify_success←$.success`, `modify_error←$.error`, `error_status←$.status`.
15./16. `suppression.stop` / `suppression.wrong_number` — `/sms-suppression`, write_suppression, **X** (404 — see finding). In: `to`\* (E.164, conversation variable; body fixes `reason` and `source`). Out: `suppression_ok←$.ok`. Once implemented: autonomous on the patient's own STOP/not-me reply, but never confirm to the patient unless `suppression_ok == true`.

**External send**

17. `staff.message` — `/message`, external_send_phi, **X** (staff channel unconfigured, returns 503). In: `message`\*, `store`\*, `callback_phone`\* (dedicated confirmation node), `name_first`, `description` (optional — separate body variants). Out: `msg_ok←$.ok`; only claim delivery on `msg_ok == true`. Even when live: PHI leaves the system, so requires synthetic no-PHI delivery proof and stays human-supervised.

18. `patient.book_new` — `/book-new-patient`, write_eyecloud_phi, **X**: catalog carries it with empty body/response contracts and patient creation disabled; it exists in the inventory only so its blocked status is explicit.

**Safety boundary.** No human in the loop needed: tools 1, 4, 5, 6, 7 (reads with provenance-bound inputs), plus 8 when configured, plus 15/16 when implemented (the STOP itself is the human act). Writes (10–14): only via the governed `/sign` signer; before any write, all of — conductor scope re-verified for that verb, every payload value traceable to a specific prior gateway response, conflict check passed for book/reschedule, and the patient's explicit yes to the exact time the tool will send. Never autonomous under any condition: acting on `urgent_double_book`, tool 17 with real patient content, tool 18 entirely.

**Never caller-suppliable.** A caller (the model) may select *which* prior gateway response feeds a write; it may never compose the values. Concretely banned as free inputs: `slot_start`/`slot_end`/`slot_doctor` and their `_2` twins (a model composing a time already booked a patient at 11:30 am Monday after offering 5:15 pm Friday — TEMPORAL-BRIEF); `patient_id`/`target`; `appt_id`; `exam_type_id`; `store` overrides (including mapping `returned_store` back into `store`); the fixed literals `verb`, `reason`, `first_available`, `slot_minutes`, suppression `reason`/`source`; `allow_conflict` (must not exist); the bearer token (never in pathway variables); and `error_status` as a success signal.

## Not Exposed

- `/book`, `/reschedule`, `/cancel` — legacy direct EyeCloud writes bypassing conductor scope and kill switch; catalog-disallowed. Governed `/sign` verbs replace them.
- `/book-new-patient` — patient creation disabled; no governed contract (tool 18 held dark).
- A raw generic `/sign` tool — a caller choosing `verb` freely is an ungoverned write multiplexer; only verb-specific, provenance-bound tools exist.
- `/health` — live but a monitoring concern, not a conversation tool.
- Paging beyond the cataloged `slots[0..2]` and the measured 8/16 offsets — no negative or variable indexing, and showing a node a whole day's list caused the mis-booking incident; each offer sees only its own two openings.
- `after`/`before` as inputs, patient `dob`/`phone` as outputs, appointment notes/demographics — measured-ignored or minimum-necessary exclusions per catalog warnings.
