# Final Numeric and Lineage Release Review

Verdict: PASS

No fatal, material, or minor issues

## Independent recomputation

All base components use only the allowed bands 20, 35, 50, 65, and 80. Canonical weights sum to 1.00 within each weighted score. Full precision is preserved until one final nearest-whole-point, half-up rounding step.

| Score | Independent calculation | Result |
|---|---|---:|
| Market Demand-Supply | 0.25(65) + 0.20(50) + 0.15(65) + 0.15(50) + 0.15(65) + 0.10(35) = 56.75 | 57 |
| Competitive Pressure, internal | 0.40(50) + 0.25(65) + 0.20(65) + 0.15(50) = 56.75 | 57 |
| Room to Win | 100 - 57 | 43 |
| Practice Competitiveness | 0.20(50) + 0.20(65) + 0.20(50) + 0.15(65) + 0.15(65) + 0.10(50) = 57.50 | 58 |
| Client Opportunity | 0.20(57) + 0.20(50) + 0.20(50) + 0.15(50) + 0.15(65) + 0.10(50) = 53.65 | 54 |
| Digital Presence | 0.25(50) + 0.20(50) + 0.20(65) + 0.15(65) + 0.10(65) + 0.10(50) = 56.75 | 57 |
| Dry eye / ocular surface | 0.20(65) + 0.15(35) + 0.15(65) + 0.15(50) + 0.15(50) + 0.10(50) + 0.10(35) = 51.50 | 52 |
| Myopia management | 0.20(65) + 0.15(35) + 0.15(65) + 0.15(50) + 0.15(50) + 0.10(50) + 0.10(35) = 51.50 | 52 |
| Specialty contact lenses | 0.20(50) + 0.15(50) + 0.15(65) + 0.15(50) + 0.15(50) + 0.10(50) + 0.10(35) = 50.75 | 51 |

Client Opportunity correctly uses the computed Market Demand-Supply result of 57. Room to Win is the exact high-good inversion of the internal Competitive Pressure result.

## Numeric and source lineage

- S17 and the frozen 2025 Census PEP receipt support the current Morton village population of 17,565.
- S18 and the frozen 2024-vintage Census PEP receipt support the historical 2024 value of 17,557. The later 2025-vintage back-series value of 17,555 is separately explained and does not replace the earlier vintage's lineage.
- S14 and the saved QuickFacts audit extract support 25.9% under age 18 and 23.1% age 65 or older.
- R01 reports 244.3 seconds. Independent conversion gives 244.3 / 60 = 4.071666..., which rounds to 4.07 routed minutes.
- The registry contains 25 unique IDs: S01 through S18, N00, and R01 through R06. Every ID referenced by `scores.json`, the one-page HTML/PDF text, and the explainer HTML/PDF resolves to the registry. The source-linked HTML anchors match the registered URLs.
- The one-page PDF is one Letter page and the explainer PDF is 11 Letter pages. Their SHA-256 hashes match the final runlog receipts.

## Cross-document and safety checks

The one-page and explainer agree on 57 Market Demand-Supply, 57 internal Competitive Pressure, 43 Room to Win, 58 Practice Competitiveness, 54 Client Opportunity, 57 Digital Presence, and specialty scores 52, 52, and 51. They also agree on 17,565, 25.9%, 23.1%, 4.07 routed minutes, Confidence C, three Fix Cards, and the internal-only boundary.

Repeated values are not conflated:

- The three 57 values answer different questions and use different component sets, even though each weighted total is 56.75.
- The two 52 specialty scores share the same band pattern but retain lane-specific evidence and rationale.
- The 30-minute extended catchment is a market-method parameter. The 30-day period is a measurement window.

All eight displayed rate formulas identify their denominators. The explainer applies one explicit rule to every rate: a zero, missing, or not-final denominator produces null / not calculable, never zero. Missing counts also remain null.

Every visible substantive number is either recomputed, tied to a registered source and frozen receipt, or identified as a structural or method number. No unsupported, stale, duplicated, contradictory, or misleading visible value was found.

Highest true state: READY_FOR_PROJECT_ROOM_REVIEW

Project Room status: inventory_review_required

External use authorized: no
