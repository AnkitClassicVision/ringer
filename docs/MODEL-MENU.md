# Ringer model menu — what to route where

Ringer uses OAuth CLIs first and Pi for explicitly selected OpenRouter text
API work. Routing is always the manifest's `engine` + `model`; OAuth failure
does not trigger automatic API fallback.

Prices are from the local OpenRouter catalog snapshot
(`~/.ringer/openrouter-catalog.json`, fetched 2026-07-08). They drift — refresh
with `./ringer.py catalog --refresh` and re-check anything load-bearing.

## Routing rule

Use `codex` for OpenAI OAuth, `claude` for Anthropic OAuth, and `gemini` for
headless Google OAuth. Antigravity remains interactive only. Use
`pi-openrouter` for API-only models or an explicit paid fallback. Every Pi
selector must be exact lowercase `openrouter/<publisher>/<model>`.

## Named lanes (set `"engine"` in the manifest)

These are defined in `~/.config/ringer/config.toml`.

| `engine` | Default model | In/out $/M | Use for |
|---|---|---|---|
| `codex` | GPT-5.5 | (ChatGPT plan) | proven default; load-bearing work |
| `claude` | Sonnet | (claude.ai plan) | native Anthropic OAuth |
| `gemini` | Gemini | (Google OAuth) | native headless Google lane |
| `pi-openrouter` | `openrouter/z-ai/glm-5.2` | OpenRouter pricing | universal text API lane |
| `xai` | `openrouter/x-ai/grok-4.5` | OpenRouter pricing | Pi/OpenRouter compatibility alias for Grok |

### Minimal example

```json
{
  "run_name": "example",
  "workdir": "/tmp/ringer-example",
  "max_parallel": 3,
  "tasks": [
    { "key": "native", "engine": "codex", "spec": "...", "check": "..." },
    { "key": "api", "engine": "pi-openrouter", "model": "openrouter/x-ai/grok-4.5", "spec": "...", "check": "..." }
  ]
}
```

## Models by task type (with cost)

Pricing per million tokens (in/out), from the catalog snapshot.

### Cheap code / docs lane (proven-by-price tier)
- `openrouter/deepseek/deepseek-v3.2` — $0.23 / $0.34 — best $/quality for mechanical code
- `openrouter/deepseek/deepseek-v4-flash` — $0.09 / $0.18 — cheapest capable model
- `openrouter/qwen/qwen3-coder-flash` — $0.20 / $0.97 — code, faster variant
- `openrouter/meta-llama/llama-3.3-70b-instruct` — $0.10 / $0.32 — cheap, general
- `openrouter/z-ai/glm-5.2` — $0.93 / $3.00 — current pi-openrouter default, 1M ctx

### Code specialist lane
- `openrouter/qwen/qwen3-coder` — $0.22 / $1.80
- `openrouter/mistralai/codestral-2508` — $0.30 / $0.90
- `openrouter/moonshotai/kimi-k2.7-code` — $0.74 / $3.50

### Reasoning (hard problems; pricier)
- `openrouter/deepseek/deepseek-r1` — $0.70 / $2.50

### Frontier lane (via OpenRouter, overlap providers)
- `openrouter/anthropic/claude-sonnet-4.5` — $3.00 / $15.00
- `openrouter/anthropic/claude-haiku-4.5` — $1.00 / $5.00
- `openrouter/google/gemini-2.5-flash` — $0.30 / $2.50

### Grok through Pi/OpenRouter

`"engine": "xai"` is a compatibility alias for the same trusted Pi wrapper
used by `pi-openrouter`; its default is
`openrouter/x-ai/grok-4.5`. It is not a direct xAI API lane. Per-task
overrides must remain exact lowercase OpenRouter selectors.

Historical direct-xAI capability probes from 2026-07-12 remain evidence about
the old harness only. They are not current routing guidance.

The xAI provider also lists image and video models. Do not route those through
the text/code worker lane; they need a media asset harness and output checks.

### Free audition lane (zero spend)
Use ONLY for low-stakes, small tasks. The check must be strong; expect failures.
- `openrouter/cohere/north-mini-code:free` — $0 / $0 — current `free` lane default
- `openrouter/meta-llama/llama-3.3-70b-instruct:free` — $0 / $0
- `openrouter/nvidia/nemotron-3-super-120b-a12b:free` — $0 / $0

> Watch for free-model churn: free models on OpenRouter are often provider-backed
> (Venice, Cohere, NVIDIA) and get deprecated or rate-limited without notice.
> `qwen3-coder:free` (Venice-backed) was deprecated mid-2026 — if a free-model
> task fails with a provider 404, switch to another `:free` model rather than
> retrying. Refresh the snapshot with `./ringer.py catalog --refresh` and check
> `--free` before relying on one.

## How to choose (the decision tree)

1. **Load-bearing / hard?** → `codex` (proven, 0.80+ pass rate on your tasks).
2. **Mechanical code or docs, cost-sensitive?** → `deepseek` (cheapest solid).
3. **Long-context API model?** → `pi-openrouter` with an exact selector.
4. **Frontier quality, will pay per token?** → explicitly select `pi-openrouter`.
5. **Want a second frontier opinion or Grok coding lane?** → `xai`, the Pi/OpenRouter alias for `openrouter/x-ai/grok-4.5`.
6. **Auditioning a model at zero cost?** → `free`, small task + strong check.
7. **Need $0 + privacy (nothing leaves the machine)?** → `local` (gemma4:31b).

## Local models (Ollama — $0, on your GPU)

The `local` lane runs models on your machine via Ollama. Cost is always $0 and
nothing leaves the machine (privacy). The hard tradeoff: **one GPU = serial, not
parallel** — parallel tasks here queue, which defeats the swarm. Best use: zero-
cost single tasks, privacy-sensitive jobs, or auditions. Never pin load-bearing
parallel swarms here.

**Historical capability evidence (probed 2026-07-08 through OpenCode):**

These rows explain old scoreboard logs. They are not current routing guidance;
new OpenRouter text work uses `pi-openrouter`.

| Model | Result | Notes |
|---|---|---|
| `ollama/gemma4:31b` | **PROVEN** | The only local model that reliably writes checked files. Lane default. |
| `ollama/gemma4:31b-no-think` | FAIL | Ignores specs; emits greetings. Don't route Ringer work here. |
| `ollama/gpt-oss:20b` | FAIL | Emits write calls as text; won't invoke tools. |
| `ollama/glm-4.7-flash` | FAIL | Refuses — claims no filesystem tools. |
| `ollama/qwen3.6:latest` | FAIL | Writes code in chat, doesn't call write tool. |
| `ollama/qwen3.6:27b`, `qwen3:32b` | untested | Likely same tool-protocol gap as qwen3.6:latest. |
| `ollama/deepseek-r1:70b` | untested | Too heavy to run reliably on this GPU. |

**gemma4:31b spec rule (important):** after writing the file it tends to keep
exploring (searching skills/memory, making todo lists) and burns the timeout.
End every gemma4 spec with an explicit stop instruction, e.g.:

> *"...do exactly these steps, then reply DONE and stop. Do not search, explore,
> or make todo lists."*

Without that it passes ~50% (writes the file, then times out before exiting).
With it, first-try pass (~144s).

Usage:

```json
{ "key": "private-task", "engine": "local", "model": "ollama/gemma4:31b",
  "spec": "<...do the work...> Then reply DONE and stop. Do not explore.",
  "check": "..." }
```

## Discovering more

```bash
./ringer.py catalog --refresh        # refresh the local snapshot + change log
./ringer.py catalog --free           # zero-cost models
./ringer.py models --explore         # routing rec from your local evidence
```

## Adding a new named lane

Append to `~/.config/ringer/config.toml`:

```toml
[engines.pi-openrouter]
bin = "/absolute/path/to/ringer/engines/pi-openrouter-ringer.sh"
model_default = "openrouter/<provider>/<model>"
args_template = ["{taskdir}", "{model}", "{spec}"]
sandbox_args = []
full_access_args = []
token_regex = "tokens used: ([0-9]+)"
```

Then `"engine": "<name>"` in any manifest. Probe it first with a one-task
checked manifest before trusting it with real work.
