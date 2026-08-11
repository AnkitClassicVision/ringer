# GW52 anaphoric-week determinism

## Change

`resolve_anaphoric_week(from_text, verbatim_text, context_date_str, today)` is a
pure resolver. When the original utterance contains the anaphoric-week trigger,
it ignores extraction qualifiers and anchors the requested weekday to the
Monday-through-Sunday week containing `context_date`. A request with no named
weekday gets the whole context week, with its start clipped to `today`. A named
day that is already past remains that past day so the availability query follows
the existing honest-empty path instead of jumping weeks.

## Handler seam

`build_argv()` calls `clamp_availability_range()` for every `/availability`
request. `clamp_availability_range()` retains the original `from`,
`user_verbatim`/`user_text`, and `context_date`, calls
`resolve_anaphoric_week()`, then writes the resulting `from`/`to` window before
the existing date normalization and CLI argument construction.

Exact trigger regex:

```text
\b(that|the same|same)\s+week\b
```

It is compiled case-insensitively. A parseable context date and either a full
weekday name in `from_text` or no weekday are also required.

## Known limitations

- Negated anaphors such as “not that week” still trigger; negation is not part
  of this bounded resolver.
- Only full English weekday names are recognized by the override. Abbreviations
  continue through the pre-existing resolver.
- The context parser accepts the gateway's existing leading `MM/DD/YYYY` and
  `YYYY-MM-DD` forms, optionally followed by slot time text.
