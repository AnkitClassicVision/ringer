# Gateway Ordinal Fix v2

## Summary

- Adds an opt-in month-anchored ordinal fallback for Mott.
- Preserves legacy-first resolution and keeps CVC behavior unchanged.
- Re-resolves ordinal-free input through the existing date grammar.

## The Diff

```python
_DATE_ORDINAL_FALLBACK = _env_bool("ECP_DATE_ORDINAL_FALLBACK", False)
```

```python
_ORDINAL_MONTHS = (
    "january|february|march|april|may|june|july|august|september|"
    "october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
)


def _ordinal_suffix(day: int) -> str:
    if 11 <= day % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
```

```python
if _DATE_ORDINAL_FALLBACK and TENANT_ID != "cvc":
    m = re.fullmatch(r"(" + _ORDINAL_MONTHS + r") (\d{1,2})(st|nd|rd|th)( \d{4})?", t)
    if m and 1 <= int(m.group(2)) <= 31 and m.group(3) == _ordinal_suffix(int(m.group(2))):
        return resolve_relative_date(f"{m.group(1)} {m.group(2)}{m.group(4) or ''}")
```

## Verify

CHECK PASSED: flag-off byte-identical to ORIGINAL (144 phrases, computed live); flag-on zero drift on 121 legacy; 12 new month-day phrases resolve; 11 over-broad/malformed inputs stay None; CVC inert under the tenant guard even with the flag on; source diff is additions only.

## Additive Proof

A diff against the original shows only insertions and no deletions.
