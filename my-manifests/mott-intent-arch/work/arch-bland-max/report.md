## Architecture

The strongest Bland-native design is a bounded conversational control plane: Bland handles dialogue and coarse intent classification, while the existing Python ECS gateway remains authoritative for dates, slots, and bookings. Narrow every model decision, prevent generated text from becoming transactional truth, and give the gateway deterministic veto power. This can reach acceptable quality at 30–100 patients/day with minimal migration risk and fast rollback. Its honest ceiling is below universal natural-language understanding: novel paraphrases and multi-turn corrections can still be misrouted before the gateway sees them.

Components:

- Bland pathway with single-purpose nodes, global safety prompt, monitored-conversation extraction bots, explicit response-path edges, knowledge-base nodes, and terminal dispositions.
- Bland offer nodes that may render only gateway-returned slot variables. They never invent dates or times.
- Existing Python ECS gateway over Tailscale to EyeCloud, including raw transcript pull by callID, 1.5-second commit retry, deterministic parser, ambiguity rails, slot search, `/sign`, and booking verification.
- Bland per-number SMS webhook feeding observability, with callID, route, parser outcome, and escalation reason correlated in gateway logs.
- Bland-managed Twilio retains A2P and STOP handling. Bland Custom Tools are excluded because tool selection would remain under the small model. Bedrock, Lambda, direct Anthropic API, and new services are also absent.

## Flow

```text
Patient SMS
  -> Bland-managed Twilio number (A2P + carrier STOP)
  -> Bland pathway global rails
  -> conversation-level extraction bot at the current decision point
       [coarse intent interpreted here: search / clarify / confirm / cancel / human]
  -> narrow response-path edge
  -> Webhook node -> Python ECS gateway
       -> pull raw transcript from Bland API by callID
       -> retry 1.5s if newest patient message is not committed
       -> deterministic raw-text parser applies negation/history/address kill-rules
       -> resolve date, time band, ASAP, ambiguity, and authoritative filters
       -> Tailscale -> EyeCloud search (~8s, serialized session, <=5 concurrent)
  -> gateway returns padded variables plus explicit next_action
  -> Bland response-path routing follows next_action, not free-form model judgment
       -> clarify template, slot-offer template, escalation, or confirm gate
  -> patient confirms
  -> Webhook node -> ECS gateway -> EyeCloud /sign
  -> deterministic booking result -> Bland confirmation or office-number escalation

Side channel: Bland per-number SMS webhook -> correlated observability/disposition logs.
```

Bland performs only the coarse route. The gateway independently interprets authoritative raw text for scheduling facts and may override Bland’s variables. ECS alone pulls slots from EyeCloud; it pulls conversation data from Bland by callID.

## Failure Modes

- **F1 qualifier drop:** Killed for scheduling correctness when every search pulls the latest transcript and the gateway reconstructs “next week Wednesday” rather than trusting `wednesday`. A commit miss after retry returns `retry_or_clarify`, never a degraded search.
- **F2 hallucinated offer:** Killed transactionally by a closed offer renderer. It can state dates and times only from padded gateway slot fields; empty or malformed fields escalate. Hallucination remains possible elsewhere, so non-offer nodes cannot discuss availability.
- **F4 ambiguity:** Killed by the existing deterministic conflict rail. “Next Friday” and “next weekend” produce a gateway-owned two-option clarification payload. Bland renders the exact options and waits; it does not choose.
- **F5 soonest-intent:** Killed with explicit ASAP labels and edges plus a deterministic fallback webhook. The gateway returns `next_action=search_asap` and a range; the frozen gate proves known variants reach search.
- **F6 finesse dilution:** Reduced, not killed. Gateway-returned wording and options feed constrained templates. Novel phrasing may still hit a generic ask before the webhook; that is the quality ceiling.

## Migration

1. Freeze the current pathway, gateway image, 155-phrase results, and route baseline.
2. Add gateway `next_action`, normalized intent, clarification options, and slot-render eligibility. Shadow-log only.
3. Refactor one decision point at a time with narrow labels, ASAP edges, padded inputs, and fallback webhook. Keep the old branch beside it for test callIDs.
4. Make offer and ambiguity nodes closed templates driven by gateway output. Run the 155 frozen phrases plus negative, stale-transcript, empty-slot, and hallucinated-slot tests.
5. Enable SMS webhook observability; alert on transcript lag, unknown route, empty offers, EyeCloud timeout, `/sign` mismatch, and escalation spikes.
6. Publish to test traffic, then a small cohort, then all traffic after measured improvement.

Rollback is a one-minute republish of the frozen pathway. Backward-compatible gateway changes allow CodeBuild/ECS to restore the prior image in roughly ten minutes. No number, Twilio registration, Bedrock, or network cutover occurs.

## Risks

1. **Small-model ceiling:** Novel language may miss the webhook. Mitigate with fewer intents per node, fallback webhooks, unknown-route escalation, and replay expansion. Do not claim 100%.
2. **Transcript timing/vendor coupling:** Mitigate late commits and platform changes with commit verification, bounded retry, fail-closed clarification, versioned publishing, callID telemetry, and frozen rollback.
3. **HIPAA/telemetry:** Patient text crosses Bland and ECS. Keep transcript access inside the authorized path, log normalized outcomes instead of messages, enforce retention/access controls, and confirm Bland/Twilio coverage. AWS’s BAA covers ECS; Bedrock is not used. Direct Anthropic API and Lambda are not introduced.

## Effort

Estimated build: 6–9 engineer days: two for gateway contracts and fail-closed rendering, two to three for pathway refactoring, one for observability, and one to three for replay and rollout. Moving parts remain Bland pathway/extraction/knowledge base, Bland API and SMS webhook, ECS, Tailscale, EyeCloud, CodeBuild, and Bland-managed Twilio. No new runtime, datastore, model endpoint, Lambda, Bedrock, or Custom Tools path.

## Scores

- **C1 correctness ceiling: 3/5.** Deterministic scheduling facts can approach 100%, but coarse intent routing remains bounded by Bland’s unswappable small model.
- **C2 kills the whack-a-mole: 3/5.** Gateway parsing absorbs many new phrasings, yet novel routing language can still require labels, examples, or edges.
- **C3 migration risk/blast radius: 5/5.** It evolves the live pathway and gateway incrementally with versioned rollback and no number or network migration.
- **C4 latency for the patient: 4/5.** It adds no new model hop; EyeCloud’s roughly eight-second serialized call remains the dominant delay.
- **C5 HIPAA posture: 5/5.** It keeps PHI-adjacent processing in the existing Bland/AWS path and avoids a new processor or separate Anthropic BAA.
- **C6 ops complexity: 4/5.** The 2am pages remain pathway routing, transcript lag, ECS health, Tailscale, or EyeCloud, with no new service to operate.
- **C7 testability: 5/5.** The 155-phrase executable gate can assert routes, normalized intent, clarification text, offer provenance, and booking outcomes.
- **C8 vendor lock-in: 2/5.** Pathway logic, extraction behavior, number operations, transcripts, and observability remain heavily coupled to Bland.
