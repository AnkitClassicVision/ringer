# Raw-Text Date Authority

## Summary

- Added an opt-in raw-message date authority guarded by `ECP_RAW_TEXT_DATES` and the non-CVC tenant check.
- The latest user message can override model-extracted availability dates; fetch and parse failures preserve the model fallback.
- `callID` is always removed before downstream CLI argument handling.

## Parser Pipeline

1. Normalize text, collapse whitespace, and expand supported texting shorthand token by token.
2. Resolve the last valid explicit English month-and-day match, treating later dates as corrections.
3. Resolve an explicit Chinese month-and-day match before relative language.
4. Try the entire normalized string as a clean date phrase.
5. Scan token windows of sizes 4, 3, 2, then 1 from left to right, excluding digit-only windows.
6. Resolve a valid bare ordinal day to its next calendar occurrence, advancing past short months.
7. Return `None` when no deterministic date is found.

## Verify

`CHECK PASSED: flag-off byte-identical to ORIGINAL (153 phrases, computed live); flag-on zero drift on 120 legacy; 12 new month-day phrases resolve; 8 compound phrases resolve; 13 over-broad/malformed inputs stay None; CVC inert under the tenant guard even with the flag on; source diff is additions only.`

`5 passed, 5 warnings in 0.14s`

## Risks

- The existing yearless `datetime.strptime` path emits a Python 3.15 deprecation warning. It is unchanged because `resolve_relative_date` was required to remain untouched.
- Conversation fetches add up to two sequential two-second attempts when the feature is enabled and both endpoints fail.
