# EXISTING PLUMBING

The production gateway has a raw-date resolver, but its present conflict signal means **ambiguity inside the raw patient text**, not disagreement between raw text and the pathway extraction.

- `resolve_from_conversation()` reads only the latest user message and passes it to `extract_date_from_text()`; a parsed range becomes `(start, end)`, while a single result is duplicated as `(resolved, resolved)` (`bland_gateway.py:1261-1299`). It does not accept or inspect the webhook body's `from` or `to` values (`bland_gateway.py:1261-1299`).
- The deterministic parser returns `("conflict", date1, date2, display1, display2)` when the latest raw message contains at least two distinct surviving dates, only for tenant `mott`, unless correction language such as `wait` or `actually` is present (`bland_gateway.py:1137-1189`). It suppresses an adjacent weekday/date mismatch of exactly one day as a spoken-label error, while larger mismatches survive (`bland_gateway.py:1144-1171`).
- The same tuple shape is also returned for the parser's built-in ambiguity around `next <weekday>` and `next weekend`, when the imminent and following-week readings differ (`bland_gateway.py:1197-1225`).
- Raw resolution runs only when raw-date handling is enabled, tenant is `mott`, a call ID or live text exists, and `first_available` is false (`bland_gateway.py:1421-1431`). The gateway chooses current-turn verbatim/live text over lagging fetched history using the checks at `bland_gateway.py:1433-1470`, then optionally refetches only when no usable user message exists (`bland_gateway.py:1471-1483`).
- Today, `clamp_availability_range()` sets `body["date_conflict"] = raw_from` and logs `date_source=conflict` only when `raw_from` is already a tuple whose first item is `conflict` (`bland_gateway.py:1594-1601`). A normal raw date instead **overwrites** the pathway's `body["from"]` and `body["to"]` and logs `date_source=raw` (`bland_gateway.py:1614-1616`). If raw authority is absent or an exception occurs, it leaves the pathway values in place and logs fallback/error fallback (`bland_gateway.py:1617-1620`), after which those values are normalized and clamped (`bland_gateway.py:1634-1651`).
- Caller-supplied conflict fields are discarded before clamping, and internally generated signals are removed from CLI arguments and preserved for the HTTP handler (`bland_gateway.py:2141-2158`).
- When a conflict signal exists, `/availability` performs no schedule search. It returns HTTP 200 with `{ok: true, result: availability_envelope([]) + date_conflict}` (`bland_gateway.py:2889-2907`). The empty envelope has real `count: 0`, two padded blank slots, and `time_pref_relaxed: ""` (`bland_gateway.py:2290-2328`). The conflict array carries the five tuple members: marker, two machine dates, and two display options (`bland_gateway.py:1183-1189`, `bland_gateway.py:2900-2907`).
- What it does **not** do: it never compares a normal raw resolution with the pathway-extracted request `from`/`to`. The raw resolver has no body-date input (`bland_gateway.py:1261-1299`), and the normal raw branch overwrites those request values without a comparison (`bland_gateway.py:1614-1616`).

The v92 pathway already contains the historical clarify plumbing:

- Four webhook nodes consume `/availability`: `n_search` (`pathway-v92.json:2453-2618`), `n_page_2` (`pathway-v92.json:2623-2732`), `n_page_3` (`pathway-v92.json:2742-2839`), and `n_page_near` (`pathway-v92.json:2851-2951`). Only `n_search` maps `$.result.date_conflict[3]`, `[4]`, and `[0]` into `conflict_option_1`, `conflict_option_2`, and `date_conflict_detected` (`pathway-v92.json:2511-2522`).
- `n_search` routes the conflict before any slot-count route (`pathway-v92.json:2552-2569`), matching the restored design requirement (`SPEC-v91.md:520-522`).
- `n_date_conflict` already asks with the two display variables and waits for the patient (`pathway-v92.json:1970-1982`). It has one generic return edge to `n_search` when the patient chooses a conflicting date (`pathway-v92.json:46-58`). The specification confirms this restored historical shape as one node and two edges, and says the node carries the five extraction variables (`SPEC-v91.md:45-46`, `SPEC-v91.md:476-482`).

# GAP

The missing signal is a **week-level cross-authority comparison**:

1. Preserve and normalize the pathway's incoming `from`/`to` before a normal raw result can overwrite them.
2. When raw yields one readable date/range, compare its calendar-week identity with the normalized pathway window. A conflict exists only when the requested date/window and raw date/window resolve to different weeks. A same-day or same-week difference, including a day-part-only difference, is not a date conflict; search the pathway-selected whole day under the ruling.
3. Return both candidate dates as structured options without overwriting the pathway date when a week conflict is emitted.
4. Know whether this conversation has already consumed its single clarification. No such once-per-conversation state or request field exists in the inspected conflict route; the current node simply re-extracts and returns to `n_search` (`pathway-v92.json:46-58`, `pathway-v92.json:1970-1982`).

Unreadable raw authority is already behaviorally compatible with the ruling: `raw_from` absent leaves pathway extraction intact (`bland_gateway.py:1617-1618`), and exceptions do the same (`bland_gateway.py:1619-1620`).

# MINIMAL WIRING

## Gateway side: 3 localized changes

1. **Snapshot and normalize pathway authority in `clamp_availability_range()`.** Immediately before raw resolution can mutate the body, retain the normalized incoming `from`/`to` as `pathway_from/pathway_to`. Reuse `resolve_relative_date()` and the existing date parser/clamp semantics rather than introduce a second date grammar; the current final normalization lives at `bland_gateway.py:1634-1651`.
2. **Add the week-level comparator before the normal raw overwrite branch.** After `resolve_from_conversation()` produces a normal readable raw date/range (`bland_gateway.py:1470-1500`), compare ISO week-year/week pairs for the pathway and raw windows. Emit only if their accepted windows do not touch the same calendar week. Same-week discrepancies do not clarify. If the only disagreement is day part, clear time narrowing for that request so availability searches the whole selected day. If raw is unreadable, retain the existing fallback (`bland_gateway.py:1617-1620`).
3. **Emit the existing five-item structured conflict and skip overwrite/search.** Construct `("conflict", pathway_date, raw_date, pathway_display, raw_display)` using concrete `MM/DD/YYYY` values and patient-facing weekday/date labels; attach it as `body["date_conflict"]` and do not execute the normal `body["from"], body["to"] = raw_from, raw_to` assignment (`bland_gateway.py:1594-1616`). The existing deferred-signal and HTTP response machinery can carry it unchanged (`bland_gateway.py:2141-2158`, `bland_gateway.py:2889-2907`). Preserve option provenance or ordering deterministically so the selected answer maps back to the correct date.

## Pathway side: reuse 1 node, make 2 answer edges, add one guard variable

1. **Clarify node:** reuse `n_date_conflict`; update its prompt to the ruled copy and retain its date extraction variables so the chosen answer becomes the next `preference_from/preference_to` (`pathway-v92.json:1970-1982`; historical requirement at `SPEC-v91.md:476-482`). No new node is needed.
2. **Two explicit answer edges:** replace the single generic return edge with two routes from `n_date_conflict` to `n_search`: option 1 selected and option 2 selected. Each route must cause the extraction/search turn to use that option's concrete date. The current single return edge is at `pathway-v92.json:46-58`; the historical design budget is two edges (`SPEC-v91.md:45-46`).
3. **Once-per-conversation guard:** add a conversation variable such as `date_clarify_used`, default false and set true when `n_date_conflict` is entered or answered. Gate `n_search`'s existing conflict route (`pathway-v92.json:1054-1066`) on `date_conflict_detected == conflict AND date_clarify_used != true`. On any later conflict, do not route back to the clarify node; honor the patient's already selected pathway date and continue the availability path. The gateway should receive the guard (or a resolved-date override) so it cannot return another no-search conflict envelope that leaves `slot_count == 0`; this is a field/condition addition, not another node.

WIRING_SIZE: 3 gateway changes, 1 pathway nodes/2 edges

# COPY DRAFT

EN: “I want to make sure I get the right day. Did you mean Thursday 08/06 or Thursday 08/13?”

ZH parity is required: the same one-question, two-date choice must be authored and tested in Chinese, preserving both exact dates and adding no third interpretation.

# RISKS

- **Loop after the answer:** raw history may still contain the earlier conflicting wording or lag the selection. Guard with `date_clarify_used` at both the pathway route and gateway conflict-emission point; after one clarify, the selected pathway date wins.
- **Over-asking on harmless disagreement:** comparing exact dates would fire for same-week or day-part differences. Compare calendar week-year/week only; day-part-only disagreement searches the whole day.
- **False conflict from unreadable or stale raw text:** raw fetch/live variables can lag (`bland_gateway.py:1402-1417`). Require a readable normal raw date and retain the current fallback behavior; do not infer a conflict from `None`, templates, or parse failure.
- **Range ambiguity:** a pathway range and raw date could partially overlap. Treat any shared calendar week as agreement; clarify only when the week sets are disjoint.
- **Answer maps to wrong authority:** display-label order can drift from machine-date order. Keep each option as a paired machine/display value and test both branches.
- **Conflict envelope falls through after guard:** the current envelope has `count: 0` and no search (`bland_gateway.py:2290-2328`, `bland_gateway.py:2900-2907`). Once the guard is used, the gateway must suppress the conflict response and actually search the selected pathway date.

# TEST PLAN

1. **Agreement:** pathway `08/06/2026..08/06/2026`, raw “Thursday 08/06.” Assert one `/availability` search, no `date_conflict`, no `n_date_conflict`, and normal offer/empty routing.
2. **Same week:** pathway and raw resolve to different days in the same ISO week. Assert no clarify and document which pathway window is searched.
3. **Day-part-only disagreement:** same date, conflicting/changed day part. Assert no clarify and that the search covers the whole day with no time-band narrowing.
4. **Week conflict:** pathway `08/06/2026`, raw `08/13/2026`. Assert no EyeCloud search on the first call, HTTP 200, `result.date_conflict == ["conflict", "08/06/2026", "08/13/2026", ...both labeled options...]`, and exactly one transition to `n_date_conflict`.
5. **Choose option 1:** answer “08/06.” Assert the first answer edge selects `08/06`, a real availability search runs, and the normal booking path receives only returned slots.
6. **Choose option 2:** answer “08/13.” Assert the second answer edge selects `08/13` and follows the same verified search/booking path.
7. **Conflict again:** after either answer, force stale raw history to reproduce the original disagreement. Assert `date_clarify_used == true`, no second clarify question, the chosen pathway date is searched, and the conversation advances.
8. **Unreadable raw authority:** fetch failure, malformed payload, and no parseable date. Assert pathway `from`/`to` survive, `date_source=fallback` or `date_source=error_fallback` is logged, and no clarify fires (`bland_gateway.py:1617-1620`).
9. **Language parity:** run the week-conflict and repeat-conflict scenarios in ZH. Assert exactly one Chinese question contains both dates and the follow-up never loops.
