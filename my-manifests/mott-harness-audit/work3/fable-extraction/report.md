# Extraction Reliability

## Summary

- The non-determinism is structural, not verbal: three nodes (`n_ask`, `n_reask`, `n_negotiate`) ask a small model to classify one patient sentence into five interdependent fields, and `n_search` forwards those fields verbatim to a receiver that rejects anything it cannot parse. No description rewrite can make a sampled classifier deterministic; the 2-of-6 failure on identical input proves it.
- The one field defined as a closed choice (`time_pref`: "exactly one of these four words") was correct in all six runs; every field defined by open-ended prose misfired in at least one measured run. Constraint works; prose does not.
- Recommendation: capture ONE free-text field that transcribes the patient's timing words, and let gateway code — which already contains `resolve_relative_date` — derive `from`/`to`/`after`/`before`/`time_pref` deterministically. Separately, close the deployment gap (Mott on task definition 18 without the resolver) immediately.

## Findings

### Finding: Five-field semantic classification is the failure point, and rewording cannot fix it
Evidence: The shared `extractVars` on `n_ask`, `n_reask` and `n_negotiate` (generated from `PREFERENCE_VARS` in build_v41.py) require the model to split one sentence into `preference_from`, `preference_to`, `preference_after`, `preference_before`, `time_pref`, including mappings like "next week → monday/friday". Six identical runs of "next week in the morning please" produced two broken captures; on v41, "after 3pm" put the literal string `after 3pm` into both date fields. Three rounds of description tightening moved the failure rate without eliminating it.
Impact: Roughly one patient in three who answers in a natural phrasing gets an apology and a request to rephrase — or, on v38, a dead conversation — despite having answered clearly.
Fix: Remove the classification task from the model. Replace the five extracted fields with a single transcription field and derive the five search parameters in gateway code (see Recommendation).
Priority: P0
Confidence: high

### Finding: A working deterministic resolver exists but is not deployed to Mott
Evidence: MEASURED-EVIDENCE.md: `resolve_relative_date` in the gateway handles every rejected phrase ("next week", "in 3 days", "this weekend", Chinese equivalents) and `/availability` already runs `from` and `to` through it — on CVC (task definition 34). Mott runs task definition 18, where every resolver-only phrase returns HTTP 409.
Impact: Even when extraction works perfectly and faithfully passes "next week", the Mott patient's search fails; on the same input a CVC patient's would succeed. This multiplies the extraction failure rate for no reason.
Fix: Redeploy the Mott gateway service onto the task definition carrying the resolver (parity with 34). This is a deploy, not a code or graph change, and shrinks the set of fatal capture variants before any redesign ships.
Priority: P0
Confidence: high

### Finding: Unfilled variables arrive as JSON null and are rejected, defended only by prompt text
Evidence: MEASURED-EVIDENCE.md: the platform substitutes an unfilled variable as a real `null`, stripping the quotes from the `n_search` body, and `/availability` returns HTTP 400 "field 'after' must be a string". The only defense is the sentence "This field must NEVER be left blank" repeated in all five descriptions on `n_ask`, `n_reask`, `n_negotiate` — a prompt-level patch for a transport-level problem, enforced by the same unreliable model.
Impact: A capture that merely omits a field (rather than mis-filling it) still kills the search; the patient is re-asked or, pre-v41, dropped.
Fix: Make the gateway accept `null`/missing for optional fields and treat them as the existing `none` sentinel. One guard clause per field; removes an entire failure class regardless of which capture design wins.
Priority: P1
Confidence: high

### Finding: The strict receiver converts capture variance into patient-visible failure
Evidence: `n_search` posts the five variables verbatim to `/availability`, which 409s on "next week", "this week", "in 2 weeks", "day after tomorrow", "in 3 days", "this weekend". `n_search` has `retryAttempts: 0`; its `ok != true` pathway routes to `n_reask`.
Impact: On v41 a rejected search no longer ends the conversation (v38's HTTP 409 death), but the patient who answered perfectly well is apologised to and asked to "name a specific day" — and a patient who repeats a natural phrasing loops there.
Fix: Subsumed by the resolver deployment (P0 above) plus null tolerance (P1). If the single-field redesign ships, the strict contract becomes acceptable because code, not the model, produces the values.
Priority: P1
Confidence: high

### Finding: The measured evidence shows constrained output is stable where free text is not
Evidence: `time_pref`, described as "Exactly one of these four words: morning, afternoon, evening, none", was `morning` in all six runs — the only field with a perfect record. The free-prose date fields failed in 2 of 6 runs and again on v41.
Impact: None directly; this is the measurement that tells us which mechanism to bet on: closed choices and code, not richer prose.
Fix: Where any extracted field must remain, phrase it as a closed enumeration of literal tokens, as `time_pref` already is.
Priority: P2
Confidence: medium

## Clean

- `PREFERENCE_VARS` is defined once in build_v41.py and shared by `n_ask`, `n_reask`, `n_negotiate` — no drift between the three capture points.
- `n_search`'s pathway ordering is safe: `slot_count == "1"` / `>= "2"` / `== "0"` cannot match on a failed call, and `ok != true` catches the remainder into `n_reask`, so a 409 degrades instead of killing the conversation (the v38 death mode is closed).
- `n_verify_1` and `n_verify_2` put the `ok != true` health check first, so a failed conflict check cannot fall through to booking.
- The `none` sentinel is accepted and ignored by the gateway, so the "not specified" convention itself is sound.

## Assumptions

- The platform's `extractVars` supports only the `"string"` type seen in v41_graph.json; no true enum/schema-constrained extraction exists, so "enumeration" can only be simulated by description wording.
- The gateway code can be modified (add a parsing path / new request field) and Mott's task definition can be redeployed; nothing in the sources says otherwise.
- The chat-harness `variables` output (pathway_harness.py) faithfully reflects what a live SMS conversation would capture.
- A single transcription field ("the patient's own words about timing, copied as said") is materially more stable than five-way classification — copying is a simpler task than classifying — but this is untested here and must be measured by the acceptance run below.

## Recommendation

Weighing the options:

1. **Rewrite the descriptions again** — near-zero cost, but three measured rounds moved the failure rate without eliminating it; a sampled small model classifying into five fields cannot be worded into determinism. Proof would be N identical runs, which can only bound, never eliminate, the rate. Rejected.
2. **Fewer fields** (drop `preference_after`/`preference_before`) — small graph edit; loses clock-time windows like "after 3pm", and the surviving date fields still received "next week" and "after 3pm" in measured runs. Shrinks the target, keeps the mechanism. Rejected.
3. **One combined free-text field, normalised downstream in code** — the model's only job becomes transcription; code decides every field, so the same words always produce the same search. Costs a gateway change and a rebuilt `n_search` body; cannot fix a model that paraphrases the transcription, but any given string then parses identically every time. **Chosen.**
4. **Tolerant receiver over the existing five fields** — the resolver deployment and null tolerance are worth shipping regardless (P0/P1 above), but the wrong-field class ("morning" in `preference_after`, "after 3pm" in both date fields) forces open-ended server heuristics to reconstruct what the model scrambled, and information the model dropped is unrecoverable. Partial adoption, not the mechanism.
5. **Constrained enumeration** — measured to work (`time_pref`), but days-plus-dates ("august 3") cannot be enumerated, and no real enum type exists on the platform (Assumptions). Use it for any field that must remain extracted; insufficient alone.

**Implement option 3.** Concretely: replace the five-entry `extractVars` on `n_ask`, `n_reask`, `n_negotiate` with one field, e.g. `preference_raw` — "the patient's words about when they want to come in, copied exactly as they wrote them"; change `n_search`'s body to send `{"store": ..., "raw": "{{preference_raw}}", "slot_minutes": "15"}`; in the gateway, parse `raw` with `resolve_relative_date` plus a clock-time/part-of-day splitter into the existing internal from/to/after/before/time_pref, with the monday–friday and `none` defaults applied in code, tolerant of null/empty. Ship the two P0/P1 gateway items first as an independent mitigation.

**Executable proof:** (a) a gateway unit corpus asserting every phrase in the accepted/rejected table of MEASURED-EVIDENCE.md — including "next week in the morning please" and "after 3pm" — parses to the identical parameter set on every call; (b) a repeat-run harness: for each timing scenario in scenarios.py ("vague week request", "clock time with no day at all", "texting shorthand for next tuesday", "two days offered at once"), run pathway_harness.py 20 times against the new version and assert every run ends on `n_offer` with byte-identical captured variables and zero HTTP 409/400 from `/availability`. Baseline is 2 failures in 6; acceptance is 0 in 80.
