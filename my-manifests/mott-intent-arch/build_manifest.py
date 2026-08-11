#!/usr/bin/env python3
import json, pathlib

PACKET = r"""CONTEXT PACKET (measured facts, 2026-07-29 — treat as ground truth, do not browse):

SYSTEM TODAY: Bland AI SMS pathway (their small node model reads each patient text, fills
extractVars like preference_from/day_part/time_after, routes edges, fires a Webhook node) ->
our ECS gateway (Python, Tailscale to EyeCloud practice scheduler; ~8s per EyeCloud call;
~5 concurrent requests max, serialized session) -> slots back into pathway variables ->
offer template ("I have {{slot_1_day_name}} {{slot_1_start}} ...") -> confirm gate -> /sign booking.
The gateway also PULLS the raw conversation transcript from Bland's API by callID (with a
1.5s retry because the webhook often fires before Bland commits the newest patient message)
and runs a deterministic free-text date parser that can override the model's extraction.

MEASURED FAILURE MODES (live incidents):
F1 qualifier drop: patient "next week Wednesday" -> model extracts bare "wednesday" (or drops
   the filter it had). Repeated across patients; prompt-tightening reduced but did not kill it.
F2 hallucinated offer: model once invented "Saturday July 31st 10:00 AM" with no data.
   Guarded by prompt now; the class remains possible at any conversational node.
F3 stale variables: absent JSONPaths kept previous values (fixed: gateway pads all fields).
F4 ambiguity: "next Friday" said mid-week = 50/50 human split (fixed deterministically:
   conflict -> two-option clarify ask). "next weekend" same (fixed).
F5 soonest-intent ("ASAP/next available") never routes to search: conversation stalls on
   the ask node because edge labels don't match (open).
F6 finesse dilution: deterministic smarts (two-option asks, asap range) sit BEHIND the small
   model layer; live diags show safe-but-clunky outcomes (generic "give me one day" instead
   of the smart ask).
DEFENSES IN PLACE: 155-phrase frozen executable gate; ask-don't-guess conflict rails;
confirm-before-book gate; weekday names computed by code; office-number escalation;
raw-text authority with negation/history/address kill-rules; time bands via variables.

CONSTRAINTS: HIPAA — patient texts are PHI-adjacent; AWS account has a BAA (Bedrock Claude
in-account is compliant); direct Anthropic API would need its own BAA. The SMS number is a
Bland-managed Twilio number with A2P registration + carrier STOP handling. EyeCloud is only
reachable from the gateway container (Tailscale). Campaign scale ~30-100 patients/day,
reply bursts <=5 concurrent. Bland platform facts: pathways with extractVars + Webhook
nodes + response-path routing; a Custom Tools API (model calls an external URL with an
input_schema mid-conversation; reserved names: input, speak, transfer, wait, finish, press);
per-number SMS webhook config field exists; conversation transcripts fetchable by id;
NO native MCP client support may be assumed. Bland's node model is small and cannot be
swapped. Deploys: gateway via CodeBuild+ECS (~10 min), pathway via versioned publish (~1 min).

EVALUATION CRITERIA (score each 1-5 with one-line justification):
C1 correctness ceiling (can it reach ~100% intent handling), C2 kills the whack-a-mole
(new phrasings need no new code), C3 migration risk/blast radius from today, C4 latency for
the patient, C5 HIPAA posture, C6 ops complexity (what pages someone at 2am), C7 testability
(can our 155-phrase executable gate still judge it), C8 vendor lock-in."""

CRITERIA_CHECK = ("python3 -c \"import pathlib,sys; t=pathlib.Path('report.md').read_text(encoding='utf-8').lower(); "
                  "req=['## architecture','## flow','## failure modes','## migration','## risks','## effort','## scores']; "
                  "missing=[s for s in req if s not in t]; fm=[f for f in ['f1','f2','f4','f5','f6'] if f not in t]; "
                  "problems=missing+[f'failure mode {x} unaddressed' for x in fm]; "
                  "print('CHECK FAILED:',problems) or sys.exit(1) if problems or len(t.split())<400 else print('CHECK PASSED')\"")

def task(key, title, brief):
    return {
        "key": key, "engine": "codex", "task_type": "research", "timeout_s": 2100,
        "expect_files": ["report.md"],
        "verified": f"Complete architecture proposal for {title} covering flow, every named failure mode, migration, risks, effort, and scored criteria.",
        "check": CRITERIA_CHECK,
        "spec": (f"You are a systems architect. Champion ONE architecture as strongly and honestly as possible. "
                 f"BOUNDARY: write only ./report.md in your task directory; no network, no browsing, no MCP, no git.\n\n"
                 f"{PACKET}\n\nYOUR ASSIGNED ARCHITECTURE: {title}.\n{brief}\n\n"
                 "OUTPUT ./report.md with EXACTLY these sections: '## Architecture' (what it is, one paragraph + "
                 "components), '## Flow' (text diagram: patient text -> ... -> booking, including where intent is "
                 "interpreted and where data is pulled), '## Failure Modes' (address F1, F2, F4, F5, F6 each by name: "
                 "how this architecture kills it or why it survives), '## Migration' (ordered steps from today's "
                 "system, what runs in parallel, rollback), '## Risks' (top 3 with mitigations, include HIPAA), "
                 "'## Effort' (build days + moving parts), '## Scores' (C1-C8, 1-5 each, one line why). "
                 "Be concrete: name real components (Bedrock, Lambda, ECS, Bland Custom Tools, Twilio webhooks). "
                 "600-1100 words.")
    }

manifest = {
    "run_name": "mott-intent-architecture",
    "workdir": "/home/ankit114/repos/ringer/my-manifests/mott-intent-arch/work",
    "max_parallel": 4,
    "tasks": [
        task("arch-llm-tier", "GATEWAY LLM TIER (evolve today)",
             "Keep the Bland pathway + webhook exactly as-is. Inside the gateway, after the transcript pull, "
             "a Bedrock Claude Haiku call interprets the patient's latest message(s) into strict JSON "
             "{intent: date|range|ambiguous|asap|none, dates, options}; deterministic code validates and feeds "
             "the existing conflict/clarify/confirm rails; deterministic parser remains fallback and referee. "
             "Champion why the smallest change wins."),
        task("arch-custom-tools", "BLAND CUSTOM TOOLS (restructure inside Bland)",
             "Replace extractVars-driven search routing with Bland Custom Tools: the conversation model calls "
             "check_availability(raw_request_text) and book_slot(...) as tools against our gateway; the gateway "
             "(deterministic + optional Bedrock tier) interprets the RAW text it receives as a tool argument, "
             "so extraction variables stop being the intent carrier. Assess honestly whether tool-argument "
             "fidelity beats extractVars fidelity given the same small model, and whether tools can drive the "
             "clarify/confirm flows. This is the closest Bland-native analog to giving the agent an MCP server."),
        task("arch-own-loop", "OWN THE CONVERSATION LOOP (middleware brain)",
             "Bland (or Twilio directly) becomes transport only: every inbound SMS hits OUR webhook service; "
             "a Bedrock Claude agent (proper frontier model, not Bland's small node model) runs the whole "
             "conversation with tools (availability, book, escalate) against the gateway; we send replies via "
             "the SMS API. The Bland pathway shrinks to nothing. Address: A2P/STOP compliance handling, "
             "conversation state storage, timeout/72h flows, and how the 155-phrase gate tests the agent. "
             "This trades migration cost for a hard ceiling lift — argue it honestly."),
        task("arch-bland-max", "BLAND-NATIVE MAXIMALIST (no external brains)",
             "Squeeze Bland's own platform: conversation-level extraction bots at decision points (the support "
             "team's monitored-conversation format), knowledge-base nodes, global prompts, per-number SMS "
             "webhooks for observability, dispositions, and the existing deterministic gateway. No Bedrock, "
             "no new services. Argue the strongest honest case that platform discipline + deterministic "
             "gateway reaches acceptable quality, and state plainly where the ceiling sits."),
    ],
}
out = pathlib.Path("/home/ankit114/repos/ringer/my-manifests/mott-intent-arch/manifest.json")
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")
