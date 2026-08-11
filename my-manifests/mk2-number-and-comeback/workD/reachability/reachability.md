# Pathway v87 reachability and dead-end analysis

This is a static analysis of the exported `nodes`, top-level `edges`, ordered Webhook `responsePathways`, the supplied incident packet, and the local Mott webhook catalog. No live endpoint was called and no source file was changed.

## Mechanical layer: edges only

The mechanical computation treats every top-level edge as a directed `source -> target` arc. It does not interpret edge labels, condition feasibility, or Bland global-node behavior.

- Start node: `n_identity`
- Nodes unreachable from the start: `n_office`, `n_faq`, `e_office`, `n_suppress_stop`, `e_stop`, `n_suppress_not_me`, `e_not_me`, `e_existing`
- End Call nodes with zero inbound edges: `e_existing`
- Nodes with no edge-path to any End Call node: none

The graph therefore has no structural nonterminating region under the requested definition. Every node can reach at least one End Call node, even though eight nodes cannot be entered from `n_identity` by edges alone.

## Judgment layer: Bland global semantics

Exactly seven nodes are global: `n_negotiate`, `n_office`, `n_faq`, `e_declined`, `n_suppress_stop`, `n_suppress_not_me`, and `e_existing`.

- `n_office` and `n_faq` globally enter the office/FAQ branch, keeping `n_office`, `n_faq`, and `e_office` alive in practice.
- `n_suppress_stop` globally enters the STOP-suppression branch, keeping it and `e_stop` alive in practice.
- `n_suppress_not_me` globally enters the wrong-person branch, keeping it and `e_not_me` alive in practice.
- `e_existing` is a global End Call node. Its global match is its only entry because no edge targets it.
- `n_negotiate` and `e_declined` are already edges-reachable; their global labels add anywhere-in-conversation entry rather than rescuing dead graph components.

After treating the start and all global nodes as possible entry seeds and then following ordinary edges, no node remains effectively unreachable.

## Ordered Webhook condition review

| Webhook | Verdict | Finding |
|---|---|---|
| `n_identity` | `no_shadowing` | Missing-input guards are independent; count cases are disjoint; an unset count leaves the last health check reachable. |
| `n_appt_check` | `no_shadowing` | Zero and one-or-more are disjoint; failure leaves the last health check reachable. |
| `n_search` | `no_shadowing` | Predicates can overlap, but the supplied files do not prove that any whole later condition is necessarily consumed by an earlier one. |
| `n_page_2` | `no_shadowing` | Health failure is first; empty and nonempty slot values are complementary. |
| `n_page_3` | `no_shadowing` | Health failure is first; empty and nonempty slot values are complementary. |
| `n_page_near` | `no_shadowing` | Health failure is first; empty and nonempty slot values are complementary. |
| `n_verify_1` | `shadowed` | The final `slot_conflict == empty string` branch cannot be selected under the catalog contract. |
| `n_book_1` | `no_shadowing` | Slot conflict, success, and the remaining non-success results retain distinct ordered coverage. |
| `n_verify_2` | `shadowed` | The final `slot_conflict == empty string` branch cannot be selected under the catalog contract. |
| `n_book_2` | `no_shadowing` | Slot conflict, success, and the remaining non-success results retain distinct ordered coverage. |
| `n_suppress_stop` | `no_shadowing` | `== true` and `!= true` are complements, even though both lead to the same End node. |
| `n_suppress_not_me` | `no_shadowing` | `== true` and `!= true` are complements, even though both lead to the same End node. |

No condition is proven intrinsically unable to evaluate true from the supplied production contracts, so `never_match_conditions` is empty. The final `slot_conflict == empty string` conditions on `n_verify_1` and `n_verify_2` are instead classified as order-shadowed: a failed response can leave that field empty, but the preceding `ok != true` condition necessarily takes control first; a successful catalog-conforming response supplies true or false and an earlier branch takes control. Removing those routes would not remove a valid failure distinction; it would remove an unsafe-looking but unselectable "missing conflict flag means book" route.

## Incident meaning

The booking incident is not caused by graph unreachability. `n_book_1 -> e_booking_failed` is both structurally reachable and conditionally live. The problem is that the route collapses distinct outcomes:

- `book_error == slot_conflict` has a distinct route to `n_recheck`.
- `book_success == true` has a distinct route to `n_confirm`.
- Every other result, including a missing success value after the measured 502, routes through `book_success != true` to `e_booking_failed`.

The node maps `book_error` and `error_status`, but only `slot_conflict` receives special handling. The supplied evidence says `/sign` can return 502 `gateway_unreachable`, 423 `write_unverified`, and 403 `authorization_denied`. The pathway does not distinguish those outcomes. In particular, a 502 means the write outcome is unknown, yet the live route tells the patient it failed and immediately terminates the conversation. Because `/sign` lacks an idempotency key, automatically retrying that unknown write would risk a duplicate booking.

The graph contains no verification-on-unknown branch. A truthful outcome for 502 or 423 would require a distinct route and read-after-write verification design; the current export has neither. The 403 case is a definite denial and can remain a non-success handoff, but it should not share patient-facing semantics with an unknown commit state.

## Scope and uncertainty

The shadowing and never-match conclusions rely on the local catalog contract that a successful `/conflict-check` returns a boolean conflict field and that failed/missing responses make `ok != true` match. If Bland represents missing variables differently from the pathway design rules or the deployed gateway violates that catalog contract, runtime behavior would need platform evidence to resolve; no such live evidence was requested or used here.
