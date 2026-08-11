# v60 day_part Repair

## Summary

- Restored the five-token `day_part` vocabulary and the honest outside-hours miss path.
- Merged exact clock-time bands with the restored after-X phrasing family and exact 3pm boundary.
- Extended invariant 3 and red proof coverage so extraction-route drift fails locally.

## The Merged Guidance

> Exactly one of these five words: morning, afternoon, late, outside, none. Use morning if the patient said morning. Morning clock times within opening hours map to morning. Use afternoon if they said afternoon, midday, or lunchtime. Noon to 2:59pm maps to afternoon. Use late if they said after 3, after 4, 3pm or later, late afternoon, late in the day, the latest, or end of day. All of those phrases map to late, and the 3pm boundary is exact. Use outside if they asked for an exact clock time outside normal clinic hours, such as 3am or 11pm. This is a routing token only and is never sent to the scheduler. Use none if they said nothing about what part of the day suits them. Never put a date, a weekday or a clock time in this field. This field must NEVER be left blank.

## Gate Extension

Invariant 3 now checks every `day_part` extraction description for both the `outside` token and an after-3-to-`late` mapping, in addition to verifying outside-route presence and precedence.

## Assumptions

- “Opening hours” remains intentionally symbolic because the graph provides no clinic-hours constant; the required 3am and 11pm examples define the outside behavior.
- Word-presence checks are intentionally narrow, matching the requested structural blind-spot repair rather than attempting semantic parsing.
