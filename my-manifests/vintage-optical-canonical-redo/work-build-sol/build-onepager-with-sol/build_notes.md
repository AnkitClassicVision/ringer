# Vintage Optical one-pager build notes

## Build ownership

Implementation owner: GPT-5.6 Sol. This worker authored `onepager.html` and this note only.

## Source template

The page starts from the specified visual and print contract in:

`/mnt/d_drive/repos/optometry-competition-analyzer-rubric/client-onepager/sample-onepager-b.html`

It preserves the single Letter page, MyBCAT editorial palette and typography, The Read, the numbered Your Market / Your Competition / Your Opportunity story, First 30 Days, and CTA flow. The logo remains the required relative reference: `assets/mybcat-logo.png`.

## Content boundary

The invalid prior Vintage HTML was excluded as a content and score source. No prior headline number, continuous subscore, unsupported forecast, acquisition material, exit material, or Tier 3 content was reused. Visible claims were rebuilt from the verified evidence pack, canonical `scores.json`, and `scoring_notes.md`.

The page is labeled INTERNAL-ONLY and UNROOMED / NOT FOR EXTERNAL USE. It does not claim external-use readiness.

## Visible high-good scores

- Client Opportunity: 54 / 100, higher = better
- Practice Competitiveness: 58 / 100, higher = better
- Digital Presence: 57 / 100, higher = better
- Room to Win: 43 / 100, higher = better, rendered in warning colors
- Market Demand-Supply: 57 / 100, higher = better
- Dry eye / ocular surface Specialty Opportunity: 52 / 100, higher = better
- Myopia management Specialty Opportunity: 52 / 100, higher = better
- Specialty contact lenses Specialty Opportunity: 51 / 100, higher = better
- Confidence: C

The raw Competitive Pressure Index is not displayed.

## Visible Fix Cards

Exactly three elements contain `data-fix-card`:

1. F-001, establish a lane-tagged specialty conversion baseline.
2. F-002, run a 30-day access diagnostic.
3. F-003, reconcile listings and establish review, referral, and recall baselines.

Each card visibly includes the action, owner, plug-in math, proof condition, and confidence. The page states that all volume, conversion, capacity, collection, and economics inputs are unknown until measured. It contains no dollar forecast.

## Print and action receipt

- Print contract: `@page { size: Letter; margin: 0; }`
- Page dimensions: 8.5in by 11in
- Rendering target: headless Google Chrome with print backgrounds preserved
- Structural HTML validator: passed with 19 visible evidence IDs, 21 unique clickable links, four required high-good score checks, and exactly three Fix Cards
- Local fallback PDF proof: one Letter page at 612 by 792 points, 21 unique clickable links, and no out-of-bounds text spans
- Visual fallback review: no page-edge clipping or missing content observed in the rendered page image
- Chrome execution gate: blocked in this worker sandbox before page load by denied crash-reporter and sandbox-host socket operations; the installed Chrome 150 and Chrome-for-Testing 149 binaries both reproduced the environment failure on a blank page
- Subsequent assembly receipt: Ringer run `vintage-optical-canonical-grow-20260730T022324Z-p1444935` rendered the verified HTML successfully with Chrome 150 outside the restricted build worker, producing one Letter page. The canonical `runlog.md` carries the final render and review receipts.
- Source URLs: registered `sources.json` URLs plus the optional MyBCAT booking CTA
- External actions: none
- Forms submitted: none
- Contacts, sends, commits, pushes, publications, and deployments: none
