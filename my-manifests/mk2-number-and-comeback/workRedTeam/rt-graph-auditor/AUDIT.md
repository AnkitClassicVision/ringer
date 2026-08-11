# Findings

## 1. HIGH - Convention 5: the main offer router is overloaded and materially ambiguous

`n_goal_response` has 10 outbound edges, exceeding the eight-edge reliability limit. The stored production graph’s main n_offer router has eight, so the draft increases the hottest router's load by two edges. Several sibling labels can match the same ordinary reply:

- "11:15" can match both `takes only the first opening offered, including by naming that opening's clock time` (or the corresponding second-opening label) and `names a specific clock time to take, including bare digit forms like 1115, 11 15, or 11:15, rather than replying 1 or 2`.
- "1, but do you have anything later?" can match `takes only the first opening offered, including by naming that opening's clock time`, the offered-date time/latest route, and `both selects an opening and asks for a different day or time`.
- "No, actually Friday" can match `declines this offer`, `states a NEW day, date, week, or time preference different from the offered date`, and `corrects or replaces the offered date with a different specific day, date, or weekday - including replies beginning with no, actually, or I meant`.

This is not only a taxonomy problem. A wrong match can bypass the intended fresh-search or mixed-consent branch and reach a booking gate.

Concrete fix: split `n_goal_response` into deterministic stages with at most eight edges each. Put mixed intent and explicit date/time correction in the first stage, then selection, then preference/decline. Remove clock-time acceptance from the direct gate labels; every named clock value should take the constrained anchor-search route.

## 2. HIGH - Convention 4: three wait prompts may speak clock times without literal templates

`n_office` instructs the model to return to scheduling while `naming the openings still on offer`, but its prompt contains no `{{slot_1_day_name}} {{slot_1_start}}` / `{{slot_2_day_name}} {{slot_2_start}}` templates. `n_faq` contains the same unsafe instruction. `n_mixed_intent` says `never name any time other than the two already offered` but also supplies no literal templates. These nodes can reconstruct or paraphrase stale times from conversation memory, exactly where convention 4 requires template-verbatim rendering.

Concrete fix: either make these nodes time-silent and route back to a fresh search/offer node, or embed the exact protected one- or two-slot templates and require substitution-only rendering. For `n_mixed_intent`, the safer fix is time-silent clarification copy that says “the opening you selected” without repeating a clock time.

## 3. HIGH - Convention 2 compatibility creates a new gap: offered-anchor response rows are simple but not exclusive

`n_goal_search_offered_anchor` uses the required simple triples represented by the verbatim condition labels `ok != true`, `slot_count == 0`, `anchor_exact == true`, and `anchor_exact != true`. Their respective target IDs are `n_goal_ask`, `n_goal_ask`, `n_gate_1`, and `n_time_pick_offer`.

Those rows can simultaneously match. For example, an error payload with a stale/default anchor-exact flag, or a zero-slot payload with that flag, matches both a safe miss row and the booking-gate row. The validator checks syntax and presence, not mutual exclusivity or fail-closed payload combinations.

Concrete fix: have the gateway return one mutually exclusive route enum with exact, closest, none, and error values, then route on four simple equality triples. If the gateway cannot change, add a deterministic normalization webhook that produces that enum before Bland routing.

## 4. HIGH - Convention 5: opt-out and wrong-person intents are uncovered on the live scheduling waits

The graph contains `n_suppress_stop` and `n_suppress_not_me`, but neither has an incoming edge. The only explicit opt-out label on a user-wait node is post-booking `opt-out language`. In particular, `n_goal_ask`, `n_goal_response`, `n_time_pick_offer`, `n_mixed_intent`, `n_gate_1`, `n_gate_2`, `n_date_conflict`, and `n_date_conflict_retry` have no sibling label for STOP/opt-out or “wrong person.” A patient can plausibly express either at every one of these waits. On `n_date_conflict_retry`, the catch-all `after the one allowed re-ask, always continue to search using the best extracted date; never remain on this node` could send STOP into another availability search.

Concrete fix: add highest-priority opt-out and wrong-person routes from every pre-booking wait to their suppression webhooks. Exclude those intents explicitly from catch-all/search labels. Add graph reachability checks proving both suppression nodes have inbound routes from all live pre-booking waits.

## 5. MEDIUM - Convention 5: pre-offer search labels overlap by construction

At `n_goal_ask`, the broad label `says any day, weekday, date, week, weekend, or time preference - including Saturday, this weekend, next week, or a month and day - or asks for the first available, soonest, earliest, or whenever opening - or gives only a time preference when no date has been offered yet - including agreement-phrased times like 3pm works for me when no opening has been offered yet` overlaps both `wants late, latest, last appointment, or end of day` and `asks for a time near, around, or close to a specific clock time`. “Around 3pm,” “latest time,” and “3pm works for me” all satisfy the broad time-preference label as well as a specialized sibling.

Concrete fix: narrow the general search label by explicitly excluding latest/end-of-day and named/near-clock requests, or add a first-stage intent classifier that emits one enum before selecting the search variant.

## 6. MEDIUM - Convention 5: the named-time offer router has overlapping time-change labels

At `n_time_pick_offer`, “4 pm instead” can match `takes the opening offered, including replying 1, yes, or naming its clock time` if 4 pm is the rendered offer, but otherwise matches `wants a different day, date, or time than the one offered`. “Something later” matches both that general different-time label and `wants late, latest, last appointment, or end of day`.

Concrete fix: make acceptance label only bare 1/yes or an exact equality to the rendered slot, route all other named clocks to a constrained anchor search, and exclude latest/end-of-day from the general change label.

## 7. MEDIUM - Convention 5: confirmation catch-alls overlap every specific support intent

Both confirmation nodes have the sibling labels `confirmation delivered`, `change requested after confirmation`, and `anything else requested after booking`. The catch-all necessarily overlaps a change request, while “confirmation delivered” is an internal transition description rather than a patient-message intent. A reply such as “Thanks, actually cancel it” can match the change branch and the catch-all. The same label shape exists on production n_confirm, so this is an inherited defect, not evidence that the draft introduced it.

Concrete fix: send the confirmation directly into one dedicated post-booking wait without a semantic “confirmation delivered” edge, or make the specific change/cancel and opt-out branches explicit and make the fallback label exclude every named sibling intent.

## 8. MEDIUM - Convention 5 / live-route semantics: office handoff has no patient-meaningful continuation

`n_office` is a user-wait Default with one outbound label, `office direction delivered`. That describes what the assistant did, not what the next patient says. Its prompt says to return to booking, yet the graph provides no patient-intent route back to scheduling. If the patient replies “yes” after the office handoff, no sibling label covers that intent. `n_faq` likewise covers only `patient asks to speak to someone`; it has no scheduling acceptance, scheduling preference, decline, opt-out, or fallback route. These two nodes are currently unreachable, but the validator preserves them as topology without detecting that activating either would strand the conversation. Production has the same one-edge shapes, so this is also inherited latent debt.

Concrete fix: either remove unreachable waits, or give each a bounded, patient-semantic router back to a fresh search/offer flow plus decline, opt-out, wrong-person, and fallback handling. Do not route back while repeating old slots from memory.

# Router load table

| User-wait node | Outbound edges | Overlapping sibling intents | Plausible uncovered intents |
|---|---:|---|---|
| `n_date_conflict` | 2 | A rejected named day such as “not Friday” can look both usable and unusable | STOP, wrong person, timeout, help/office request |
| `n_gate_1` | 4 | “No, Friday instead” matches both no/other-times and mismatching date/time | STOP, wrong person, help/FAQ, ambiguous consent |
| `n_gate_2` | 4 | Same collision as `n_gate_1` | STOP, wrong person, help/FAQ, ambiguous consent |
| `n_help` | 0 | None | Every reply; node is isolated with no inbound or outbound edges |
| `n_office` | 1 | None | Yes/resume scheduling, new preference, decline, STOP, wrong person, fallback |
| `n_faq` | 1 | None | Yes/resume scheduling, new preference, decline, STOP, wrong person, fallback |
| `n_date_conflict_retry` | 1 | Catch-all search route can absorb protected intents | STOP, wrong person, timeout; these must not fall through to search |
| `n_post_booking` | 2 | None | Change/cancel/reschedule, question/help, wrong person, ordinary acknowledgement |
| `n_confirm_1` | 4 | Change request and `anything else requested after booking`; acknowledgement and `confirmation delivered` | STOP/opt-out is not explicit here; wrong person |
| `n_confirm_2` | 4 | Same as `n_confirm_1` | STOP/opt-out is not explicit here; wrong person |
| `n_goal_ask` | 5 | General time preference vs latest/end-of-day vs near-clock | STOP, wrong person, help/FAQ/office, unusable or irrelevant input |
| `n_goal_response` | **10** | Named offered clock vs direct gate/anchor; selection-plus-change vs selection/change; correction vs decline/new preference | STOP, wrong person, help/FAQ/office, ambiguous “that works” without identifying a slot |
| `n_time_pick_offer` | 5 | Named-clock acceptance vs different time; general different time vs latest | STOP, wrong person, help/FAQ/office, ambiguous acknowledgement |
| `n_mixed_intent` | 5 | Named-clock confirmation vs new time preference; a second mixed answer can match a gate and search again | STOP, wrong person, help/FAQ/office, still-mixed/ambiguous answer |

# Validator gaps

Assertions worth adding:

1. **All-router edge cap:** enumerate every user-wait `Default` and fail above eight outbound edges, rather than capping only selected nodes.
2. **Semantic collision fixtures:** run adversarial patient utterances against every sibling set. Required fixtures should include named offered clocks, “1 but later,” “No, actually Friday,” “around 3,” “latest,” “Thanks, actually cancel,” STOP, and wrong-person language. Assert exactly one winning edge.
3. **Protected-intent coverage:** require opt-out and wrong-person routes from every reachable pre-booking wait, and prove `n_suppress_stop` / `n_suppress_not_me` are reachable. Catch-all routes must explicitly exclude protected intents.
4. **Response-path exclusivity:** evaluate representative success, zero-result, error, missing-field, and contradictory payloads against each webhook's `responsePathways`; require exactly one match. Specifically fail any `n_goal_search_offered_anchor` payload that can match a safe-miss row and a booking row together.
5. **Template-verbatim closure:** if a prompt tells the model to name, repeat, restate, compare, or refer to an opening/time, require the exact approved slot template in that prompt or require the prompt to be explicitly time-silent and route through a fresh search.
6. **Patient-semantic edge labels:** reject labels that describe internal completion rather than the next patient intent, including `office direction delivered` and `confirmation delivered` on user-wait Defaults.
7. **Reachability plus liveness:** flag unreachable wait nodes and reachable waits with zero edges; for each reachable wait, require timeout, protected intents, and either a bounded fallback or a proved exhaustive partition.
8. **Negative-availability provenance:** for every prompt clause that can say “unavailable,” “no openings,” “no match,” “nothing later,” or equivalent, prove the immediately preceding live route is the matching constrained availability webhook and that no semantic route can make the claim from stale slots.
9. **Prompt/edge consistency:** extract routing claims from prompts and ensure a corresponding edge exists, and ensure every edge label is represented in the prompt. This would expose prompts that promise a return to booking while their node has no scheduling continuation.
