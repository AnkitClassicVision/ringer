## Architecture

Champion Bland Custom Tools as the least-disruptive architecture that materially raises correctness: keep Bland’s managed SMS number, A2P registration, carrier STOP handling, and conversational shell, but remove `extractVars` as the search-intent authority. The small Bland model calls `check_availability(raw_request_text, call_id)` and, only after explicit confirmation, `book_slot(slot_id, confirmation_text, call_id)`. Both terminate at the existing ECS gateway, the only component with Tailscale access to EyeCloud. The gateway fetches the committed transcript, applies raw-text authority and deterministic rails, then optionally sends minimum necessary text to in-account Bedrock Claude for novel-language interpretation. Code validates Bedrock’s constrained intent before EyeCloud access. Tool responses are structured actions such as `offer_slots`, `clarify_two_options`, or `escalate`. This is not MCP, but it is the closest Bland-native equivalent: the gateway, not pathway variables, becomes the intent and action boundary. Components: Bland SMS pathway and Custom Tools, Bland transcript API, ECS, Bedrock, EyeCloud/Tailscale, and Bland-managed Twilio webhooks. Lambda adds no value on the EyeCloud path because it lacks the gateway’s serialized Tailscale session.

## Flow

```text
Patient SMS
  -> Bland-managed Twilio number (A2P + STOP handling)
  -> Bland conversation node
  -> Custom Tool call: check_availability(raw_request_text, call_id)
  -> ECS gateway
       -> pull transcript from Bland by call_id
          -> retry for newest committed message when needed
       -> choose authoritative current patient text from transcript
       -> deterministic rails/parser
       -> Bedrock Claude only for unresolved novel phrasing
       -> validate constrained intent and clarification state
       -> if ambiguous: structured two-option clarification -> Bland -> patient
       -> if searchable: EyeCloud query over Tailscale (~8s)
  <- structured result with opaque slot IDs and grounded display values
  -> Bland offers only returned slots
  -> patient confirms
  -> Custom Tool call: book_slot(slot_id, confirmation_text, call_id)
  -> ECS re-pulls transcript, verifies explicit confirmation and slot validity
  -> EyeCloud /sign booking
  <- booked or safe failure/escalation
  -> Bland sends grounded receipt or office-number escalation
```

Intent is interpreted from transcript-authoritative raw text, not trusted from the tool argument alone. The argument is a hint; the transcript is the fidelity backstop.

## Failure Modes

**F1 qualifier drop:** Mostly killed. A tool argument can lose “next week” because the same small model creates it; Custom Tools alone do not improve fidelity. The decisive change is re-pulling raw text by `call_id`. “Next week Wednesday” reaches deterministic or Bedrock interpretation intact. If freshness is uncertain, return `wait/retry` or clarify, never broaden.

**F2 hallucinated offer:** Killed at the action boundary. Bland receives structured results with opaque slot IDs and server-computed dates. Booking rejects IDs not issued for that conversation and revalidated against EyeCloud. The model may still invent prose, so response nodes must render returned fields and tests must fail any ungrounded offer.

**F4 ambiguity:** Killed deterministically. The gateway returns `clarify_two_options` with two computed interpretations. Bland asks that bounded question; the transcript supplies follow-up context. No search occurs until resolved.

**F5 soonest-intent:** Killed. “ASAP/next available” no longer depends on an edge label. The gateway classifies it centrally, applies its range, and queries EyeCloud. A pathway fallback calls the tool when search intent is plausible.

**F6 finesse dilution:** Substantially killed, not eliminated. Tool responses select the next action, but Bland can weaken a good ask. Return ready-to-send `speak` text or enumerated fields and test the visible SMS.

## Migration

1. Add versioned `check_availability` and `book_slot` contracts; preserve current webhooks and transcript retry.
2. Implement structured actions, opaque slots, confirmation checks, idempotent booking, and flag-gated Bedrock.
3. Extend the 155-phrase gate to assert calls, raw-text recovery, actions, grounded offers, and confirmation.
4. Clone the pathway and replace one branch. Shadow tools while `extractVars` still serves patients; never shadow-book.
5. Canary a small cohort. Route back on elevated stalls, latency, or grounding failures.
6. Expand by cohort; remove legacy routing only after gate and canary success. Rollback is a one-minute pathway republish; keep gateway compatibility.

## Risks

1. **Tool-call fidelity and compliance:** The small model may omit, alter, or fail to call the tool. Mitigation: transcript-authoritative interpretation, broad pathway fallback to the availability tool, constrained returned wording, and executable call/no-call cases.
2. **Latency and serialized EyeCloud capacity:** Transcript retry plus an ~8s EyeCloud call can make a reply feel slow, and bursts approach the five-request ceiling. Mitigation: use Bland `wait`, deduplicate/idempotently coalesce calls, queue above capacity, cache only safe availability reads briefly, and return a graceful office escalation on timeout.
3. **HIPAA/data boundary:** Patient text is PHI-adjacent. Keep raw text inside Bland, the BAA-covered AWS account, ECS, and in-account Bedrock; do not use direct Anthropic without its own BAA. Minimize Bedrock inputs, redact logs, encrypt transport/storage, restrict IAM, define retention, and confirm Bland’s applicable contractual posture before production.

## Effort

Estimated 8-12 build days plus 3-5 observation days: 3 for tool contracts/state, 2 for booking controls, 1-2 for Bedrock, 1-2 for pathway work, and 1-3 for tests/instrumentation. Moving parts: two Custom Tools, one pathway, ECS/Tailscale/EyeCloud, transcript retry, Bedrock, queue/idempotency storage, and alarms.

## Scores

- **C1 correctness ceiling: 4/5.** Transcript authority plus deterministic and Bedrock tiers can approach comprehensive handling, but Bland still controls tool invocation and patient-facing phrasing.
- **C2 kills the whack-a-mole: 4/5.** Bedrock handles novel language without phrase-specific code while deterministic rails protect known hazards; new safety classes may still need gates.
- **C3 migration risk/blast radius: 4/5.** It preserves the number, pathway shell, gateway, and EyeCloud boundary, with shadowing and one-minute pathway rollback.
- **C4 latency for the patient: 3/5.** Tool dispatch and transcript reconciliation add overhead to the existing ~8s EyeCloud call, though they avoid extra pathway turns.
- **C5 HIPAA posture: 4/5.** AWS Bedrock stays in the BAA-covered account and direct Anthropic is excluded; Bland’s handling still requires contractual confirmation and minimization.
- **C6 ops complexity: 3/5.** Fewer brittle edges, but 2am pages can come from Bland tool failures, transcript lag, ECS, Bedrock, Tailscale, EyeCloud, or queue saturation.
- **C7 testability: 5/5.** The 155-phrase gate can judge calls, actions, exact offers, confirmation, and final SMS behavior with clearer boundaries than extractVars.
- **C8 vendor lock-in: 3/5.** Intent logic becomes portable in the gateway, but tool invocation, SMS identity, pathway behavior, and rollback remain Bland-specific.
