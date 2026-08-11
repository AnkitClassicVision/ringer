# Fix notes

## Visual defect

The `The Read` strip reserved only `0.53in`. In the first Chrome PDF, the strip was vertically clipped at the hero and zone boundary. Only `READ` and the final fragment `spend.` remained visible.

## Exact CSS changes

- Increased `.read` from `flex: 0 0 0.53in` to `flex: 0 0 0.70in`.
- Changed `.read` alignment from `center` to `flex-start`.
- Changed `.read` padding from `0.07in 0.48in` to `0.21in 0.48in 0.07in`.
- Set `.read .zone-spine` width and flex basis to `0.72in`.
- Added `white-space: nowrap` to `.read-label`.

These changes keep `THE READ` on one line and keep the executive sentence visible and continuous across two readable lines. The existing flex layout reclaims the added strip height from flexible zone whitespace.

## Page and overflow proof

- The updated gauge source validator returned `PASS`.
- The temporary local print proof contained exactly one Letter page at `612 x 792 pt`.
- Bounding-box inspection checked 615 extracted words and found zero text boxes outside the page.
- `pdftotext` contained the full `THE READ` label, the full executive sentence, and both footer statements.
- Page 1 was rasterized and visually inspected. The complete read strip, all three numbered zones, all three Fix Cards, and the footer were visible with no new clipping.
- The installed Google Chrome was invoked locally, but the managed shell blocked it at startup with a sandbox-host permission error. The geometry, text, and raster proof therefore used the installed local print engine. No Chrome PDF pass is claimed.

## Deliberately preserved

The dark template hero, circular 54-point Client Opportunity gauge, palette variables, orbital linework, full five-window table, nine approved scores, all meters, facts, nulls, evidence language, numbered zones, three Fix Cards, compact table and card typography, and exact footer wording were unchanged.
