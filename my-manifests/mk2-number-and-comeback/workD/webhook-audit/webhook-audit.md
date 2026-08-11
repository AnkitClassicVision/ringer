# Bland pathway v87 webhook settings and variable-flow audit

Scope: static analysis of `pathway-v87.json`, the Mott webhook catalog, and `EVIDENCE-502.md`. No live endpoint was called. `timeout: none exported` means none of `timeout`, `timeout_seconds`, or `timeoutSeconds` exists in that node's `data`; it does not mean Bland waits indefinitely.

## Executive finding

Both booking nodes collapse an omitted `$.success` into failure. In the measured incident, `/sign` returned HTTP 502 with `{"error":"gateway_unreachable","status":502}` after about 28.2 seconds. That body had no `success` key, so `book_success == true` did not match and `book_success != true` sent the conversation to `e_booking_failed`. The patient received: “I couldn't confirm that booking. Please call MK2 Optical at (212) 219-2219 so they can check it for you.” The appointment had committed, so the correct state was UNKNOWN, not failed.

A separate critical fail-open exists immediately before each booking node. `n_verify_1` and `n_verify_2` explicitly route `slot_conflict == ""` to `/sign`. If a malformed nominal conflict-check response has `ok: true` but omits `result.conflict`, the pathway advances into a real write.

## Per-node settings and variables

All methods are `POST`; all nodes export `modelOptions.retryAttempts: 0`; no node exports an explicit timeout field.

| Node | URL | Method | Timeout / effective observation | Retries | Extracted variables in responseData order | Routing consumes (sorted) | Extracted but unused by this node's conditions |
|---|---|---|---|---:|---|---|---|
| `n_identity` | `https://mott-booking-gw.mail.mybcat.com/patient-search` | POST | None exported. Catalog intent 10s; endpoint measured near 22s under load, so observed practical wait was longer. Exact node/platform cutoff unknown. | 0 | `ok`←`$.ok`; `count`←`$.result.count`; `patient_first`←`$.result.patients[0].name_first`; `patient_id`←`$.result.patients[0].patient_id`; `exam_type_id`←`$.result.exam_type_id` | `count`, `ok`, `recall_cell`, `recall_patient_id`, `store` | `exam_type_id`, `patient_first`, `patient_id` |
| `n_appt_check` | `https://mott-booking-gw.mail.mybcat.com/appt-list` | POST | None exported. Catalog intent 10s; endpoint measured 18.1–24.4s under load. Exact node/platform cutoff unknown. | 0 | `ok`←`$.ok`; `appt_count`←`$.result.count` | `appt_count`, `ok` | none |
| `n_search` | `https://mott-booking-gw.mail.mybcat.com/availability` | POST | None exported. Catalog intent 10s; endpoint measured 21.5–23.8s under load and the incident conversation completed multiple availability rounds. Platform cutoff unknown. | 0 | `ok`←`$.ok`; `slot_count`←`$.result.count`; `slot_1_start`←`$.result.slots[0].start`; `slot_1_end`←`$.result.slots[0].end`; `slot_1_doctor`←`$.result.slots[0].doctor_id`; `slot_2_start`←`$.result.slots[1].start`; `slot_2_end`←`$.result.slots[1].end`; `slot_2_doctor`←`$.result.slots[1].doctor_id`; `time_pref_relaxed`←`$.result.time_pref_relaxed` | `day_part`, `ok`, `preference_from`, `slot_count` | `slot_1_doctor`, `slot_1_end`, `slot_1_start`, `slot_2_doctor`, `slot_2_end`, `slot_2_start`, `time_pref_relaxed` |
| `n_page_2` | `https://mott-booking-gw.mail.mybcat.com/availability` | POST | None exported. Same 21.5–23.8s endpoint observation; node-specific cutoff unknown. | 0 | `ok`←`$.ok`; `slot_count`←`$.result.count`; `slot_1_start`←`$.result.slots[8].start`; `slot_1_end`←`$.result.slots[8].end`; `slot_1_doctor`←`$.result.slots[8].doctor_id`; `slot_2_start`←`$.result.slots[9].start`; `slot_2_end`←`$.result.slots[9].end`; `slot_2_doctor`←`$.result.slots[9].doctor_id`; `time_pref_relaxed`←`$.result.time_pref_relaxed` | `ok`, `slot_1_start` | `slot_1_doctor`, `slot_1_end`, `slot_2_doctor`, `slot_2_end`, `slot_2_start`, `slot_count`, `time_pref_relaxed` |
| `n_page_3` | `https://mott-booking-gw.mail.mybcat.com/availability` | POST | None exported. Same 21.5–23.8s endpoint observation; node-specific cutoff unknown. | 0 | `ok`←`$.ok`; `slot_count`←`$.result.count`; `slot_1_start`←`$.result.slots[16].start`; `slot_1_end`←`$.result.slots[16].end`; `slot_1_doctor`←`$.result.slots[16].doctor_id`; `slot_2_start`←`$.result.slots[17].start`; `slot_2_end`←`$.result.slots[17].end`; `slot_2_doctor`←`$.result.slots[17].doctor_id`; `time_pref_relaxed`←`$.result.time_pref_relaxed` | `ok`, `slot_1_start` | `slot_1_doctor`, `slot_1_end`, `slot_2_doctor`, `slot_2_end`, `slot_2_start`, `slot_count`, `time_pref_relaxed` |
| `n_page_near` | `https://mott-booking-gw.mail.mybcat.com/availability` | POST | None exported. Same 21.5–23.8s endpoint observation; node-specific cutoff unknown. | 0 | `ok`←`$.ok`; `slot_count`←`$.result.count`; `slot_1_start`←`$.result.slots[8].start`; `slot_1_end`←`$.result.slots[8].end`; `slot_1_doctor`←`$.result.slots[8].doctor_id`; `slot_2_start`←`$.result.slots[9].start`; `slot_2_end`←`$.result.slots[9].end`; `slot_2_doctor`←`$.result.slots[9].doctor_id`; `time_pref_relaxed`←`$.result.time_pref_relaxed` | `ok`, `slot_1_start` | `slot_1_doctor`, `slot_1_end`, `slot_2_doctor`, `slot_2_end`, `slot_2_start`, `slot_count`, `time_pref_relaxed` |
| `n_verify_1` | `https://mott-booking-gw.mail.mybcat.com/conflict-check` | POST | None exported. Catalog intent 10s; endpoint measured 19.3–22.0s under load. Exact cutoff and its share of the 48.2s reply gap unknown. | 0 | `ok`←`$.ok`; `slot_conflict`←`$.result.conflict`; `conflict_reason`←`$.result.reason` | `conflict_reason`, `ok`, `slot_conflict` | none |
| `n_book_1` | `https://mott-booking-gw.mail.mybcat.com/sign` | POST | None exported. Measured 502 body arrived at about 28.2s; YES-to-reply was 48.2s including surrounding processing. A roughly 28s server-side failure deadline appeared in that run; Bland's own timeout remains unknown. | 0 | `book_success`←`$.success`; `book_http_status`←`$.http_status`; `book_error`←`$.error`; `new_appt_id`←`$.new_appt_id`; `error_status`←`$.status` | `book_error`, `book_success` | `book_http_status`, `error_status`, `new_appt_id` |
| `n_verify_2` | `https://mott-booking-gw.mail.mybcat.com/conflict-check` | POST | None exported. Catalog intent 10s; endpoint measured 19.3–22.0s under load. Exact cutoff and its share of the 48.2s reply gap unknown. | 0 | `ok`←`$.ok`; `slot_conflict`←`$.result.conflict`; `conflict_reason`←`$.result.reason` | `conflict_reason`, `ok`, `slot_conflict` | none |
| `n_book_2` | `https://mott-booking-gw.mail.mybcat.com/sign` | POST | None exported. Same endpoint and identical routing as `n_book_1`; measured 502 at about 28.2s applies as an endpoint risk, not a node-2 observation. Bland's timeout remains unknown. | 0 | `book_success`←`$.success`; `book_http_status`←`$.http_status`; `book_error`←`$.error`; `new_appt_id`←`$.new_appt_id`; `error_status`←`$.status` | `book_error`, `book_success` | `book_http_status`, `error_status`, `new_appt_id` |
| `n_suppress_stop` | `https://mott-booking-gw.mail.mybcat.com/sms-suppression` | POST | None exported. Catalog intent 10s, but endpoint is cataloged missing/404. No effective timeout measurement exists. | 0 | `suppression_ok`←`$.ok` | `suppression_ok` | none |
| `n_suppress_not_me` | `https://mott-booking-gw.mail.mybcat.com/sms-suppression` | POST | None exported. Catalog intent 10s, but endpoint is cataloged missing/404. No effective timeout measurement exists. | 0 | `suppression_ok`←`$.ok` | `suppression_ok` | none |

## Ranked missing-variable risks

### 1. Critical: missing `book_success` turns UNKNOWN writes into patient-facing failure

- Nodes: `n_book_1`, `n_book_2`.
- Response classes: measured 502 `gateway_unreachable`; documented 423 `write_unverified`. Both omit `$.success`.
- Ordered consequence: `book_error == slot_conflict` is false; `book_success == true` is false; `book_success != true` matches; destination is `e_booking_failed`.
- Conversation consequence: the patient is told the booking could not be confirmed. The measured 502 case proved the appointment may already exist. The pathway performs no read-after-write reconciliation and must not retry because `/sign` has no idempotency key or visible slot dedupe.
- The documented 403 `authorization_denied` also omits success and reaches the same end node. That write is denied rather than commit-unknown, but the pathway does not distinguish the operational cause.

### 2. Critical: missing `slot_conflict` can fail open into the write

- Nodes: `n_verify_1`, `n_verify_2`.
- Response class: malformed nominal response with `$.ok == true` but no `$.result.conflict`.
- Ordered consequence: the `ok != true` guard does not match; conflict true and nonempty reason checks do not match; the explicit `slot_conflict == ""` route advances to `n_book_1` or `n_book_2`.
- Conversation consequence: the pathway can execute `/sign` without a positive `slot_conflict == false` result. The catalog describes conflict-check as advisory, and `/sign` rechecks conflict, but the pathway gate itself is fail-open.

### 3. High: an unavailable appointment-list check continues toward a new booking

- Node: `n_appt_check`.
- Response class: error or malformed body without `$.result.count`, and missing or non-true `$.ok`.
- Ordered consequence: neither appointment-count branch matches; `ok != true` routes to `n_ask`.
- Conversation consequence: the patient is asked when they want to come in despite the pathway not knowing whether an upcoming appointment already exists. This can increase duplicate-booking risk.

### 4. High: suppression persistence is missing, but success and failure are routed identically

- Nodes: `n_suppress_stop`, `n_suppress_not_me`.
- Response class: the catalog says authenticated `/sms-suppression` returns 404; that response is not shown to carry `$.ok`.
- Ordered consequence: missing/non-true `suppression_ok` takes the failure comparison, but both comparisons go to the same End Call node with the same label and text.
- Conversation consequence: the copy cautiously directs the person to call the office, but pathway routing and outcome do not preserve whether suppression was persisted. An operator cannot infer success from the End Call result.

### 5. High: missing availability count can leave an incomplete route

- Node: `n_search`.
- Response class: `ok: true` with no `$.result.count`.
- Ordered consequence: ambient `day_part` may page to another webhook; otherwise no slot-count condition matches. The files do not define Bland's no-match fallback.
- Conversation consequence: routing can proceed without verified availability or become stranded. This is undeterminable from the export and should not be treated as a safe fallback.

### 6. Medium: ambient variables are consumed but never extracted by their webhook

- `n_identity` consumes `recall_cell`, `recall_patient_id`, and `store` from pathway state. `n_search` consumes `preference_from` and `day_part` from pathway state.
- These variables are absent from every corresponding webhook response by design. Their safety depends on upstream initialization and Bland's treatment of an absent variable versus an empty string.
- Consequences are concrete: identity variables comparing empty go to `e_safe_identity`; missing `preference_from` can bypass clarification; missing `day_part` bypasses outside/late/afternoon routing.

### 7. Low: paged availability deliberately treats absent array elements as empty

- Nodes: `n_page_2`, `n_page_3`, `n_page_near`.
- `slots[8]` is absent with fewer than nine slots; `slots[16]` is absent with fewer than seventeen.
- Consequence: `slot_1_start == ""` sends the conversation to a thin-results fallback or another page. This is a missing-variable case, but it is conservative and appears intentional.

## Timeout reconciliation

The catalog states `default_node_settings.timeout_seconds: 10` and `retry_attempts: 0`. Version 87 explicitly agrees on zero retries but does not encode the timeout default in any of the three recognized keys. Runtime observations do not behave like a proven flat 10-second cutoff: reads completed around 18–24 seconds under load, the measured `/sign` 502 arrived around 28.2 seconds, and the patient reply gap was 48.2 seconds across conflict-check, signing, and conversation processing. The export alone cannot determine whether Bland has a hidden UI/platform default, whether the roughly 28-second event was a gateway-side deadline, or how the 48.2 seconds divides among the two webhook nodes and Bland processing.

## Interpretation limits

- The catalog defines normal response mappings and selected warnings, not an exhaustive body fixture for every HTTP and transport failure on every read endpoint.
- Exact Bland semantics for an absent JSONPath in ordered comparisons are not exported. Consequences above that depend on missing-equals-empty or missing-not-equal-true behavior are labeled as intended/apparent routing, not measured platform semantics.
- The 502 commit incident was measured on `n_book_1`. `n_book_2` is rated the same because its URL, extraction mappings, and ordered conditions are identical, not because a slot-2 incident was observed.
- No source file was changed and no live API, gateway, webhook, or network endpoint was called.
