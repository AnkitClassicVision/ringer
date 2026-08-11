## Architecture

Own the conversation loop in AWS and reduce Bland to SMS transport. Every inbound message reaches API Gateway/Lambda, which validates, deduplicates, and queues the turn. An ECS orchestrator loads DynamoDB state, sends the turn and bounded history to Bedrock Claude, and exposes typed tools: `search_availability`, `book_slot`, and `escalate`. They call the existing ECS EyeCloud gateway over Tailscale. The orchestrator validates tool results, renders replies from authoritative data, and sends through Bland's SMS API on the existing Bland-managed Twilio number. Bland retains A2P registration and carrier STOP handling; it no longer interprets intent. The Bland Custom Tools API is deliberately bypassed because Bland's small model would still decide when to call it. DynamoDB stores suppression, offered-slot IDs, confirmation, idempotency keys, and a 72-hour expiry. EventBridge and SQS handle timeouts and retries.

Components:

- Bland-managed Twilio number, inbound SMS webhook, outbound SMS API, A2P registration, and carrier STOP enforcement.
- API Gateway plus Lambda for authenticated ingress, deduplication, STOP/START mirroring, and fast acknowledgement.
- SQS FIFO for per-conversation ordering, retry isolation, and burst control.
- ECS orchestrator using Bedrock Claude for conversation policy and typed tool selection.
- DynamoDB with TTL for state and PHI-minimized CloudWatch logs.
- Existing ECS EyeCloud gateway and Tailscale connection for availability and booking.

## Flow

```text
Patient SMS
  -> Bland-managed Twilio number
     -> carrier/Bland STOP handling
     -> per-number inbound SMS webhook
  -> API Gateway + Lambda
     -> authenticate, deduplicate, mirror suppression status, enqueue
  -> SQS FIFO keyed by conversation/phone token
  -> ECS conversation orchestrator
     -> pull state from DynamoDB
     -> interpret intent with Bedrock Claude
     -> request typed tool call
        -> search_availability / book_slot / escalate
        -> existing ECS gateway
        -> Tailscale
        -> EyeCloud
     <- validated slots or booking result
     -> write state, offered-slot IDs, and confirmation gate to DynamoDB
     -> render reply only from validated tool data
  -> Bland SMS API
  -> Patient confirms a specific offered-slot ID
  -> Bedrock selects book_slot
  -> ECS gateway -> EyeCloud -> booking receipt
  -> final SMS or office-number escalation
```

Bedrock interprets intent from patient text and controlled state. Availability and booking data come only through the gateway. The agent cannot manufacture slots or bypass confirmation.

## Failure Modes

- F1 qualifier drop: Killed as an architectural class. "Next week Wednesday" stays in the complete utterance supplied to Bedrock; there is no lossy `extractVars` handoff. Search requires a resolved date range and evidence span; missing evidence forces clarification.
- F2 hallucinated offer: Controlled, not magically eliminated. Claude can still generate bad prose, so offers are rendered by code from gateway-returned slot IDs, dates, and times. The outbound validator rejects any date/time not present in the current offer set. Booking accepts only a confirmed offered-slot ID.
- F4 ambiguity: Killed by policy enforcement. Configured conflicts such as "next Friday" and "next weekend" require the existing two-option clarification before Claude continues. Deterministic policy owns the gate.
- F5 soonest-intent: Killed. ASAP and "next available" map directly to `search_availability` with a configured forward range; there are no pathway edge labels to miss.
- F6 finesse dilution: Killed. Deterministic clarifications and range logic run before response generation, while the same frontier model sees their structured output and writes the final ask. The small Bland node model is removed from the decision path.

## Migration

1. Build the ingress, SQS ordering, DynamoDB state schema, orchestrator, typed tools, outbound validator, and observability without changing production routing.
2. Replay the frozen 155 phrases plus multi-turn fixtures through Bedrock. Assert intent, clarification, tool arguments, allowed slot IDs, confirmation, and reply class. Repeat trials for variance; require zero unsafe bookings and a defined intent-pass threshold.
3. Add shadow mode beside today's pathway. The current Bland pathway remains authoritative while it copies sanitized turns to the new service; the new service records decisions but sends nothing and cannot book.
4. Canary a test number, then a small production cohort. Keep bookings human-reviewed initially and compare outcomes, latency, escalations, and disagreements.
5. Increase traffic in measured stages, then remove the pathway's extraction and response nodes after the canary meets the gate. Preserve its last published version.
6. Roll back by restoring the last Bland pathway version, quarantining queued turns, and disabling the orchestrator's booking permission.

## Risks

1. HIPAA and PHI exposure. Keep interpretation in BAA-covered AWS using Bedrock; use KMS, short retention, redacted logs, least-privilege IAM, and a documented data-flow review. Direct Anthropic API use requires a separate BAA.
2. Orchestration can page the team at 2am. Alarm on SQS backlog, Bedrock throttling, state errors, send failures, and EyeCloud saturation. Use circuit breakers, bounded retries, a DLQ, per-conversation locks, and office escalation.
3. Transport compliance or duplicates. Bland/Twilio remains authoritative for STOP and A2P. Mirror suppression locally but fail closed; sign webhooks, enforce turn and booking idempotency, and reconcile receipts.

## Effort

Estimate 18-28 engineering days: 6-8 for transport/state, 5-7 for Bedrock orchestration and tools, 3-5 for the test harness, 2-4 for security and operations, and 2-4 for canary/cutover. Moving parts are API Gateway, Lambda, SQS/DLQ, ECS, Bedrock, DynamoDB, EventBridge, CloudWatch, Bland/Twilio, the gateway, Tailscale, and EyeCloud. This is more infrastructure, but failures become observable and testable.

## Scores

- C1 correctness ceiling: 5/5. Frontier reasoning plus deterministic tool and confirmation gates can approach complete intent coverage without trusting generated slot facts.
- C2 kills the whack-a-mole: 5/5. Full-utterance reasoning handles new phrasings semantically; code changes remain for new policy classes, not every wording.
- C3 migration risk/blast radius: 2/5. Transport routing, state, replies, and booking authority move at once, though shadowing, canaries, and instant pathway rollback contain the cutover.
- C4 latency for the patient: 3/5. Bedrock and queueing add seconds around an existing roughly eight-second EyeCloud call; asynchronous acknowledgement and parallel non-EyeCloud work help.
- C5 HIPAA posture: 5/5. PHI-adjacent interpretation stays in the BAA-covered AWS account with Bedrock and private gateway access.
- C6 ops complexity: 2/5. More AWS services and failure boundaries can page someone, even with queues, circuit breakers, alarms, and escalation.
- C7 testability: 5/5. The 155-phrase gate can call the orchestrator directly and assert structured decisions, tool arguments, state transitions, and prohibited outputs.
- C8 vendor lock-in: 3/5. Conversation logic becomes ours, but Bedrock, Bland/Twilio transport, EyeCloud, and Tailscale remain dependencies; typed internal interfaces make Bedrock or transport replacement feasible.
