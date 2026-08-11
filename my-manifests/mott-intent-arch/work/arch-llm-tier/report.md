## Architecture

The Gateway LLM Tier is the strongest near-term architecture because it fixes interpretation at the point we control, trust with scheduling access, and exercise with the 155-phrase gate. The Bland pathway, Bland-managed Twilio number, A2P and STOP handling, extractVars, routing, and Webhook remain unchanged. After the ECS gateway pulls the committed transcript by callID, it sends minimal recent context to Amazon Bedrock Claude Haiku in the BAA-covered AWS account. Haiku returns strict JSON: `{intent: date|range|ambiguous|asap|none, dates, options}`. Gateway code validates it, reconciles it with the deterministic parser, and applies existing conflict, confirmation, and booking rails. Components: Bland pathway and transcript API; ECS Python gateway; Bedrock Claude Haiku; deterministic referee; EyeCloud over Tailscale; `/sign`. No Lambda, Bland Custom Tools, direct Anthropic API, Twilio webhook replacement, or MCP is required.

## Flow

```text
Patient SMS
  -> Bland-managed Twilio number (A2P + STOP handling)
  -> Bland pathway small model reads text, fills extractVars, routes to Webhook
  -> ECS gateway receives callID + pathway variables
  -> gateway pulls raw transcript from Bland API
       -> if newest message is not committed, retry after 1.5s
  -> gateway selects latest patient turn plus bounded relevant context
  -> Bedrock Claude Haiku interprets intent into strict JSON
       {intent, dates, options}
  -> JSON Schema validation + deterministic parser/referee
       -> conflict/ambiguity: produce bounded two-option clarification
       -> invalid/low-confidence/model failure: deterministic fallback
       -> valid date/range/asap: normalize search constraints
  -> existing ECS EyeCloud adapter over Tailscale
       -> serialized EyeCloud session, approximately 8s/call, <=5 concurrent
  -> gateway pads and returns all pathway slot/clarification variables
  -> Bland response path renders clarification or slot offer
  -> patient confirms
  -> existing confirm gate
  -> ECS `/sign` books in EyeCloud
```

Intent is interpreted after transcript retrieval. Availability and booking facts come only from EyeCloud through deterministic code; Haiku never invents or books a slot.

## Failure Modes

**F1 qualifier drop:** Killed at the gateway decision point. Haiku reads “next week Wednesday” rather than trusting Bland’s bare `wednesday`. Parser disagreement, lost qualifiers, or invalid dates trigger clarification or fallback. The pathway must still reach the Webhook; this tier cannot repair a turn that never invokes it.

**F2 hallucinated offer:** Killed for data-bearing offers when templates use only gateway-padded EyeCloud results. Haiku emits constraints, not prose or availability. Validation rejects extra fields; only EyeCloud slots populate `slot_*`. Bland can still hallucinate at other nodes, so this contains rather than globally eliminates the class.

**F4 ambiguity:** Killed by deterministic conflict rails. Haiku may propose bounded options, but code owns the decision. Known 50/50 phrases produce the existing two-option ask; the model cannot guess through the rail.

**F5 soonest-intent:** Fixed once the existing Webhook is reached. Haiku maps “ASAP,” “soonest,” and unseen semantic equivalents to `intent: asap`; code converts that into the existing ASAP search range. However, because the Bland pathway and edges remain unchanged, phrases that stall before the Webhook still survive. The migration must therefore add an observation-backed catch-all route only if testing proves the current Webhook is unreachable for those turns; that would be a later pathway change, outside the promised unchanged baseline.

**F6 finesse dilution:** Mostly killed after Webhook entry. Gateway `options` and rails replace generic day requests with precise asks or ASAP search. Dilution can occur before the Webhook or if Bland paraphrases poorly; templates should render bounded choices verbatim.

## Migration

1. Define the versioned schema, prompt, context rule, timeout, and reconciliation matrix. Add all 155 phrases plus staleness, negation, history, and address fixtures.
2. Add a Bedrock adapter in ECS behind `INTENT_TIER_MODE=off|shadow|authoritative`, with strict parsing and short timeouts.
3. Run `shadow`: today’s result remains authoritative while Haiku output, parser output, disagreements, latency, and redacted reason codes are compared. Do not add raw patient-text logs.
4. Promote only validated intent classes incrementally: `asap`, then ambiguity/range, then date. The parser and safety rails remain active for every class.
5. Run the 155-phrase gate through Bland. Require zero unsafe offers/bookings and measure Webhook reachability.
6. Switch to `authoritative` with automatic fallback on Bedrock timeout, schema failure, disagreement classes, or circuit-breaker open.

Rollback is one ECS configuration change to `off`, restoring today’s parser-led behavior without republishing Bland. A prior ECS task definition remains available if code rollback is needed. Bland pathway rollback is unnecessary because it did not change.

## Risks

1. **HIPAA/data boundary:** Patient texts are PHI-adjacent. Mitigation: use Bedrock Claude only in the AWS BAA account, least-privilege IAM, approved region/model access, encryption, minimal bounded context, no direct Anthropic API, and no raw-text model logs or traces. Complete the organization’s HIPAA risk review before authoritative mode.
2. **Double-interpreter disagreement:** Haiku and the parser can disagree confidently. Mitigation: deterministic precedence rules, ask-don’t-guess on material conflict, schema rejection, frozen fixtures, shadow metrics, and a kill switch. Haiku raises semantic coverage; it does not outrank booking safety.
3. **Latency and dependency failure:** Bedrock adds a network inference hop on top of the approximately 8-second EyeCloud call. Mitigation: small Haiku model, tight input, parallelize safe transcript parsing work, enforce a sub-second-to-low-seconds timeout target, circuit-break on errors, and fall back locally. EyeCloud serialization, not Bedrock, likely remains the dominant bottleneck at current burst scale.

## Effort

Estimated build: 4-6 engineer days plus 2-3 shadow days. Day 1 covers schema, reconciliation, and HIPAA/logging review; days 2-3 implement Bedrock, modes, metrics, and fallback; days 4-5 cover fixtures and integration; day 6 covers deployment evidence and runbook. Added parts: one Bedrock invocation, schema/prompt version, reconciliation module, flags, and metrics. No Lambda, Custom Tools service, new number, MCP client, or scheduling network path.

## Scores

- **C1 correctness ceiling: 4/5.** Raw-text semantic interpretation plus deterministic rails can approach full gateway-handled intent coverage, but unchanged pre-Webhook Bland routing prevents an honest 5.
- **C2 kills whack-a-mole: 4/5.** Haiku generalizes new phrasings without parser edits; genuinely new intent classes and pre-Webhook misses still need explicit handling.
- **C3 migration risk/blast radius: 5/5.** It is additive, shadowable, feature-flagged, and rolls back inside ECS without changing the pathway, number, or booking contract.
- **C4 latency: 4/5.** Haiku adds a small hop, while EyeCloud’s approximately 8 seconds remains dominant; timeout fallback bounds patient impact.
- **C5 HIPAA posture: 5/5.** Bedrock stays in the BAA-covered AWS account with data minimization; direct Anthropic and extra vendors are avoided.
- **C6 ops complexity: 4/5.** One managed inference dependency and disagreement metrics are added; 2am failure degrades to the existing deterministic parser rather than stopping booking.
- **C7 testability: 5/5.** The same 155-phrase executable gate can judge final structured intent, clarification behavior, offers, and booking safety in shadow and authoritative modes.
- **C8 vendor lock-in: 4/5.** The strict internal JSON contract isolates Bedrock and permits model replacement, though the surrounding SMS pathway remains Bland-specific.
