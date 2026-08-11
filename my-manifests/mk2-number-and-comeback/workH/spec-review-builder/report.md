# Coverage method

CANARY: blue paperclip

I read `SPEC-v91.md` in full, then built three independent checklists: (1) all 150 classified v86-to-v90 diff rows and their deliberate/FIX-LOSS/UNKNOWN dispositions from `DIFF-INVENTORY.md`; (2) every pathway-side extraction, request-body, response-mapping, route, prompt, and HELP-node requirement in `workG/provenance-fix-week/report.md`; and (3) every `/availability` request/control field, precedence rule, absent-field effect, and response-routing requirement in `workG/gateway-contract/report.md`. I checked each item against the v86-rebase rule, section 2's four deltas, the byte-identity preservation rules, and validator assertions 1-34. This covers the v62 additions, v88 reconcile branch, deliberate greeting replacement, all 113 FIX-LOSS rows, all three UNKNOWN rows, and the gateway's request/response contract.

# Gaps found

1. **REQUIRED cross-source conflict over `user_text` and `user_verbatim`.** The fix-week rebuild checklist requires all four availability bodies to retain both fields. SPEC-v91's P-A rule instead authorizes the builder to remove both from all four bodies if the deployed gateway rejects them. Assertion 10 correctly follows whichever shape P-A proves, so the spec is internally executable, but its deletion branch would knowingly produce a graph missing two pathway-side carriers that the independent fix-week source calls required. Amend the spec before build: either make the fields mandatory and resolve gateway acceptance outside the graph change set, or explicitly state that a failing P-A supersedes the fix-week carrier requirement and record that exception as a deliberate delta.

2. **REQUIRED contract-minimum field `first_available` is not placed in the four availability request bodies or asserted by the validator.** The gateway contract's minimum body shape includes `first_available`, with false/empty for non-soonest searches. SPEC-v91 discusses its semantics and uses it in a probe explanation, but section 2 never says to include it in `n_search`, `n_page_2`, `n_page_3`, or `n_page_near`, and assertions 10-11 do not check it. Because v86's retained body checklist in the fix-week source does not list the field, rebase inheritance does not close this omission. Runtime currently treats absence as false, so this is not evidence of an immediate behavior failure; it is still a completeness miss against the gateway contract's stated “should contain at least” request shape. Amend the four bodies to send an explicit false/empty value, or document and validate an intentional exception.

No other omissions or wrong values were found. In particular, the spec preserves or restores the complete extraction sets and long-form prompts; `callID`, date range, `after`, `before`, time band, slot duration, store, and diagnostic carriers (subject to gap 1); real `count` routing; both slots' start/end/doctor/day fields; `time_pref_relaxed`; conflict mappings and ordering; HELP behavior through byte-identical v86 preservation; day-labelled offer copy; retries only on reads; the v62 close/defer/gate/label changes; all v88 reconcile nodes, copy, ordering, and no-write-retry rules; and the deliberate greeting while rejecting the other v90 stale-base residue.

# recommendation

**Amend first.** Resolve the `user_text`/`user_verbatim` source-of-truth conflict and explicitly decide the `first_available` body field, then build. Confidence: 94%. The first issue leaves a required fix-week field contingent without an explicit supersession rule; the second is a contract-completeness issue with low present runtime risk because absence is treated as false.

# unique_catches

- The dangerous item is not a validator contradiction: assertion 10 adapts to P-A. It is a source-of-truth conflict because P-A grants permission to delete fields that the fix-week source calls required without explicitly superseding that requirement.
- `first_available` is named in SPEC-v91's contract discussion, so keyword coverage can look complete even though no construction rule or graph assertion puts it in any request body.
- The HELP node's detailed fields are not all restated in section 2, but this is not a gap: the v86 rebase plus the byte-identical-node rule preserves the complete node. The same inheritance closes the apparent omissions for `store`, `from`, `to`, `before`, `slot_minutes`, slot ends, doctor IDs, and `time_pref_relaxed` mappings.

# proof_slots

- **Diff inventory:** 150/150 rows accounted for by D1-D4, v86 preservation, or an explicit OPEN decision; no additional deliberate v62/v88/greeting delta was found.
- **Fix-week rebuild checklist:** extraction 9/9 nodes; request wiring 4/4 webhooks; response mappings 4/4; conflict route and return edge; four offer prompts; HELP node. Exception: the P-A deletion branch conflicts with the required diagnostic carriers.
- **Gateway request contract:** `store`, `from`, `to`, `after`, `before`, `time_pref`, `slot_minutes`, and `callID` are inherited/asserted; `first_available` is not constructed/asserted. `doctor` and `min_minutes` are accepted optional inputs, not minimum fields in the contract's pathway example.
- **Gateway response contract:** real `count`, slot fields, `time_pref_relaxed`, and `date_conflict` are inherited or explicitly asserted; padded slot length is not used as availability truth.
- **Deliberate deltas:** v62 graph/copy/label delta, v88 reconcile delta, and greeting delta are specified; D4 is an additional honesty fix and does not erase a required source delta.

```json CITATIONS
[
  {"file":"../../DIFF-INVENTORY.md","quote":"Verified by script: every var v86 extracts, cross-referenced against v90's extraction"},
  {"file":"../../DIFF-INVENTORY.md","quote":"Neither removal is named in SPEC-v62 or SPEC-v88. `n_date_conflict` is the node that"},
  {"file":"../../DIFF-INVENTORY.md","quote":"All four availability-search Webhook nodes (`n_search`, `n_page_2`, `n_page_3`,"},
  {"file":"../../workG/provenance-fix-week/report.md","quote":"On `n_search`, `n_page_2`, `n_page_3`, `n_page_near`, retain: `store`, `from:\"{{preference_from}}\"`, `to:\"{{preference_to}}\"`, `after:\"{{time_after}}\"`, `before:\"none\"`, `time_pref`, `slot_minutes:\"15\"`, `callID:\"{{callID}}\"`, `user_text:\"{{lastUserMessage}}\"`, `user_verbatim:\"{{user_verbatim}}\"`."},
  {"file":"../../workG/provenance-fix-week/report.md","quote":"All four nodes: `ok`, `slot_count`, both slots' `start`, `end`, `doctor_id`, `day_name`, and `time_pref_relaxed` with the JSONPaths shown in v65."},
  {"file":"../../workG/provenance-fix-week/report.md","quote":"`n_help`: all global/auto-return fields and exact help prompt described in the inventory."},
  {"file":"../../workG/gateway-contract/report.md","quote":"The gateway additionally consumes the control fields `time_pref`, `first_available`, and `callID` before strict whitelist validation. Unknown remaining fields fail the request."},
  {"file":"../../workG/gateway-contract/report.md","quote":"\"first_available\": \"<1|true|yes only for an explicit soonest search; otherwise false/empty>\","},
  {"file":"../../workG/gateway-contract/report.md","quote":"`first_available` | Treated as false: authority may engage and caller/conversation dates are used."},
  {"file":"../../workG/gateway-contract/report.md","quote":"For reliable pathway routing, map `count`, slot fields, and `time_pref_relaxed` from the response. In the LLM-intent tier, also map/route `date_conflict` so ambiguous raw language asks the patient to clarify rather than searching. Route on the real `count`, not padded `slots` length: the envelope pads to at least two slot objects to clear stale Bland variables."}
]
```
