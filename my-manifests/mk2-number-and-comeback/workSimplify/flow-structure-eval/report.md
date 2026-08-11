# Mott SMS booking pathway v92: structure and simplification options

Scope: read-only analysis of `pathway-v92.json`, the two `workG` wiring reports, `DIFF-INVENTORY.md`, `SPEC-v91.md`, and the deployed `bland_gateway.py` snapshot. Counts below are mechanical unless labeled inference. The locked rulings are treated as constraints: HYBRID interpretation remains; week disagreement gets at most one clarification and then proceeds; answer latency is at most 15 seconds and filler is removed; clock times require fresh slot data; Mott ships first and the shape remains CVC-ready.

## 1. Structure inventory

### Graph and node purposes

The graph contains **48 nodes and 125 edges**.

| Type | Count | Purpose breakdown | Node ids |
|---|---:|---|---|
| Webhook | 14 | identity 1; availability reads 4; slot verification 2; booking writes 2; suppression writes 2; appointment read/reconciliation 3 | `n_identity`; `n_search`, `n_page_2`, `n_page_3`, `n_page_near`; `n_verify_1`, `n_verify_2`; `n_book_1`, `n_book_2`; `n_suppress_stop`, `n_suppress_not_me`; `n_appt_check`, `n_reconcile_1`, `n_reconcile_2` |
| Default | 21 | greeting/intake 1; clarification/recovery 7; offers 4; offer disambiguation 1; confirmation gates 2; negotiation 1; lost-slot recheck 1; booking confirmation 1; help/office/FAQ 3 | `n_ask`; `n_date_conflict`, `n_clarify`, `n_miss_empty`, `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, `n_miss_time`; `n_offer`, `n_offer_2`, `n_offer_3`, `n_offer_near`; `n_which_intent`; `n_gate_1`, `n_gate_2`; `n_negotiate`; `n_recheck`; `n_confirm`; `n_help`, `n_office`, `n_faq` |
| End Call | 13 | booked outcomes 2; safe/unknown/failure outcomes 4; decline, timeout, suppression, existing-appointment, office, and post-booking deferral outcomes 7 | `e_booked`, `e_booked_recovered`; `e_safe_identity`, `e_safe_failure`, `e_booking_failed`, `e_book_unknown`; `e_declined`, `e_timeout`, `e_stop`, `e_not_me`, `e_existing`, `e_office`, `e_defer` |

### Every webhook call site

| Endpoint/purpose | Call sites | Count |
|---|---|---:|
| `POST /patient-search` | `n_identity` | 1 |
| `POST /availability` | `n_search` (`time_pref=none`), `n_page_2` (`afternoon`), `n_page_3` (`late`), `n_page_near` (`afternoon`) | 4 |
| `POST /conflict-check` | `n_verify_1`, `n_verify_2` | 2 |
| `POST /sign` with `appt.book` | `n_book_1`, `n_book_2` | 2 |
| `POST /sms-suppression` | `n_suppress_stop`, `n_suppress_not_me` | 2 |
| `POST /appt-list` | `n_appt_check`, `n_reconcile_1`, `n_reconcile_2` | 3 |

The availability request body is duplicated four times. The bodies differ mainly by `time_pref`; all carry `preference_from`, `preference_to`, `time_after`, `callID`, `lastUserMessage`, and `user_verbatim`. The two verify, two book, and two reconcile branches are also parallel copies keyed to slot 1 versus slot 2.

### Every date interpretation or transformation site

There are **three overlapping interpretation layers**, plus downstream normalization:

1. **Pathway LLM extraction.** Nine nodes contain extraction configurations. Eight carry the full five-variable set `user_verbatim`, `preference_from`, `day_part`, `time_after`, `preference_to`: `n_ask`, `n_date_conflict`, `n_miss_empty`, `n_miss_unread`, `n_miss_thin`, `n_miss_unbookable`, `n_miss_time`, `n_negotiate`. `n_clarify` carries `user_verbatim`, `preference_from`, and `preference_to`. Thus the long date rules are copied into nine node configurations, and eight also interpret time-of-day/clock bounds.
2. **Gateway deterministic raw-text authority.** `clamp_availability_range` chooses among `user_verbatim`, `user_text`, and fetched conversation history; `resolve_from_conversation` selects the latest user turn; `extract_date_from_text` interprets it. A successful raw result assigns `body["from"]` and `body["to"]`, overriding pathway values. `first_available` overrides both. This is the silent precedence responsible for tonight's correct pathway extraction being replaced.
3. **Gateway LLM intent.** `llm_interpret_intent` extracts date words and passes them back through `extract_date_from_text`. In authoritative mode it runs only if the deterministic raw parser returns no date; in shadow mode it logs only. It is still a third interpretation policy with a separate prompt and classification contract.
4. **Gateway normalization after authority.** `resolve_relative_date` converts remaining textual `from`/`to` values to dates; `clamp_availability_range` collapses invalid/inverted ranges and caps spans at 14 days. This is transformation rather than a fourth intent source.

The current precedence is therefore `first_available` > successful gateway raw interpretation > gateway LLM only when raw is empty > pathway `from`/`to` fallback > relative-date normalization. The HYBRID ruling exists in code, but the contract does not make disagreement handling symmetric: gateway success overwrites rather than reconciles.

### Copy duplication

- **21** nodes have prompts. **20** contain the same `ABSOLUTE RULE ON TIMES` block and the exact sentence `One moment while I check the schedule for you.`: every prompt node except `n_date_conflict`.
- `n_negotiate` additionally instructs the second filler variant, `Let me check that for you.` Its prompt therefore contains both variants.
- The same long background/safety/presentation rules are copied across those 20 nodes. Date extraction instructions are separately copied across nine extraction-bearing nodes. A copy or policy change is consequently a 20-edit or 9-edit operation, not a single contract change.

### Greeting-to-offer routing

`n_identity` is the sole explicit start, then `n_appt_check` reaches greeting `n_ask`. From `n_ask`, all ordinary timing replies enter `n_search`. There are **7 condition-distinct acyclic initial routes** from the greeting to a slot offer, at **2 to 4 edges** after `n_ask`:

- Depth 2: two conditions (`slot_count == 1`, `slot_count >= 2`) both end at `n_offer`.
- Depth 3: `n_page_2 -> n_offer_2`, `n_page_2 -> n_offer_near`, `n_page_3 -> n_offer_3`, and `n_page_3 -> n_offer_near`.
- Depth 4: `n_page_3 -> n_page_near -> n_offer_near`.

That finite count describes the initial acyclic decision tree only. Nine nodes feed back to `n_search` (`n_date_conflict`, six other clarification/miss nodes, `n_negotiate`, and `n_recheck`), so patient-interactive path depth is unbounded. Most importantly, `n_date_conflict -> n_search -> n_date_conflict` has no state bit, attempt counter, or alternate second-pass edge. Although `n_date_conflict` extracts the answer, its sole explicit outgoing route merely says “patient chooses one conflicting date” and returns to the same authority logic that can recreate the conflict.

### Unreachable or vestigial structure

- `e_booking_failed` has zero inbound edges and is not global. It is vestigial after the reconciliation branches were added.
- A plain edge traversal from `n_identity` cannot reach `n_help`, `n_faq`, `n_office`, `n_suppress_stop`, `n_suppress_not_me`, `e_existing`, or their terminal outcomes. This does **not** prove they are dead: their `isGlobal`/`globalLabel` behavior is Bland runtime routing outside ordinary edges. They should be inventoried as implicit global entry points, not deleted based on graph reachability.
- `n_help` has no outgoing edge and relies on global auto-return semantics. That is structurally implicit and harder to validate than an edge.

## 2. Friction map

| Measured failure | Structural cause | Why it produces the observed result |
|---|---|---|
| Three date interpreters disagree; raw overrides correct extraction | Nine pathway extraction copies feed four availability nodes, while `clamp_availability_range` independently parses current/fetched raw text and may invoke `llm_interpret_intent`; successful raw parsing overwrites `from`/`to` | HYBRID has no explicit reconciliation record or disagreement policy. One source is silently authoritative rather than evidence being compared. Historical comments show the extra sources were added to compensate for lag/stale extraction, so incident fixes accumulated into precedence by code order. |
| `n_date_conflict` fail-stay trap | `n_search` emits a conflict tuple to `n_date_conflict`; that node asks and extracts, but has only one return route to `n_search` and no `clarification_consumed`/attempt state | The same gateway interpreter can regenerate the same conflict indefinitely. Tonight's three answers, correct extraction, repeated question, and zero successful search calls match this loop. |
| Recall greeting twice, 3 seconds apart | The graph has one explicit greeting owner, `n_ask`, after silent `n_identity -> n_appt_check`; `n_ask` also declares itself “the very first message this patient receives” | The second send is not explained by duplicate graph greeting nodes. The structural risk is split send ownership between the pathway start and the external recall launch/campaign. Exact origin needs message-id/send-owner telemetry; the repository evidence supports an ownership boundary defect, not a proven second node. |
| Filler SMS before real answer | The exact filler is embedded in 20 prompts, while `n_negotiate` has a second variant and immediately routes to silent search | A no-information Default node emits an SMS and the webhook returns the real answer about 0.3 seconds later. The patient pays an extra message and the team must edit up to 20 prompts to remove the policy. |
| Raw conflict tuple leaks into patient copy | Gateway returns positional `date_conflict` data; `n_search` maps tuple indexes 3/4 to `conflict_option_1/2`; `n_date_conflict` interpolates them directly into an LLM prompt | There is no presentation-safe conflict object or formatter boundary. Internal parser fragments become patient copy, allowing duplicated weekday/date phrases such as tonight's malformed question. |

## 3. Simplification options

### Option A: Contracted Hybrid Funnel

**Structural change.** Keep both pathway extraction and gateway reinterpretation, preserving HYBRID, but replace silent overwrite with one typed comparison contract at `/availability`: `pathway_hint`, `gateway_read`, `decision`, `decision_source`, `disagreement_kind`, `clarification_count`, and presentation-safe `clarification_options`. Merge `n_search`, `n_page_2`, `n_page_3`, and `n_page_near` into one `n_availability` call site; the gateway owns band progression/relaxation and returns the two offerable slots plus a route code. Merge `n_offer`, `n_offer_2`, `n_offer_3`, and `n_offer_near` into one `n_offer`. On week disagreement, route once to `n_date_conflict`; its answer returns with `clarification_count=1`, after which the gateway must choose the clarified current-turn reading and search, never emit another clarification. Remove both filler variants from all prompts. Put shared patient-copy constraints in one reusable prompt block or one offer/clarify renderer. Keep verify-before-book, two booking write branches, reconciliation, and fresh-slot-only clock copy intact.

**Patient difference.** One question at most for a true week mismatch, then an offer. No filler SMS. Conflict wording is clean and deterministic. “Later” requests still work but do not traverse separate page nodes.

**Effort.** **M**: change the availability request/response contract and gateway orchestration; replace four webhook nodes and four offer nodes; add one-attempt state; build Mott fixtures for agreement, disagreement, clarification, bands, first-available, empty results, and the full verify/book/reconcile path; then validate CVC configuration through tenant/store data rather than forked logic.

**Live risk.** **Medium.** It alters the busiest read path and routing envelope, but keeps booking writes and all locked behavioral rulings. Rollout should be shadow comparison first, then Mott-only canary. Latency risk falls because only one availability call and no synchronous filler turn are needed; the gateway must still prove p95 end-to-end answer latency at or below 15 seconds.

**Locked rulings.** All intact: HYBRID remains explicit; one clarification maximum; filler removed; clock times come only from returned slots; Mott-first, tenant-shaped for CVC.

### Option B: Surgical Contract Repair

**Structural change.** Keep the four availability and four offer nodes. Add explicit precedence and `clarification_count` to the existing gateway contract; make the clarified current turn final after one question; return formatted conflict options; remove filler from the 20 prompts and the `n_negotiate` variant; add a send-owner/idempotency key around `n_ask`. Centralize the duplicated prompt text if the pathway platform supports a shared block; otherwise this option fixes behavior without materially reducing graph branching.

**Patient difference.** The five live failures stop, but later/near searches still traverse the existing multi-message graph and four availability variants.

**Effort.** **S–M**: small graph and gateway changes, but all nine extraction sites and four request bodies need regression validation because duplication remains.

**Live risk.** **Low–medium**, the lowest migration risk. Its main cost is retained structural debt: the next incident can again require parallel edits.

**Locked rulings.** All intact.

### Option C: Gateway Authority, Pathway Hints

**Structural change.** Merge the same four availability nodes and four offer nodes as Option A, but make pathway date extraction diagnostic hints only; the gateway becomes the sole date decision authority and returns a complete, presentation-safe scheduling result. The pathway retains extraction telemetry but cannot determine `from`/`to`.

**Patient difference.** Same simplified experience as Option A, with fewer live precedence combinations.

**Effort.** **L**: rebuild the authority contract, fixtures, observability, fallback behavior, and tenant compatibility; revalidate every date phrase and stale-history case that originally motivated pathway extraction.

**Live risk.** **High** because gateway fetch lag or parser misses would no longer have a pathway-authoritative fallback.

**Locked rulings.** **ASK-ANKIT:** this demotes pathway extraction from a decision participant to a hint and therefore revisits the 2026-08-03 HYBRID ruling. Do not select or build without re-ruling. The other four rulings can remain intact.

## 4. Recommendation

Choose **Contracted Hybrid Funnel**. The measured structure has four availability call sites, four offer nodes, nine repeated extraction configurations, 20 duplicated safety/filler blocks, seven initial offer routes, and an unbounded clarification loop. Surgical repair is safer tonight but leaves the mechanism that made incident fixes multiply. Gateway-only authority is cleaner on paper but crosses the locked HYBRID ruling and removes a fallback added for measured gateway/history lag.

The recommended design makes HYBRID explicit instead of accidental: two readings are compared at one funnel, one disagreement can ask one safe question, and the second turn must search. It also fixes the latency and copy defects at their ownership boundaries rather than editing symptoms in 20 prompts. Acceptance requires fixture coverage for each route code, proof that a second conflict cannot occur after clarification, exactly one greeting send owner/idempotency key, no filler strings in any patient output, no raw tuple fields entering copy, clock-time provenance from the current availability response, and Mott p95 answer latency at or below 15 seconds.

**IF WRONG:** consolidating band progression into the gateway could change which two slots are offered or mishandle a rare negotiation path, causing missed booking opportunities even if no unsafe booking occurs. Contain that cost with response-by-response shadow comparison against v92, Mott-only canarying, and a reversible route switch while leaving verify/book/reconcile untouched.

OPTIONS=3 RECOMMEND=Contracted-Hybrid-Funnel
