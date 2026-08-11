# Design notes

## Template match

The page uses the supplied MyBCAT template as its structural source, including:

- A full-width dark navy hero with the MyBCAT brand line, CSS vector mark, aqua headline accent, and restrained orbital linework.
- A large circular score gauge at the right side of the hero.
- A short `The Read` strip followed by numbered `Your Market`, `Your Competition`, and `Your Opportunity` zones.
- White and light-gray zone rhythm, fine rules, condensed display fallbacks, aqua and teal accents, gold highlights, and one restrained warm warning color.
- Horizontal meters as the primary score language instead of a card dashboard.
- A compact three-part `First 30 Days` strip and a dark internal-review footer.

## Main gauge math

The gauge uses an SVG circle with radius 44. Its circumference is approximately 276.5. The 54 percent foreground arc is 149.3:

`276.5 x 0.54 = 149.31`

The rendered `stroke-dasharray` is `149.3 276.5`. The center label is `54 / 100`, and the adjacent label names it the Client Opportunity Score. The copy explicitly frames the score as public-only directional evidence, not a grade.

## Score color mapping

- Teal: attractive or stronger core signals.
- Aqua: digital and measurement-oriented signals.
- Warm warning: competitive pressure, where a higher number means more pressure.
- Gold: room-to-win caution and the lowest-ranked specialty lane.
- Dark navy and light gray: structure, tracks, rules, and review-state framing.

All nine approved scores appear as current values. The direction exception for Competitive Pressure is explicit, and Room to Win is shown as the exact inverse.

## Density choices

The catchment evidence uses a compact full-width table because the five windows and six measures need direct row comparison. The two observed-growth series sit immediately below it as a paired strip. Competition uses two-column meters and two evidence rails so the route correction and bounded review sample stay visible without creating another card grid. Specialty lanes use ranked rows with score pills, meters, and one short proof threshold each.

The first-30-days area is limited to the three required cards. Each card compresses owner, first proof, cadence or decision, and kill rule into four short lines.

## Remaining visual risk

The main risk is small-text legibility in the catchment table and 30-day strip on low-quality office printers. The layout prioritizes exact one-page fit and keeps the smallest text for caveats and operational metadata. A fresh PDF render should be inspected at actual size for clipping, table readability, and footer separation before human approval.
