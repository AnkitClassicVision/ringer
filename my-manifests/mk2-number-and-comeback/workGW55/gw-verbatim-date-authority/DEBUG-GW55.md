# GW55 verbatim date authority

## What changed

At the availability handler's from-resolution seam, the gateway now restores a
day-of-month ordinal found in `user_verbatim` or `user_text` when extraction's
`from` value dropped every explicit day. The restored value is canonicalized as
`the <day><suffix>` and passed through the existing nearest-future ordinal
resolver. This keeps the standing rule that an explicit day beats a weekday.

Lane 52's context-week resolver now also recognizes `that <weekday>` and
`on that <weekday>`. The weekday is read from the verbatim phrase and anchored
to the Monday-Sunday week containing `context_date`. Existing `<weekday> that
week`, same-week behavior, missing-context behavior, and the past-day guard are
unchanged. The ordinal override runs first and suppresses the anaphoric override
when both match.

## Exact trigger regexes

Verbatim ordinal:

```regex
\bthe\s+(?:(?P<numeric>\d{1,2})(?P<suffix>st|nd|rd|th)?|(?P<spelled>first|...|thirty[-\s]first))\b
```

The numeric day must be 1-31 and any supplied suffix must be correct. The
spelled alternation is generated from `_SPELLED_ORDINAL_DAYS`.

Extractor already has an explicit day, so do not override:

```regex
(?:\bthe\s+\d{1,2}(?:st|nd|rd|th)?\b|\b\d{1,2}(?:st|nd|rd|th)\b|\bthe\s+(?:<spelled ordinals>)\b|\b(?:<month names>)\s+\d{1,2}(?:st|nd|rd|th)?\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\b\d{1,2}-\d{1,2}-\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b)
```

That-weekday:

```regex
\b(?:on\s+)?that\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b
```

The existing lane-52 trigger remains:

```regex
\b(that|the same|same)\s+week\b
```

## Known limitations

- The new ordinal-authority trigger intentionally requires `the`; a bare
  cardinal such as `Thursday 27` is outside this fix.
- Spelled ordinals cover the existing lane-53 vocabulary, first through
  thirty-first, with spaces or hyphens for compound forms.
- `that` weekday support is limited to full English weekday names as specified.
- Context anchoring still requires `MM/DD/YYYY` or `YYYY-MM-DD` at the start of
  `context_date`.
- Clock text such as `4:27 pm` cannot match the required `the <ordinal>` shape.
