# LLM Intent Tier v2 - phrase contract

## Why

- The 48-phrase Bedrock exam showed Haiku classified intent, negation, busy context, corrections, and ASAP correctly.
- Haiku still produced off-by-one weekday dates on 10+ cases, matching the date-math failure seen across models.
- The existing deterministic resolver was correct on all 153 phrases, so calendar derivation belongs only in code.

## Contract

The LLM returns only `{"phrase":"..."}`: the patient's operative date words, with limited shorthand expansion and filler removal. It keeps qualifiers and ignores negated, busy, historical, and address-context dates. Empty means no intent. The gateway passes the phrase to `extract_date_from_text` and converts that deterministic result into the existing date, range, ambiguous, or none verdict shape. Existing precedence, modes, logging, and fail-open wiring remain unchanged.

## Verify

`python3 -m pytest -q test_llm_intent.py`

`11 passed in 0.23s`

`CHECK PASSED: flag-off byte-identical to ORIGINAL (153 phrases, computed live); flag-on zero drift on 120 legacy; 12 new month-day phrases resolve; 8 compound phrases resolve; 13 over-broad/malformed inputs stay None; CVC inert under the tenant guard even with the flag on; source diff is additions only.`

`shape OK`
