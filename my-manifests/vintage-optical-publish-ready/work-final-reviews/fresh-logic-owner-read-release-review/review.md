# Fresh practice-owner and logic review

Verdict: FAIL

The one-page summary and number explainer are unusually clear for a public-only competitive analysis. A smart practice owner can distinguish raw facts, directional bands, derived scores, structural numbers, and missing evidence. The score stack is also substantively cautious. Two minor artifact defects prevent an issue-free release state.

## Check evidence

### plain_language_explanations: PASS

The explainer defines all four number types before presenting results. Its number map tells the owner what 54, 57, 43, 58, 52, 51, 17,565, 17,557, 25.9%, 23.1%, 4.07 minutes, the peer counts, and the 30-day period mean. Each score table states the question answered, direction, component bands, weights, contribution math, rationale, sources, unknowns, and evidence that could move the result.

The one-page summary uses the same plain-language distinctions. It calls city data context, the peer set bounded, specialty lanes research-next, and the Fix Cards measured baselines rather than growth claims.

### logic_reconciled: FAIL

The substantive score logic reconciles correctly:

- Market Demand-Supply 57 describes directional demand support with incomplete supply and catchment proof.
- Internal Competitive Pressure 57 uses higher = more pressure.
- Room to Win 43 is exactly `100 - 57` and uses higher = better.
- Practice Competitiveness 58 evaluates the public face against a bounded peer set.
- Client Opportunity 54 asks about actionable upside and uses the computed market score of 57 as its required input.
- Digital Presence 57 evaluates a different component set.
- Repeated 57, 52, 50, 65, and 35 values are explicitly explained rather than conflated.

However, `scores.json` contains two current-looking Project Room states. `project_room.status` is `inventory_review_required`, while `data_quality.project_room_status` is `EMPTY`. The one-page summary, explainer, evidence, and runlog consistently use `inventory_review_required`. The stale `EMPTY` value is a minor machine-readable contradiction that must be reconciled.

### unknowns_neutral: PASS

The explainer says a neutral unknown 50 is missing-evidence handling, not measured average performance, good performance, bad performance, or zero. Component rationales distinguish wholly missing evidence from neutral mixed public signals. Missing catchment, supply, reputation, access, capacity, referral, conversion, and economics inputs remain neutral or limited instead of being replaced with favorable assumptions.

### no_overclaim: PASS

Morton village facts are repeatedly labeled city context, not 5-, 10-, 15-, 20-, or 30-minute catchment measurements. The routed alternatives are called a bounded set, not a complete office census or population-weighted patient-choice set. Public pages support stated services, hours, and booking paths only. They are not used as proof of utilization, clinical outcomes, conversion, capacity, patient draw, or financial performance.

The specialty scores are labeled RESEARCH NEXT and explicitly rejected as patient forecasts, revenue forecasts, white-space declarations, or expansion recommendations. No hidden revenue, margin, patient-volume, or clinical-performance claim appears.

### score_direction: PASS

Every displayed report score uses higher = better. The sole high-pressure measure is named as an internal Competitive Pressure input and is visibly inverted into Room to Win. The one-page summary, score labels, number map, formulas, and final interpretation all preserve that direction.

### limitations_visible: PASS

The one-page report places city-versus-catchment, incomplete supply, public-page, reputation, access, conversion, capacity, and economics limitations beside the relevant results. The explainer repeats them at the component, score, specialty, route, source, disconfirmer, and overall unknown levels. Confidence C and the internal-only Project Room boundary are prominent.

The population refresh is also explicit and score-neutral. The current official 2025 Morton village estimate is 17,565. The frozen historical 2024-vintage estimate is 17,557. Neither is a measured drive-time catchment population, no manual band changes, and all six core and three specialty scores remain unchanged.

### owner_actionability: PASS

The three Fix Cards are usable measurement instructions:

- F-001 defines lane inquiries, booked evaluations, starts, completions, cohort rules, and three conversion rates.
- F-002 defines mutually exclusive access-gap dispositions, the total-attempt denominator, and a later tested-recovery sensitivity.
- F-003 defines listing accuracy, review velocity, referral booking, and recall booking.

The explainer requires zero, missing, or unfinished denominators to return null or not calculable, never zero. It also names the 30-day tables, owners, counts, definitions, and proof needed. The cards diagnose before prescribing staffing, hours, service expansion, or growth.

### source_dictionary_complete: FAIL

All 24 registered IDs are unique, every ID used by the explainer resolves, and the dictionary gives claim use, confidence or status, URL, and limitation for S01-S17, N00, and R01-R06.

The historical 17,557 lineage is the exception. The explainer correctly says it comes from the frozen official 2024-vintage PEP file and lists that package receipt in the receipt manifest. The source registry has no ID for that file. More importantly, `evidence.md` cites S17 for 17,557 even though S17's registry record and URL support the 2025 file and current 17,565 value. The historical fact is auditable, but its source-ID trail is incomplete.

## Issue classification

No fatal issues.

No material issues.

Two minor issues:

1. Reconcile the stale `EMPTY` Project Room value in `scores.json`.
2. Register and cite the frozen 2024 PEP source for 17,557.

Highest true state: REVIEW_REQUIRED_BEFORE_PROJECT_ROOM_REVIEW

Project Room status: inventory_review_required

External use authorized: no
