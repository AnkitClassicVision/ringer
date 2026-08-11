# Round 6: direct webhook execution boundary

## Convention class

In Bland chat mode, the current user-wait `Default` node owns extraction and routes directly to the required `Webhook`. Bland chat mode does not auto-advance through a silent `Default` node mid-turn. The round-5 `n_goal_update` hop violated that platform convention, so its extractors and its edge to `n_goal_search` never ran.

## Changes

- Removed `n_goal_update` and every edge to or from it.
- Rewired `n_goal_response`, `n_date_conflict`, `n_date_conflict_retry`, `n_gate_1`, `n_gate_2`, `n_book_1`, and `n_book_2` directly to `n_goal_search` on their existing scheduling conditions.
- Put all nine `n_goal_search` request extractors on each user-wait source: `user_verbatim`, `preference_from`, `preference_to`, `day_part`, `time_after`, `time_from`, `time_to`, `goal_anchor`, and `goal_relation`.
- Preserved persistent-goal behavior by re-extracting the four goal fields every turn and explicitly carrying prior values forward with `retain` when the turn does not change them.
- Preserved the round-5 `n_goal_search` data object byte-for-byte, including its real headers, URL, method, body parameterization, response mappings/pathways, and retry/skip settings.
- Added assertion 6 to reject a silent `Default` hop into a slot-producing webhook, incomplete extraction at a user-wait source, and any graph containing `n_goal_update`.

## Regeneration

Run from this directory:

```bash
python3 build_goalloop.py --fixtures
```

This deterministically rewrites `pathway-goalloop-draft.json` and all `fixture-*.json` files.
