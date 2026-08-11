# Goal-loop round 12: wait-stage split

## Intermittent-router evidence

Rounds 9 through 11 measured an intermittent semantic-router abstention at the single `n_goal_response` user-wait node. That node combined about 11 outbound semantic routes with roughly 3,600 characters of opening, miss, offer, and negotiation policy. In the same run, the same patient message, `Tuesday the 18th`, routed correctly once and later failed to route, after which the model fabricated 2020-dated offers. Label changes improved individual cases but did not remove this reliability ceiling.

Production v96 avoids that hot-node shape by separating the pre-offer ask/miss role from the post-offer offer/negotiation role. Round 12 restores that structural property.

## Split design

- `n_goal_ask` is the pre-offer user-wait `Default`. It owns the exact opening copied from the former combined entry path, the when-would-you-like ask, zero-result/error clarification, and the `out_of_hours` response using `{{requested_clock}}`. It has no slot template, so it cannot render an offer. Its prompt is 2,165 characters and it has five outbound edges.
- The broad round-11 none-search enumeration, including the agreement-phrased `3pm works for me` example, moved to `n_goal_ask`. Generic latest and anchor routing also originate there.
- `n_goal_response` is post-offer only. It retains the protected offer template, clock-time-hardened gates, mixed-intent route, offered-date time/latest routes, out-of-hours honesty copy, and decline/timeout routes. The opening and generic latest/anchor routes were removed. Its prompt is 2,517 characters and it has eight outbound edges.
- Round 12 changes round 11's prompt compression by splitting the formerly compressed 3,600-character combined `n_goal_response` policy across two role-specific prompts: the 2,165-character `n_goal_ask` owns opening and miss/re-ask policy, while the 2,517-character `n_goal_response` owns offer and consent policy. The post-offer prompt remains compressed below its 3,900-character budget and retains the exact protected offer templates, out-of-hours branch, and bans on promises, waiting copy, and invented or non-slot clock times; the moved pre-offer prompt contains no slot templates.
- Conversation entry from `n_appt_check` now targets `n_goal_ask`.
- Every availability webhook sends `slot_count == 1` and `slot_count >= 2` to `n_goal_response`. It sends `ok != true`, `slot_count == 0`, and `out_of_hours == true` to `n_goal_ask`. Date-conflict handling remains on the existing date-conflict nodes.
- Both wait nodes carry the frozen five-extractor prefix byte-for-byte plus the existing `goal_anchor` extractor required by anchor search. `frozen-extractors.json` itself is unchanged from round 11.
- Assertion 12 verifies the split node types, extractor pin, prompt/edge budgets, physical absence of slot templates from `n_goal_ask`, enumeration origin, and all availability success/miss destinations. Assertions 1 through 11 remain active.

The date-conflict family, mixed-intent node, gates, verifies, books, branch confirmations, suppression/end nodes, webhook bodies, and unrelated extractors remain generated from their prior sources without round-12 behavioral edits.

## Regeneration and proof

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
python3 check_goalloop_graph.py --draft pathway-goalloop-draft.json
python3 check_goalloop_graph.py --draft fixture-conformant.json
python3 check_goalloop_graph.py --draft /home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workGLD14/gl-round11-fix/pathway-goalloop-draft.json
```

The first command deterministically rewrites the draft and fixtures from local snapshots. The two round-12 drafts pass all twelve assertion groups. The untouched round-11 draft must fail and include `assertion 12` failures because it lacks `n_goal_ask`, exceeds the post-offer edge budget, and routes misses back to the combined response node.
