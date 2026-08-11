# LLM Intent Tier

## Design

- Adds `off`, `shadow`, and `authoritative` modes, defaulting to `off`.
- Lazily creates a Bedrock Runtime client with short timeouts and no retries.
- Sends one SMS plus a fixed date-intent contract to Claude Haiku at temperature 0.
- Parses fenced or plain JSON, then validates intent, date bounds, ranges, and ambiguity locally.
- Reuses the latest-user-message selector and logs only intent class, deterministic class, agreement, and source.

## Precedence table

| Mode | Deterministic result | LLM result | Outcome |
|---|---|---|---|
| off | any | not called | Existing behavior |
| shadow | any | any/error | Existing behavior; comparison log only |
| authoritative | present | any/error | Deterministic result wins |
| authoritative | none | date/range/asap/ambiguous | Apply validated LLM result |
| authoritative | none | none/error/invalid | Existing fallback behavior |

## Verify

```text
.........                                                                [100%]
9 passed, 242 warnings in 0.23s
CHECK PASSED: flag-off byte-identical to ORIGINAL (153 phrases, computed live); flag-on zero drift on 120 legacy; 12 new month-day phrases resolve; 8 compound phrases resolve; 13 over-broad/malformed inputs stay None; CVC inert under the tenant guard even with the flag on; source diff is additions only.
shape OK
```

The offline evaluator also exits safely with `SKIPPED` unless `RUN_REAL=1` and a Bedrock client is available.

## Residual risks

- The real corpus exam was intentionally not run because AWS/network access was prohibited.
- Model quality and latency remain unmeasured until the guarded real exam runs with credentials.
- Existing parser tests emit 242 Python date-parsing deprecation warnings; this change does not alter that code.
