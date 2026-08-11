# Ringer model-routing recommendations

Generated from the rebuilt local scoreboard on 2026-07-10 after fixing effective-model attribution and OpenRouter route normalization.

## Operating policy

1. Do not change global engine defaults from a single audition.
2. Catalog changes create candidates, not assignments.
3. Use manifest-scoped routes for every deliberate model choice.
4. Require an executable check for every audition.
5. Promote a model/task-type pair only after at least 3 comparable tasks and a first-try pass rate of at least 0.67.
6. Retries retain the same engine and model so evidence remains attributable.
7. Do not rewrite historical `runs.jsonl` rows. Rows without an explicit recorded model remain `Codex CLI default (unpinned)`.

## Current routing recommendations

### Verification

**Preferred:** `engine: claude-lean`, `model: fable`

Evidence: 3 tasks, 100% first-try, 100% final. This is the strongest model-specific proven lane. Confirm Claude OAuth availability before routing because prior failures included account-state limits.

### Mechanical documentation and data pipelines

**Probation candidate:** `engine: opencode`, `model: openrouter/z-ai/glm-5.2`

Evidence:

- Documentation: 2 tasks, 100% first-try, 100% final.
- Data pipeline: 2 tasks, 100% first-try, 100% final.

Keep contracts mechanical and explicit. One additional comparable first-try pass is required before promotion.

### Code review

**No named model is proven yet.**

- `gpt-5.6-luna`: 8 tasks, 62.5% first-try, 75% final.
- Claude Sonnet through `claude-lean`: 8 tasks, 62.5% first-try, 100% final.
- Historical unpinned Codex: 6 tasks, 100% first-try, but the underlying model identity is not recoverable from the log and must not be used as named-model proof.

Recommendation: continue explicit Luna and Sonnet auditions with deterministic review contracts. Use paired or independent review for load-bearing decisions until one named model clears the evidence floor.

### Research, live-source verification, and synthesis

Historical Codex research evidence is strong at the harness level: 16 tasks, 75% first-try, 93.75% final. Those older rows are now honestly labeled `Codex CLI default (unpinned)` and cannot establish a specific model winner.

Use the manually verified lanes in `docs/MODEL-NOTES.md` prospectively with explicit pins:

- `gpt-5.6-terra`: exhaustive live-source verification, disconfirmation, source-family independence, and conflict preservation.
- `gpt-5.6-sol`: acquisition/location analysis, structured extraction, and bounded synthesis. Use an independent evidence-floor reviewer for high-stakes synthesis.

These routes must accumulate new model-specific scoreboard rows before automatic promotion is considered.

### Short mechanical code features

**Probation:** `engine: opencode`, `model: openrouter/cohere/north-mini-code:free`

Evidence: 2 tasks, 50% first-try, 100% final. A third comparable task must pass first try to reach the 2/3 promotion floor. The normalized catalog comparison now prevents this tested model from appearing again as an untested candidate.

### Avoid broad routing

Do not broadly route code-feature or data-pipeline work to the current DeepSeek alias. Recorded evidence remains weak:

- Code feature: 2 tasks, 0% final.
- Data pipeline: 5 tasks, 20% first-try, 40% final.

## Manifest forms

### Codex model pin

```json
{
  "engine": "codex",
  "engine_args": [
    "-m",
    "gpt-5.6-terra",
    "-c",
    "model_reasoning_effort=high"
  ]
}
```

Codex has no model placeholder in the current engine template. Do not also set the task `model` field.

### OpenRouter model pin

```json
{
  "engine": "opencode",
  "model": "openrouter/z-ai/glm-5.2"
}
```

Do not add a second `-m` or `--model` selector through `engine_args` when the engine template already has a model placeholder.

### Claude model pin

```json
{
  "engine": "claude-lean",
  "model": "fable"
}
```

## Decision boundary

No global default, saved workload route, or promotion was changed automatically. The next routing change should name the exact manifest task and selected model after human approval.
