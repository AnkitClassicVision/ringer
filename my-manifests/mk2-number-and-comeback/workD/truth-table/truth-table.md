# Booking write-path routing truth table

CANARY: blue paperclip

Scope: static analysis of `pathway-v87.json`, the webhook catalog, and `EVIDENCE-502.md`. No live endpoint was called. The two booking nodes have identical response mappings and ordered routing; the two verification nodes likewise differ only in which booking node they enter.

## Scenario truth table for `n_book_1` and `n_book_2`

| Scenario | Extracted routing values | Destination | Basis |
|---|---|---|---|
| `success_true` | `book_success="true"`; `book_error=ABSENT` | `n_confirm` | ✓ Graph fact: the second condition, `book_success == true`, matches. |
| `success_false_no_error_code` | `book_success="false"`; `book_error=ABSENT` | `e_booking_failed` | ✓ Graph fact: the first two conditions fail and `book_success != true` matches. |
| `slot_conflict` | `book_success=ABSENT`; `book_error="slot_conflict"` | `n_recheck` | ✓ Graph fact: the first ordered condition matches before the success conditions. |
| `http_502_gateway_unreachable` | `book_success=ABSENT`; `book_error="gateway_unreachable"`; `error_status="502"` | `e_booking_failed` | ✓ Incident-observed destination; ? the export does not reveal whether the missing extraction is internally empty or undefined. Either way, the real run shows it satisfied or was handled as `book_success != true`. |
| `http_423_write_unverified` | `book_success=ABSENT`; `book_error="write_unverified"` | `e_booking_failed` | ? Inferred from ordered evaluation plus the incident-confirmed treatment of missing `book_success`. No condition recognizes `write_unverified`. |
| `http_403_authorization_denied` | `book_success=ABSENT`; `book_error="authorization_denied"` | `e_booking_failed` | ? Inferred from ordered evaluation plus the incident-confirmed treatment of missing `book_success`. No condition recognizes `authorization_denied`. |
| `timeout_or_empty_response` | all five booking response variables `ABSENT` | `e_booking_failed` | ? Inferred from the observed missing-success behavior. The export alone does not define timeout handling or empty-versus-undefined representation. |

`ABSENT` means the response JSON has no value at the configured JSONPath. It does not claim that Bland stores an empty string. The graph export does not specify whether a missing extraction is `""`, undefined, or another sentinel. The design rules say failed calls leave missing values able to satisfy complement checks, and the incident supplies direct operational evidence here: a 502 body with no `$.success` ended at `e_booking_failed`. The exact internal representation remains undeterminable from the supplied files.

## Exact ordered webhook routes and outgoing edges

### `n_book_1` and `n_book_2`

Both nodes have the same ordered `responsePathways`:

| Order | Variable | Operator | Value | Destination |
|---:|---|---|---|---|
| 1 | `book_error` | `==` | `slot_conflict` | `n_recheck` |
| 2 | `book_success` | `==` | `true` | `n_confirm` |
| 3 | `book_success` | `!=` | `true` | `e_booking_failed` |

Their outgoing top-level edges, in export order, are exactly:

| Target | `data.label` |
|---|---|
| `n_recheck` | `book_error == slot_conflict` |
| `n_confirm` | `book_success == true` |
| `e_booking_failed` | `book_success != true` |

### `n_verify_1`

| Order | Variable | Operator | Value | Destination |
|---:|---|---|---|---|
| 1 | `ok` | `!=` | `true` | `e_safe_failure` |
| 2 | `slot_conflict` | `==` | `true` | `n_miss_unbookable` |
| 3 | `conflict_reason` | `!=` | empty string | `n_miss_unbookable` |
| 4 | `slot_conflict` | `==` | `false` | `n_book_1` |
| 5 | `slot_conflict` | `==` | empty string | `n_book_1` |

| Target | `data.label` |
|---|---|
| `e_safe_failure` | `ok != true` |
| `n_miss_unbookable` | `slot_conflict == true` |
| `n_miss_unbookable` | `conflict_reason != ` |
| `n_book_1` | `slot_conflict == false` |
| `n_book_1` | `slot_conflict == ` |

### `n_verify_2`

| Order | Variable | Operator | Value | Destination |
|---:|---|---|---|---|
| 1 | `ok` | `!=` | `true` | `e_safe_failure` |
| 2 | `slot_conflict` | `==` | `true` | `n_miss_unbookable` |
| 3 | `conflict_reason` | `!=` | empty string | `n_miss_unbookable` |
| 4 | `slot_conflict` | `==` | `false` | `n_book_2` |
| 5 | `slot_conflict` | `==` | empty string | `n_book_2` |

| Target | `data.label` |
|---|---|
| `e_safe_failure` | `ok != true` |
| `n_miss_unbookable` | `slot_conflict == true` |
| `n_miss_unbookable` | `conflict_reason != ` |
| `n_book_2` | `slot_conflict == false` |
| `n_book_2` | `slot_conflict == ` |

For verification failures, `ok != true` is first. Based on the local Bland design rules, a missing `ok` after a failed call can match this complement and route safely before either empty-slot condition is considered. That missing-value behavior is guidance, not a semantic guarantee encoded in the graph export.

## `e_safe_failure` inbound and write-path reachability

Every inbound edge source is: `n_identity`, `n_verify_1`, and `n_verify_2`. Each edge label is `ok != true`.

No response from `n_book_1` or `n_book_2` routes directly to `e_safe_failure`. The distinction between the `gateway_failed` End node and the `booking_failed` End node exists, but the write response router does not use it.

Pure graph reachability is technically yes, but only indirectly and later: `/sign` `slot_conflict` → `n_recheck` → search/offer/confirmation flow → `n_verify_1` or `n_verify_2` → a new `/conflict-check` failure → `e_safe_failure`. This is not a route that classifies the original `/sign` response. No `gateway_unreachable`, `write_unverified`, `authorization_denied`, 502, or empty `/sign` response reaches the safe end through its own ordered evaluation.

## 502 distinguishability verdict

**No.** The write nodes do not test `book_error == gateway_unreachable`, `error_status == 502`, `book_http_status`, or Bland's HTTP status. Apart from `slot_conflict`, every non-success case is collapsed by `book_success != true` into `e_booking_failed`.

That makes these materially different states indistinguishable at the routing layer: a genuine `success:false`, an unknown-outcome 502, `write_unverified`, `authorization_denied`, and a timeout or empty response. The measured incident is consistent with the table and resolves the otherwise undocumented missing-extraction question at the behavioral level: the 502 with no `success` reached `e_booking_failed`. It does not reveal whether Bland represented the missing value as empty, undefined, or handled the webhook error through an equivalent internal failure path.
