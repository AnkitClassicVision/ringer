# Gateway Ordinal Fix

## Summary

- Added an opt-in `ECP_DATE_ORDINAL_FALLBACK` flag, disabled by default.
- Added a legacy-first ordinal suffix fallback only after all existing date parsing branches fail.
- The fallback strips one English ordinal suffix from a day number and reuses the existing resolver.

## The Diff

```python
_DATE_ORDINAL_FALLBACK = _env_bool("ECP_DATE_ORDINAL_FALLBACK", False)
```

```python
    if _DATE_ORDINAL_FALLBACK:
        stripped = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1", t)
        if stripped != t:
            return resolve_relative_date(stripped)
    return None
```

## Verify

```text
CHECK PASSED: flag-off byte-identical to OLD across 106 phrases (CVC untouched); flag-on zero drift on 96 legacy phrases; 10 new ordinal phrases resolve correctly and were None before; bad/bare/compound stay fail-closed.
```

## Additive Proof

A unified diff against `impl-src/bland_gateway.py` shows exactly two hunks: the added module-level flag and the replacement of the final `return None` in `resolve_relative_date`. No other source bytes changed.
