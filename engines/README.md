# Ringer engine wrappers

These shell scripts adapt third-party agent CLIs to Ringer's engine contract:

```text
<bin> <taskdir> <access_args> ... <spec>
```

Ringer spawns the engine as a subprocess, passes the task directory as the first
argument, injects any per-engine environment variables configured in
`[engines.<name>.env]`, and verifies the resulting artifact with the task's
check command.

## Per-engine environment variables

Ringer now supports an `env` table under each engine in `config.toml`:

```toml
[engines.omnigent]
bin = "/absolute/path/to/ringer/engines/omnigent-sandboxed.sh"
args_template = ["{taskdir}", "{access_args}", "-z", "{spec}", "-m", "{model}", "{engine_args}"]

[engines.omnigent.env]
OMNIGENT_SERVER = "http://127.0.0.1:6767"
OMNIGENT_AGENT_ID = "your-agent-id-here"
```

Values in `[engines.<name>.env]` override inherited process environment
variables for that engine's worker subprocess only. Shell-level environment
variables can still be used, which is useful for local overrides and CI secrets.

## Wrappers

### `hermes-sandboxed.sh`

Runs the Hermes agent one-shot under macOS Seatbelt. Supports `--no-sandbox`
as the second argument for full-access runs.

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `HERMES_HOME` | `~/.hermes` | Hermes config/credential tree |
| `HERMES_STATE` | `~/.local/state/hermes` | Hermes state directory |
| `PAPERCLIP_OLLAMA_CLOUD_ADMISSION_BIN` | (none) | Path to `ollama_cloud_admission.py` |
| `PAPERCLIP_OLLAMA_CLOUD_ADMISSION_POLICY` | (none) | Path to `cloud-admission-policy.v1.json` |
| `PAPERCLIP_OLLAMA_CLOUD_ADMISSION_STATE_DIR` | (none) | Admission state directory |

Cloud admission is **only** required when a task pins an `ollama-cloud` route
(model starts with `ollama-cloud:` or `--provider ollama-cloud` is used). If a
cloud route is pinned and the admission variables are not configured or the
binary/state dir is missing, the wrapper exits with code 74 and a clear error.
Non-cloud routes ignore admission entirely.

### `omnigent-sandboxed.sh`

Drives Omnigent's session API headlessly.

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `OMNIGENT_SERVER` | `http://127.0.0.1:6767` | Omnigent session API endpoint |
| `OMNIGENT_AGENT_ID` | (required) | Agent ID used to create sessions |
| `OMNIGENT_DEFAULT_MODEL` | `ollama-cloud/deepseek-v4-pro` | Fallback model when `-m` is not supplied |

If `OMNIGENT_AGENT_ID` is empty, the wrapper exits with code 2.

## Adding a new wrapper

1. Make the script executable (`chmod +x engines/<name>-sandboxed.sh`).
2. Avoid hardcoding installation-specific paths or IDs.
3. Read configuration from `[engines.<name>.env]` via environment variables.
4. Fail closed with a clear error when required configuration is missing.
5. Add an example block to `config.sample.toml`.
6. Document the env vars in this file.
