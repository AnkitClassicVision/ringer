# GW56: verbatim day-part authority

## Change

`enforce_verbatim_daypart_authority(verbatim_text, after, before, time_pref)` is a pure function called by `clamp_availability_range` at the availability handler's existing window seam. It fills only an absent `after`/`before` pair. `build_argv` then uses its unchanged clock normalization and ordinary `--after`/`--before` flags.

Exact detection regex:

```regex
(?<!\bgood\s)\b(morning|afternoon|evening|tonight|night)\b
```

It is compiled case-insensitively. The fixed-width negative lookbehind excludes `good <day-part>` greetings.

## Window mapping

| Verbatim word | Effective after | Effective before |
|---|---:|---:|
| morning | none | 12:00 pm |
| afternoon | 12:00 pm | none |
| evening | 04:00 pm | none |
| tonight | 04:00 pm | none |
| night | 04:00 pm | none |

An existing `after` or `before` is returned unchanged. A `time_pref` containing `anchor` or `latest` also returns the original pair unchanged, so an explicit clock request wins. Date resolution remains independent and runs through the cumulative lane-52/53/55 logic.

## Known limitations

- Only the five specified English day-part words are recognized.
- The greeting guard covers the exact adjacent phrase `good <day-part>` with whitespace; punctuation between the words is not treated as that greeting.
- The first qualifying day-part wins if a message contains multiple conflicting day-parts. Such ambiguity is not newly resolved here.
