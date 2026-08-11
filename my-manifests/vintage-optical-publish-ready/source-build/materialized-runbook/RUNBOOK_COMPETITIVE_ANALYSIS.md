# Competitive Analysis GROW Runbook

This is the loopable operating runbook for the members-only Competitive Analysis, also called the revenue map.

The product question is:

> How hard is it for this practice to win the next patient dollar, and where can it still win despite competition?

Use this runbook only for the GROW lane. The default data mode is `public_only`. The executive deliverable is one page, supported by a separate number-by-number explainer and a reproducible evidence package.

## Operating contract

- A human owns intake and delivery. Agents may collect, transform, score, explain, render, and review.
- Public data is the default. Do not use PHI, patient data, private client exports, cookies, session scraping, login-only sources, or credentials in report artifacts.
- Keep every artifact internal-only until the release gates pass.
- External use requires human Project Room approval.
- The public-only SLA is five business days from complete intake.
- All displayed report scores are higher = better. Competitive Pressure Index remains the internal high-pressure measure and is inverted for the client-facing Room to Win score.
- Produce no more than three GROW Fix Cards.
- Keep white-space opportunity separate from competition pressure.
- Treat owned sister locations as network context, not ordinary competitors, unless the evidence supports another classification.
- Keep mobility and corridor variables in an opportunity layer unless evidence proves that they change base competition pressure.
- Do not change scoring weights or formulas in an engagement. A proposed model change belongs in the rubric decision process, not this runbook.

## Trigger

Start an engagement after one of these events:

- A booking on the competitive-analysis calendar at `meetings.hubspot.com/ankit98/competitive-analysis`.
- A request in the Circle pinned thread, post `34471553`.
- A founder assignment for prospect courtship or a Door 1 pilot.

Ask once for missing GROW intake fields from `INTAKE_FORMS.md`. Do not guess. If the practice is an existing client, stop and have the human owner route the work by relationship state.

## Record of engagement

Create the canonical package at:

```text
reports/<practice-slug>/<YYYY-MM-DD>/
```

The complete package must contain:

```text
intake.md
source_inventory.json
missing_evidence.json
data/
data/source_receipts/
scores.json
onepager.html
onepager.pdf
number-explainer.md
number-explainer.html
number-explainer.pdf
runlog.md
```

Store source-labeled data files under `data/`. Use JSON, CSV, or GeoJSON where possible. Preserve raw responses separately from cleaned outputs. At minimum, the package needs the collected local-search observations, reputation observations, catchment polygons, Census intersection output, geocodes, routes, the supply census, the reject set, and scoring inputs when those data exist.

`source_inventory.json` is the source dictionary. Give every source and receipt a stable source ID. Record:

- source ID and source family;
- direct source URL or official API endpoint;
- claim or field supported;
- query parameters and requested geography;
- source vintage and access time;
- collection method and response status;
- package-relative frozen receipt path;
- entity-match basis and confidence;
- limitation and replacement or supersession status.

`runlog.md` records the operator or lane, start and finish times, commands, artifact checks, failures, fallbacks, QA verdicts, reviewer findings, approval state, and `external_actions_taken`. Set `external_actions_taken: none` unless a human records a separately authorized action.

Keep client-confidential packages out of git. Public-only status does not itself authorize a commit, upload, publish, CRM write, or external send.

## Source hierarchy and fallback ladder

Discovery output is not publication evidence.

Use this hierarchy for each claim:

1. Official APIs and first-party pages are preferred authorities.
2. DataForSEO is the structured path for local SERP, Maps, rank-grid, and platform review facts when configured.
3. Google Search/Maps is the direct observation path and public fallback for local search, entity, listing, rank, pack, and review observations.
4. Exa is for discovery, domain-restricted retrieval, and visible-page capture.
5. Perplexity is for cross-source research, contradiction hunting, and cited leads.
6. Direct public directories may close a bounded supply or identity gap when higher-authority sources fail. Record their limits.

Exa or Perplexity output may discover or cross-check a claim. Promote the claim only after it resolves to a direct source URL or official API plus a frozen receipt. The receipt must include the query parameters, geography, source vintage, and access time. A search snippet, generated summary, citation list, or uncaptured browser statement cannot support publication.

For every attempted source, save the successful response or a gap receipt. A gap receipt records the exact request shape without secrets, time, response status, failure class, named fallback, and outcome. Do not write credentials, cookies, authorization headers, or private response content into receipts.

### DataForSEO preflight

Run the DataForSEO preflight before any paid request or collection:

1. Confirm the intended endpoint and required fields.
2. Check that authentication is configured without exposing credentials.
3. Check endpoint availability, quota, expected cost, requested geography, language, device, and result depth.
4. Define the cost stop and named fallback before sending a request.
5. Record the preflight result in `runlog.md` and `source_inventory.json`.

If DataForSEO is not configured, authentication or credentials are unavailable, quota is insufficient, an HTTP block occurs, the result is empty, or the cost stop is reached, create a gap receipt and activate the named fallback. Use Google Search/Maps direct observation first for public local facts. Use Exa for domain-restricted discovery or visible-page capture. Use Perplexity for contradiction review and cited leads. Resolve any promoted fact to the underlying direct source.

Never claim a paid local result, export, or rank grid ran when it did not. A dated SERP sample is not a rank grid.

## Gap register and null handling

`missing_evidence.json` is the live gap register. Create it at intake and update it after every failed source, fallback, transform, scoring gate, or review.

Every unresolved field records:

```text
field
decision_impact
attempted_sources
exact_failure
fallback_tried
owner
status
upgrade_evidence
```

Use a stable gap ID and one of these statuses: `open`, `fallback_in_progress`, `partially_resolved`, `resolved`, or `accepted_limitation`. A resolved item keeps its history and points to the source ID and receipt that closed it.

Unknown is not zero and is not proof of average performance.

Missing raw values, denominators, observations, and canonical computed fields stay null. Do not convert an empty response to zero. Do not describe a null as average, normal, no competition, no demand, or no problem.

Neutral scoring is allowed only when the governing formula explicitly defines a neutral missing-evidence input. Record the source input as null, record the formula-defined neutral value separately, name its score effect, and label the limitation in `scores.json`, the one-pager, and the explainer. Never invent a neutral value to make a formula run.

If a denominator is zero, missing, or not final, the rate is null and `not_calculable`. It is not zero.

## Steps

### 1. Intake and setup, human owned

The human owner supplies practice name, locations, website, owner intent (`grow`, `hold`, or `tighten`), and data mode. Confirm that the request is GROW, public-only by default, and has no patient or private client data.

Create the canonical package. Save `intake.md`, initialize `source_inventory.json` and `missing_evidence.json`, assign the five-business-day due date, and mark every output `internal_only`.

Run the DataForSEO preflight before collection. Record the planned stable query set, source fallbacks, catchment service, and cost stops.

Machine check: required intake fields are nonempty, required directories and registers exist, and no prohibited data mode is active.

### 2. Fetch and freeze public evidence, agent owned

Collect first-party identity, location, hours, services, booking paths, and access claims for the subject and candidate peers. Fetch official Census, ACS, TIGER, CDC PLACES, NPPES, and other public authority records needed by the model.

For every promoted field:

1. Assign a source ID.
2. Resolve it to a direct URL or official API.
3. Freeze the exact response in `data/source_receipts/`.
4. Record query parameters, geography, vintage, access time, entity match, and limitation.
5. Open a gap when the preferred source fails, then run the named fallback.

Machine check: every promoted fact has a source ID that resolves to one inventory row and one existing frozen receipt.

### 3. Capture local SEO, reputation, and citation facts, agent owned

Define a stable query set before observation. Keep the same query wording across the subject and peers. For each local SEO observation, record:

- query or keyword;
- coordinates, latitude and longitude, or declared locality;
- search radius or grid point when applicable;
- device and language;
- observation time and timezone;
- organic rank, local-pack position, or Maps position;
- result URL and matched entity;
- URL/entity match basis and confidence;
- platform, source ID, and receipt.

A rank grid must include the coordinates or other explicit geography for every grid point, the stable query set, and timestamped access time. A direct Google Search/Maps sample remains a dated sample when no grid ran.

Keep review observations platform-specific. For each platform, record rating, count, review recency, review velocity when supportable, owner-response behavior, and aggregator composition. Record whether the displayed count is first-party to that platform, imported, syndicated, or unknown.

Do not average ratings or sum cross-platform review counts without an explicit dedupe method. If no defensible cross-platform dedupe method exists, keep the platform values separate.

Check the practice and peers for current and legacy address, name, phone, and citation consistency. Preserve legacy citations as observations. Do not silently overwrite them with the current address.

Machine check: every rank or review fact includes platform, query or entity, geography, observation time, source ID, and receipt; platform-specific review records remain separate.

### 4. Build complete market catchments, agent owned

Geocode the subject with an entity-matched source. Use Valhalla or an equivalent isochrone service to create polygon GeoJSON for the 5, 10, 15, 20, and 30-minute windows. Save each requested and returned contour in `data/`. If a service contour limit prevents one request, split the requests and record the provider limit. Do not omit a window silently.

Validate every polygon. Record routing provider, profile, coordinates, request parameters, response time, and known limitations.

Intersect the isochrone GeoJSON with Census ACS and TIGER block-group geometry. Store the intersection method, source vintage, allocation rule, coordinate reference system, partial-block treatment, and results for population, households, age bands, and every other modeled field.

Keep city, ZIP, and county facts as separate context fields. A city value is not and cannot substitute for a drive-time catchment value. Do not copy city context into a catchment field.

Use OSRM or an equivalent routing engine for point routes between the subject and matched entities. Point routes do not replace isochrones. Record that public route results may omit live traffic, time-of-day congestion, turn restrictions, or willingness to travel.

Use CDC PLACES and other geographic demand proxies only at their supported geography and vintage. Document any interpolation. A proxy cannot become a patient-volume claim.

Machine check: five valid polygon receipts exist, one for each fixed window, and every catchment value traces to a polygon, a block-group intersection, and a Census/ACS/TIGER source ID. Otherwise the affected value remains null and a gap is open.

### 5. Build the cleaned supply census and competitor tiers, agent owned

Build candidate supply from DataForSEO or direct Google observations, first-party sites, NPPES, and direct directories where needed. NPPES records are not office counts.

Geocode, classify, and deduplicate these entity types before counting:

- provider individuals;
- provider organizations;
- office locations;
- independent optometry offices;
- multi-location optometry group locations;
- retail optical with OD services;
- optical-only stores;
- ophthalmology locations;
- owned sister locations.

Use name, normalized address, suite, phone, domain, provider-to-practice relationships, taxonomy, and first-party location evidence to make merge decisions. Keep match basis and confidence. Do not merge low-confidence rows silently.

Preserve the raw candidate set, accepted census, merge map, duplicate groups, rejects, stale addresses, legacy addresses, and out-of-market addresses. Give each exclusion a reason. A bounded peer set is not a complete supply census.

After the census is complete, assign Tier 1 direct peers and Tier 2 substitutes under `RUBRIC.md`. Keep Tier 3 hidden by default. Treat owned sister locations as network context unless a documented exception applies.

Machine check: office and provider counts derive only from accepted, geocoded, classified, deduplicated rows; every rejected or stale row remains auditable.

### 6. Calculate market fields and apply the VDU gate, agent owned

For every fixed window, calculate or leave null the required population, households, age bands, Vision Demand Units, eye-care offices, OD/provider count, retail chain count, ophthalmology count, population per office, and VDU per office.

The canonical full VDU formula remains the formula in `CALCULATIONS.md`:

```text
Vision Demand Units =
  population
+ 0.35 * children_under_18
+ 0.30 * population_40_to_64
+ 0.60 * population_65_plus
+ 0.40 * diabetes_prevalence_indexed_population
+ 0.20 * commercial_pay_indexed_population
```

Full VDU is not calculated unless every required term is sourced.

Every required term needs source ID, vintage, geography, units, derivation, and receipt. A three-term or other reduced model is a `partial diagnostic`. It must list every omitted term, remain outside the canonical full-VDU field, and cannot be used or described as full VDU.

Machine check: the canonical VDU field is populated only when all six required terms pass lineage checks; otherwise it is null. Any reduced result is stored only as a labeled partial diagnostic.

### 7. Score and select no more than three Fix Cards, agent owned

Apply the weights, formulas, bands, confidence rules, peer rules, and rounding rules from `RUBRIC.md` and `CALCULATIONS.md` without modification.

The scoring contract is:

- Market Demand-Supply Score: 0 to 100, higher = a more attractive market.
- Competitive Pressure Index: 0 to 100, higher = more pressure and internal diagnostic direction.
- Room to Win: 0 to 100, higher = better client-facing room.
- Practice Competitiveness Score: 0 to 100, higher = stronger than the peer set.
- Client Opportunity Score: 0 to 100, higher = more actionable owner upside.
- Specialty Opportunity Scores: 0 to 100, higher = stronger lane.
- Confidence Grade: A is strongest; public-only evidence normally limits confidence.

Room to Win = 100 - Competitive Pressure Index

Do not use the high-pressure Competitive Pressure Index as a client-facing high-good score. Record all inputs, nulls, formula-defined neutral handling, full-precision contributions, rounding, source IDs, confidence, and limitations in `scores.json`.

Run the website and positioning review against the evidence packet. Use `FIX_IT_PLAYBOOK` in GROW mode to select a maximum of three "do now" Fix Cards. Each card needs an owner, action, baseline, numerator and denominator where applicable, measurement window, proof field, decision rule, dependency, and linked evidence. Do not forecast patients or revenue from unmeasured gaps.

Machine check: JSON parses, required score fields exist, all displayed scores have direction cues, weights sum correctly, formulas recompute, and the Fix Card count is at most three.

### 8. Build the number-by-number explainer, agent owned

Create `number-explainer.md`, render `number-explainer.html`, and print `number-explainer.pdf`.

The explainer covers every substantive visible number in `scores.json`, `onepager.html`, and `onepager.pdf`. For each number, include:

- source ID and direct source;
- observation date or source vintage;
- units and geographic scope;
- derivation or formula with full-precision inputs;
- directionality;
- plain-language interpretation;
- why the number appears;
- confidence;
- limitations;
- unknown handling;
- cross-document consistency status.

Also include:

- a number map;
- repeated values and why they repeat;
- structural tokens such as section numbers, tier labels, Fix Card IDs, years, addresses, scale denominators, and measurement-window parameters;
- full score recomputation;
- disconfirmers;
- a source dictionary;
- a receipt manifest with package-relative paths;
- a clear `What we do not know` section;
- the distinction between raw facts, directional bands, derived scores, and structural numbers.

Recompute the client-facing inversion in the explainer:

Room to Win = 100 - Competitive Pressure Index

Machine check: 100% of substantive visible numbers map to explainer entries, zero substantive numbers are unexplained, source IDs resolve, formulas reproduce the displayed values, and repeated values reconcile.

### 9. Render the one-page executive deliverable, agent owned

Render `onepager.html` from the approved client one-pager template, then print `onepager.pdf` with the documented headless Chromium or Playwright command.

The one-pager must:

- fit on one page;
- put The Read first;
- show higher = better direction cues for every displayed score;
- show no more than three Fix Cards;
- separate pressure from white-space opportunity;
- show confidence and limitations;
- keep internal-only and Project Room labels visible until human approval;
- contain no internal filesystem paths or receipt paths.

Delete or replace stale render outputs inside the engagement package before final rendering. Do not mistake an older PDF for the current HTML.

Machine check: the HTML and PDF exist, have current modification times after the source inputs, and the PDF has exactly one page.

### 10. Release review and human delivery gate

Run the complete QA gates below. Use fresh-context, report-only reviewers for:

1. numeric lineage and formula recomputation;
2. logic, score direction, limitations, and disconfirmers;
3. technical package integrity, source resolution, rendering, and path leakage.

Reviewers cite the artifact and issue. They do not edit, approve, deliver, publish, commit, push, merge, or deploy.

Keep all artifacts labeled internal-only until every machine gate passes and the human Project Room owner approves the exact package. External use requires human Project Room approval.

After approval, the human delivery owner may follow the separately authorized delivery process. This runbook does not authorize email, HubSpot writes, uploads, publishing, or any other external action.

## QA gates

Record each check, command or method, result, reviewer, time, and evidence in `runlog.md`. Every gate must pass:

- Intake is complete, GROW scope is confirmed, and the five-business-day SLA is recorded.
- The canonical package contains every required file and no stale duplicate render.
- `source_inventory.json`, `missing_evidence.json`, and `scores.json` parse as JSON.
- Every promoted fact resolves from source ID to a direct URL or official API and a frozen receipt.
- Source receipts record query parameters, geography, source vintage, access time, response status, and limitation.
- Current-vintage checks pass or the older vintage is explicitly historical and limitation-labeled.
- All report links validate without authentication, redirects to unrelated entities, or dead targets.
- Catchment polygons exist and validate for 5, 10, 15, 20, and 30-minute windows.
- Catchment values reconcile to Census ACS/TIGER block-group intersections; city, ZIP, and county context remains separate.
- Supply counts reconcile to accepted, geocoded, classified, and deduplicated entities; rejects and stale addresses remain preserved.
- Full VDU is present only when all required terms are sourced; reduced diagnostics cannot occupy the canonical full-VDU field.
- Score weights, contributions, full-precision totals, and rounding recompute.
- The release recomputation uses exactly: Room to Win = 100 - Competitive Pressure Index
- Higher-good direction cues are present on every displayed report score.
- The number explainer has 100% substantive-number lineage and zero unexplained substantive numbers.
- Every explainer source ID resolves to the source dictionary and receipt manifest.
- Repeated values, structural tokens, nulls, formula-defined neutral handling, and `What we do not know` reconcile across artifacts.
- One-pager and explainer scores, facts, labels, source vintages, confidence, and limitations are consistent.
- No more than three GROW Fix Cards appear.
- The one-page PDF has exactly one page and the explainer PDF has the expected page count.
- Page geometry, margins, fonts, links, headers, footers, and pagination pass.
- A clipping and overflow scan finds no cut-off, hidden, overlapping, or off-page content.
- Visual QA checks every page of both PDFs at readable resolution.
- Stale-render cleanup is confirmed by render times and content hashes or equivalent checks.
- No internal filesystem path, credential, cookie, PHI, patient data, private export, raw internal ID, or login-only source appears.
- Tier 3 material is absent from the client artifact.
- Fresh-context numeric, logic, and technical reviews have no unresolved release-blocking findings.
- The Read is present and reconcilable by a non-analyst.
- Sample or illustrative labeling is removed only when the displayed evidence is real and fully traced.
- Internal-only and Project Room labels remain until approval.
- `external_actions_taken` remains `none` during agent execution.
- External use requires human Project Room approval.

If any gate fails, reopen the owning step, update the gap register and runlog, rebuild downstream artifacts, and rerun all affected checks. Do not approve only the corrected page or field in isolation.

## Loop

For a quarterly re-score:

1. Create a new dated canonical package. Do not overwrite the prior engagement.
2. Reuse the prior stable query set and source IDs where the same authority still applies.
3. Refresh source vintages, access times, receipts, catchments, supply census, scores, explainer, and renders.
4. Show deltas only when the prior and current fields use comparable definitions, geography, source, and method.
5. Keep noncomparable prior values visible as historical context and explain the break.
6. Use Fix Card proof fields as the human follow-up agenda.

If owner intent changes to exit, stop and hand off to `RUNBOOK_EXIT_VALUATION.md`. If operating help is needed, the human owner may start the separately governed Door 1 conversation.

## Automation path

Implement the agent work as checked Ringer lanes in this order:

```text
1. intake/preflight
2. fetch
3. transform/dedupe
4. source audit and contradiction review
5. catchment build
6. scoring
7. explainer build
8. render
9. fresh-context release review
```

Each Ringer lane has a machine-verifiable output or check:

| Lane | Required artifact or check |
|---|---|
| intake/preflight | `intake.md`, initialized registers, DataForSEO preflight result, and required-field check |
| fetch | raw receipts plus one-to-one source inventory resolution |
| transform/dedupe | cleaned data files, entity merge map, preserved reject set, and row-count reconciliation |
| source audit and contradiction review | zero orphan source IDs and a contradiction log with resolved or open status |
| catchment build | valid GeoJSON for all five windows plus block-group intersection checks |
| scoring | schema-valid `scores.json`, weight totals, formula recomputation, null gate, and exact Room to Win inversion |
| explainer build | Markdown, HTML, and PDF plus 100% substantive-number lineage |
| render | current one-page PDF, explainer PDF, page-count check, and clipping/overflow scan |
| fresh-context release review | numeric, logic, and technical verdicts with zero unresolved release blockers |

On lane failure, write the exact failure and fallback to the gap register, return to the owning lane, and rerun every dependent lane. A lane cannot convert an unknown to zero or silently retain a stale downstream artifact.

No Ringer lane may autonomously deliver, email, write HubSpot, publish, commit, push, merge, or deploy. Final delivery remains human owned after Project Room approval.
