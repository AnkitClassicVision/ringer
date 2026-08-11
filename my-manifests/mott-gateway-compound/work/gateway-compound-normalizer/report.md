# Gateway Compound Normalizer

## Summary

- Added the guarded compound date normalizer after the ordinal fallback.
- Relative or weekday prefixes are stripped only when the remainder contains a month name.
- Verification is blocked by a contradictory checker corpus entry.

## The Diff

```python
    if _DATE_ORDINAL_FALLBACK and TENANT_ID != "cvc":
        _RELATIVE_PREFIX = {"today", "tomorrow", "tmrw", "tmr"}
        _compound_words = t.split()
        if len(_compound_words) >= 3 and (_compound_words[0] in _RELATIVE_PREFIX or _compound_words[0] in _WEEKDAYS):
            remainder = " ".join(_compound_words[1:])
            if any(m in remainder for m in _ORDINAL_MONTHS.split("|")):
                result = resolve_relative_date(remainder)
                if result is not None:
                    return result
```

## Verify

`CHECK FAILED`

The checker requires `tomorrow july 28th` to remain `None` in `legacy` and resolve to `07/28/2026` in `new_compound`, so no single resolver result can pass both assertions.
