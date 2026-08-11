# Validator coverage

The validator covers the section 6 gate-corruption failure modes statically: `n_appt_check` must exist, preserve conservative-first ordering, route an existing appointment to `e_defer`, and isolate the reconcile-confirmation path. Assertions 24-25 plus R4 catch omission, misrouting, reordering, and unsafe reachability. It also covers section 7's stale-base/classification, position-drift, false-latest-copy, and deliberately retained `analysis_options` states.

It does not catch every section 7 failure mode. Static graph checks cannot establish Bland's numeric-versus-lexicographic `>=` behavior, confirm that today's gateway emits `date_source=`, establish English/Chinese semantic parity, or resolve OPEN-1/OPEN-2. The classification gate catches an unaccounted v87 loss only if the classification input is itself complete; the required v86/v90 negative controls and all 14 redproof mutations test validator sensitivity, not inventory completeness.

- Clean validator. Confirm: draft exits 0 and every assertion 1-34 executes. Refute: any failure, skipped assertion, constant, echo, or no-op.
- v86/v90 negative controls. Confirm: each legacy graph exits nonzero for relevant named invariants. Refute: either legacy graph passes.
- R1-R14 redproof. Confirm: every isolated mutation exits nonzero and trips its named assertion. Refute: any mutation passes or fails only for an unrelated reason.
- Classification gate. Confirm: every field-level v86-v90 difference appears exactly once with zero open/unclassified entries. Refute: any omitted, duplicated, open, or unclassified row.

# Harness coverage

The harness contains the required words and route checks for `friday afternoon` followed by `any later time?`, but it does not prove the actual incident fix. `expect_slot_floor: '03:00 PM'` proves only that displayed times are not before 3 PM. It neither compares the second offer with the first offer nor proves that displayed slots came from the gateway response. A repeated 3:00/3:15 offer, or invented later times, could pass. The third ask deliberately proves honesty rather than genuinely latest availability, matching section 7's admitted residual limitation.

The section 6 two-run appointment-gate measurement is explicitly included before Phase 2 and has the right variable-level evidence: one existing appointment must defer with `appt_count >= 1`; after removal, a fresh thread must reach `n_ask` with `appt_count == 0`.

- Pre-build P-A/P-B/P-C probes. Confirm: proved request shape returns count, `late` returns only post-3 PM slots with a smaller count than `none`, and an empty band returns count 0 with two padded entries. Refute: any observation differs or is unrecorded.
- Appointment-gate run 1. Confirm: exactly one seeded appointment yields `e_defer`, `appt_count >= 1`, and no `n_ask`. Refute: any other route or missing payload evidence.
- Appointment-gate run 2. Confirm: after removal and in a fresh thread, `n_ask` is reached with `appt_count == 0`. Refute: defer, stale/nonzero count, missing `n_ask`, or missing payload evidence.
- Phase 1 base suite. Confirm: all 33 scenarios pass with the zero-appointment precondition asserted before each. Refute: any failure or post-run waiver.
- Eight added scenarios. Confirm: all eight pass their node/text/floor checks. Refute: any failed assertion, while noting that a green incident scenario is insufficient without the missing relational and inventory checks below.
- Incident-fix proof. Confirm: the second response offers gateway-returned slots strictly later than the first response's latest slot and never denies a later returned slot. Refute: repeat/non-advancing slot, invented slot, denial despite later inventory, or no later inventory in the fixture.
- Gateway-authority log check. Confirm: Phase 1 produces attributable `date_source=` lines. Refute: lines are absent or cannot be tied to the run.
- Manual transcript check. Confirm: at least one passing patient-visible transcript is read and agrees with structured evidence. Refute: only the summary is inspected or visible behavior contradicts evidence.
- Phase 2. Confirm: both ordered scenarios pass and exactly one real appointment is written. Refute: zero/multiple writes or either scenario fails.

# Cheapest-first ordering

1. Run P-A/P-B/P-C before editing. Cut: no, because they uniquely test deployed gateway contract semantics.
2. Run classification completeness and the clean validator. Cut: no; these are the cheapest whole-graph checks.
3. Run v86/v90 negative controls. Cut: no; they uniquely expose a broadly vacuous validator.
4. Run R1-R14. Cut: no individual mutation without losing direct sensitivity evidence for its named invariant.
5. Run the five-minute multi-digit Bland comparison probe. Cut from the v91 flip gate: yes, because section 7 assigns it to the proposed v92 design; do not cut before designing v92 or claiming comparison semantics are known.
6. Mint unattached and run the two-run appointment gate. Cut: no; it is the only direct proof of section 6's sharpest risk.
7. Run Phase 1 with the strengthened incident assertions. Cut: no.
8. Inspect `date_source=` logs. Cut: no; harness output cannot prove which authority path executed.
9. Read one passing transcript. Cut: no; this uniquely catches patient-visible semantic/copy defects outside structured assertions.
10. Run Phase 2. Cut: no for the spec's complete flip gate; it proves the real write/re-entry path, not the availability incident alone.

# Missing checks

1. Relational later-slot check: record the first offer's latest datetime and require every second-turn offered datetime to be strictly later on the requested day. This catches repeated or non-advancing offers that the fixed floor misses.
2. Returned-inventory reconciliation: retain the filtered gateway response, require at least one genuinely later real slot to exist, require displayed slots to be members of that response, and fail on denial while such a slot exists. This catches invented slots and vacuous no-denial passes.
3. Bilingual semantic check, if parity is a release requirement: compare the inherited Chinese greeting's claims with the English greeting. Nothing else catches this named residual copy mismatch; the spec currently documents rather than gates it.

# recommendation

**REVISE the proof plan before flip.** Keep the validator, both legacy negative controls, all 14 mutations, both appointment-gate runs, Phase 1, log inspection, transcript review, and Phase 2. Add relational later-than and returned-inventory assertions to the incident scenario. The current harness proves “at or after 3 PM and no forbidden denial phrase,” not “genuinely later real slots surfaced and existing availability was never denied.”

# proof_slots

- Validator: strong static coverage of section 6; incomplete by design for runtime and copy risks in section 7.
- Incident conversation: partial until relational and inventory-membership evidence is added.
- Appointment gate: complete on paper; requires both opposite-outcome runs with `variables.appt_count` evidence.
- Runtime authority: covered only when the gateway log observation is captured.
- Booking path: covered by the two ordered Phase 2 scenarios and exactly-one-write measurement.
- Overall proof-plan verdict: revise before flip.

```json CITATIONS
[
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"No assertion may be satisfied by `true`, `exit 0` or an echo."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"Hardcoded indices"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"The clean draft must pass."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"All fourteen mutations must be observed failing with their text captured;"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"`expect_slot_floor` is already implemented in `pathway_harness.run_scenario`"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"Seed the synthetic test subject with exactly one upcoming appointment"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"Two runs, one variable, opposite outcomes."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"Assert `appt_count` from the"},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"A third \"later\" ask still does not surface the genuinely latest slot."},
  {"file":"/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/SPEC-v91.md","quote":"`date_source=raw`"}
]
```
