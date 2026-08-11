# Gateway Field Inventory

Legend (operation ids): 1 patient.lookup.recall · 2 patient.search.name_dob · 3 patient.disambiguate.first_name · 4 availability.first_available · 5 availability.specific_date · 6 availability.conflict_check · 7 appointment.list · 8 appointment.book.slot_1 · 9 appointment.book.slot_2 · 10 suppression.stop · 11 suppression.wrong_number · 12 staff.message · 13 hours.state · 14 urgent.availability · 15 appointment.cancel.governed · 16 appointment.reschedule.governed · 17 appointment.modify.governed · 18 patient.book_new.

v54_graph.json wires only 8 webhook nodes: n_identity(→1), n_search/n_page_2/n_page_3(→5-shaped, plus undocumented fields), n_verify_1/n_verify_2(→6), n_book_1/n_book_2(→8/9). Ops 2,3,7,10-18 have no node in the graph.

## Summary
- The live graph never reads the catalog's success/conflict flags ($.success, $.result.conflict) for the two operations that write or gate a real booking, using undocumented or status-code logic instead.
- Shared-phone disambiguation and the home-store mismatch check exist in the catalog but are never wired in, and STOP/wrong-number replies are never persisted anywhere.
- The catalog contradicts the graph: availability.conflict_check is marked "Not currently used" while n_verify_1/n_verify_2 call it live under pathway 19.

## Findings

### Finding: Booking confirmation is gated on HTTP status, not the documented success flag
Evidence: n_book_1/n_book_2 responseData omits `$.success`/`$.action`; routing uses `book_http_status=="200"/"201"`. Op 8/9 warns "Only send patient-facing confirmation after book_success equals true"; reviewed-state's `response_contract.sign.success_paths` lists `$.success`.
Impact: A 200/201 with `success:false` (or vice versa) would tell the patient "You're all set" on a write the catalog's own contract wouldn't call successful.
Fix: Extract `$.success`, make it the authoritative condition into n_confirm; keep http_status as a secondary check.
Priority: P0
Confidence: high

### Finding: Conflict detection ignores the documented flag and may miss out-of-schedule conflicts
Evidence: n_verify_1/n_verify_2 read `$.result.overlapping_appt_id` (undocumented in op 6) and `$.result.reason`, never `$.result.conflict`, which op 6 defines as "True when the slot collides OR is outside the schedule."
Impact: A slot outside clinic hours with no colliding appointment (empty `overlapping_appt_id`) routes to booking as "free and clear" — the graph can't see the flag that would catch it.
Fix: Extract `$.result.conflict` too and route on either signal; document `overlapping_appt_id` in the catalog since the graph already depends on it.
Priority: P0
Confidence: medium

### Finding: Catalog says conflict-check is unused; the live graph disagrees
Evidence: op 6 `evidence.live_pathway_version: null`, `live_node_role: "Not currently used"`. n_verify_1/n_verify_2 call `/conflict-check` and are reachable from n_gate_1/n_gate_2 on pathway 19, same tag as every other live node here.
Impact: Trusting the catalog's evidence block to judge whether conflict-check is safe to touch would be wrong; ops 7,13-17 correctly show "Not currently used" and match the graph, but op 6 doesn't.
Fix: Update op 6's evidence to `live_pathway_version: 19`, `live_node_role: "Pre-booking conflict verification"`.
Priority: P1
Confidence: high

### Finding: STOP and wrong-number replies are never persisted through the gateway
Evidence: `e_stop`/`e_not_me` are terminal End Call nodes that only tell the patient to call the office; neither calls `/sms-suppression`. Ops 10/11 are status "missing"; reviewed-state confirms `/sms-suppression` is unimplemented (404).
Impact: No durable, gateway-side opt-out record for STOP or wrong-number; suppression depends entirely on a human acting on a phone call, with no audit trail.
Fix: Already a listed release blocker ("Implement and prove authenticated idempotent SMS suppression"); once built, wire `e_stop`/`e_not_me` to ops 10/11 before ending the call.
Priority: P0
Confidence: high

### Finding: Shared-phone disambiguation (op 3) is built but unreachable
Evidence: n_identity routes `count>=2` straight to `e_safe_identity` (safe exit). Op 3 exists to "narrow a shared-phone match using the texter-provided first name," and none of its fields appear anywhere in v54_graph.json.
Impact: Every shared-phone household gets a dead-end handoff instead of the disambiguation flow the catalog was built for.
Fix: Insert a node between n_identity and e_safe_identity that extracts the texter's first name and calls op 3 when count>=2.
Priority: P1
Confidence: high

### Finding: No human-readable time field exists anywhere in the catalog
Evidence: every start/end field (ops 4-9) is a raw string JSONPath. TEMPORAL-BRIEF.md confirms the measured shape (`08/05/2026 12:30 pm`); offer/gate prompts instruct "do not convert it, do not reformat it."
Impact: No fallback field for localized/spoken-friendly formatting — patient-facing time is whatever raw string the gateway returns, and reformatting is explicitly forbidden.
Fix: File a gateway request for a formatted companion field (e.g. `start_display`) alongside `start`.
Priority: P2
Confidence: high

### Finding: Positional slot paging substitutes for the never-implemented time_pref filter
Evidence: n_search/n_page_2/n_page_3 send `"time_pref":"none"` and read fixed offsets `slots[0]/[1]`, `[8]/[9]`, `[16]/[17]`. Op 5 documents `time_pref` as a real preference field, but the graph never sends anything but the sentinel. TEMPORAL-BRIEF.md confirms `time_pref` is "accepted and then IGNORED," and the offsets only work because "the thinnest weekday holds 18 slots."
Impact: `time_pref` can never carry a real preference; the offset workaround has no bounds check and silently misbehaves on thin days.
Fix: Track as a gateway-side dependency (per TEMPORAL-BRIEF); document the offset/slot-count assumption directly in the nodes.
Priority: P1
Confidence: high

### Finding: `home_store`/`returned_store` is documented for comparison but never read
Evidence: ops 1 and 3 both describe `returned_store` as "returned for comparison; never overwrite trusted upstream store." n_identity's responseData omits it.
Impact: Nothing in the live graph checks whether a patient's home store differs from the booking store, though the field exists exactly for that.
Fix: Add `home_store` to n_identity's responseData and branch (or warn) when it differs from `store`.
Priority: P2
Confidence: medium

### Finding: `time_pref_relaxed` is captured but never consumed
Evidence: n_search/n_page_2/n_page_3 extract `$.result.time_pref_relaxed`, but no pathway or prompt references it, though op 5's warning says to explain when the requested time was relaxed.
Impact: If the gateway relaxes an unmet preference, the patient is never told — contradicting the catalog's own warning.
Fix: Route on `time_pref_relaxed != ""` into a short caveat, or drop the extraction.
Priority: P3
Confidence: medium

### Finding: n_identity sources the phone field from an undocumented variable
Evidence: n_identity body uses `"phone":"{{recall_cell}}"`; op 1 documents the source variable as `to`.
Impact: Minor drift risk — auditing by variable name won't find `recall_cell` documented anywhere.
Fix: Update op 1's upstream_variables to `recall_cell`, or rename the graph variable to `to`.
Priority: P3
Confidence: low

## Request fields

| Field (body key) | Ops | Req | Meaning | Graph supplies |
|---|---|---|---|---|
| phone | 1, 3 | yes | recipient phone | Yes (op 1, via `recall_cell`) |
| patient_id | 1, 7 | yes | EyeCloud patient id | Yes (1); No (7) |
| last | 2 | yes | patient last name | No |
| dob | 2 | yes | DOB MM/DD/YYYY | No |
| first | 3 | yes | texter first name | No |
| store | 4,5,6,7,8,9,12,13,14 | yes | Mott store id | Yes (5,6,8/9); No (7,12,13,14) |
| first_available | 4 | fixed "1" | earliest-window flag | No |
| slot_minutes | 4,5 | fixed "15" | slot granularity | Yes |
| from | 5 | yes | window start date | Yes |
| to | 5 | yes | window end date | Yes |
| time_pref | 5 | no | morning/afternoon/evening pref | Yes, always sentinel "none" (Finding) |
| after / before | — | not in any op | undocumented params | Yes — n_search family; ignored gateway-side per TEMPORAL-BRIEF |
| doctor | 6 | yes | doctor id, proposed slot | Yes |
| start | 6 | yes | proposed slot start | Yes |
| end | 6 | yes | proposed slot end | Yes |
| target | 8,9,15,16,17 | implicit | write target | Yes (8/9); No (15-17) |
| verb | 8,9,15,16,17 | fixed per op | conductor action | Yes ("appt.book" only) |
| reason | 8,9,15,16,17 | fixed per op | audit reason | Yes ("new-booking" only) |
| params.doctor | 8,9,17 | yes/no | doctor id to write | Yes (8/9); No (17) |
| params.start | 8,9 | yes | appt start to write | Yes |
| params.end | 8,9 | yes | appt end to write | Yes |
| params.type | 8,9,17 | yes/no | exam type to write | Yes (8/9); No (17) |
| phone_e164 | 10,11 | yes | E.164 recipient | No |
| source | 10,11 | fixed | suppression origin tag | No |
| message | 12 | yes | callback message text | No |
| caller_name | 12 | no | caller first name | No |
| callback_phone | 12 | yes | callback number | No |
| intent | 12 | no | non-diagnostic intent | No |
| slot_mode | 14 | yes | same_day/first_am mode | No |
| params.appt_id | 15,16,17 | yes | target appointment id | No |
| params.day | 15,16,17 | yes | current appt day | No |
| params.new_start | 16 | yes | new slot start | No |
| params.new_end | 16 | yes | new slot end | No |
| params.new_doctor | 16 | yes | new doctor id | No |
| (none) | 18 | — | patient creation disabled | No |

## Response fields

| JSONPath | Ops | Meaning | Graph reads |
|---|---|---|---|
| $.ok | 1,2,3,4,5,6,7,10,11,12,13,14 | gateway/persistence success flag | Yes (1,5-shape,6); No elsewhere |
| $.result.count | 1,2,3(match_count), 4,5(slot_count), 7,14 | count of matches/slots | Yes (1,5-shape); No (2,3,7,14) |
| $.result.patients[0].patient_id | 1,2,3 | resolved patient id | Yes (1); No (2,3) |
| $.result.patients[0].name_first | 1,2,3 | first name | Yes (1); No (2,3) |
| $.result.patients[0].name_last | 1 | last name | No |
| $.result.patients[0].home_store | 1,3 | home store, for store-mismatch check | No (Finding) |
| $.result.exam_type_id | 1,3 | server-trusted appt type | Yes (1); No (3) |
| $.result.first_start/first_end/first_doctor | 4,5 | documented "first slot" fields | No — graph reads `slots[0]` instead (Finding) |
| $.result.slots[1].start/end/doctor_id | 4,5 | second slot | Yes |
| $.result.slots[2].start/end/doctor_id | 4 | third slot | No |
| $.result.alt_store/alt_count/alt_first_start | 4 | alternate-store opening | No |
| $.result.slots[0].store_id | 4 | returned store diagnostic | No |
| $.result.time_pref_relaxed | 5 | requested time was unavailable | Extracted, never consumed (Finding) |
| $.result.conflict | 6 | conflict/outside-schedule flag | No (Finding) |
| $.result.reason | 6 | non-PHI conflict reason | Yes |
| $.result.overlapping_appt_id | undocumented for op 6 or any op | — | Yes — n_verify_1/2 depend on it (Finding) |
| $.result.appointments[0].appointment_id/start/end/doctor_id/store_id/status | 7 | first upcoming appt | No |
| $.success | 8,9,15,16,17 | definitive write-success flag | No (Finding) |
| $.new_appt_id | 8,9 | new appointment id | Yes |
| $.action | 8,9 | confirmed conductor action | No |
| $.http_status | 8,9 | signer HTTP status | Yes |
| $.error | 8,9,15,16,17 | stable conductor error code | Yes (8,9); No (15-17) |
| $.status | 8,9,15,16,17 | error-only signer status | Yes (8,9, as error_status); No (15-17) |
| $.state | 13 | open/about_to_close/after_hours | No |
| $.closes_at | 13 | current close time | No |
| $.first_am_start | 13 | next opening time | No |
| $.result.slot_start/slot_end/slot_doctor | 14 | urgent slot fields | No |
| $.result.double_book | 14 | double-book proposal flag | No |

## Clean
- Op 6's `store`/`doctor`/`start`/`end` and `$.result.reason` match the catalog node-for-node (n_verify_1/n_verify_2).
- Op 8/9's write params (`doctor`,`start`,`end`,`type`) and `$.new_appt_id`/`$.http_status`/`$.error` match catalog and graph, aside from the missing `$.success`.
- Ops 7,12,13,14,15,16,17,18 are correctly marked "Not currently used"/blocked in both catalog evidence and reviewed state, matching v54_graph.json — no contradiction.
- Op 1's core identity fields (`phone`→patient_id/name_first/exam_type_id, `count`) round-trip correctly in n_identity.

## Assumptions
- v54_graph.json is "the live conversation graph"; catalog "pathway version 19" evidence refers to it.
- "Graph supplies/reads" = the key/JSONPath appears in a Webhook node's `body`/`responseData`; an unwired operation's fields read "No."
- Request-table identity is the JSON body key, not the `{{variable}}` name, since different variables fill the same key (`to` vs `recall_cell` both fill `phone`).
- `after`/`before` are reported since they appear verbatim in graph bodies — undocumented by the catalog, not invented.
