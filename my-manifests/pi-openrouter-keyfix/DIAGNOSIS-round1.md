# Pi 0.84.1 credential-injection regression

## Root cause

Pi 0.84.1 still supports OpenRouter's `OPENROUTER_API_KEY`, but startup now touches the credential store before request authentication is resolved.

- `dist/core/agent-session-services.js`, approximately lines 45-75: `createAgentSessionServices()` constructs `ModelRuntime` with `authPath: join(agentDir, "auth.json")`, then calls `modelRuntime.refresh({ allowNetwork: false })` before returning services.
- `dist/core/model-runtime.js`, approximately lines 180-210: the refresh path runs provider availability/auth checks and `this.credentials.list({ signal })` together. Credential listing is therefore mandatory during startup even when provider authentication is available from the environment.
- `node_modules/@earendil-works/pi-ai/dist/models.js`, approximately line 219, and `dist/auth/resolve.js`, approximately line 129: a credential-store read exception is wrapped as `Credential store read failed for <provider>` and propagated as a fatal `ModelsError`. There is no environment fallback for a store I/O error.
- `dist/core/provider-composer.js`, approximately lines 200-275: configured API-key resolution still checks environment references and the inherited OpenRouter provider still resolves its supported environment authentication. The current OpenRouter environment variable remains `OPENROUTER_API_KEY`.
- `dist/cli/args.js`, approximately lines 43-44 and 245-246: `--api-key <key>` remains supported.
- `dist/main.js`, approximately lines 641-650: `--api-key` is installed with `modelRuntime.setRuntimeApiKey()` only after services and the initial model-runtime refresh have already been created. It cannot prevent the earlier credential-store failure.
- `dist/core/model-config.js`, approximately lines 165-180, permits provider `apiKey` in `models.json`; `dist/core/resolve-config-value.js`, approximately lines 117-128, permits `$ENV_VAR` references. This does not bypass the earlier unconditional store listing.

The existing wrapper binds `/agent` read-only. When Pi's startup store backend tries to create or lock `/agent/auth.json`, the filesystem returns `EROFS`; startup exits before a model request.

## Chosen mechanism

Keep `/agent` unchanged as the read-only, credential-free generated model directory. Add a second view of its single `models.json` file inside sandbox tmpfs at `/tmp/home/.pi/agent/models.json`, mounted read-only. Set `PI_CODING_AGENT_DIR=/tmp/home/.pi/agent` in the supervisor's clean environment. Pi can then create its required empty `{}` `auth.json` and lock metadata only in sandbox tmpfs. The actual OpenRouter key continues to come from `OPENROUTER_API_KEY` in the clean environment.

Required wrapper diff:

```diff
@@ bwrap_argv
     --tmpfs /tmp \
     --dir /tmp/home \
+    --dir /tmp/home/.pi \
+    --dir /tmp/home/.pi/agent \
+    --ro-bind "$runtime_agent_dir/models.json" /tmp/home/.pi/agent/models.json \
     --dir /opt \
@@ clean_env
-        "PI_CODING_AGENT_DIR": "/agent",
+        "PI_CODING_AGENT_DIR": "/tmp/home/.pi/agent",
```

This session could not apply that diff because its managed filesystem grants write access only to the manifest work directory, not `/mnt/d_drive/repos/ringer/engines/pi-openrouter-ringer.sh`. The patch tool rejected the edit as outside the writable project root. The wrapper therefore remains unmodified in this run.

## Alternatives rejected

- Adding or renaming an environment variable: rejected because `OPENROUTER_API_KEY` is already the supported name and environment authentication is reached only after the failing startup store access.
- Passing `--api-key`: rejected because Pi applies it after the initial refresh, and placing a key in process arguments would enlarge secret exposure.
- Adding `apiKey: "$OPENROUTER_API_KEY"` to generated `models.json`: rejected because it cannot bypass credential-store listing.
- Mounting or copying the host `auth.json`: rejected because it would put credential material in a sandbox mount and violate the design.
- Making `/agent` writable or adding `/agent/auth.json`: rejected because `/agent` must remain read-only and contain only `models.json`.
- Pinning 0.84.0: no longer necessary because a wrapper-only solution exists that stores no key on disk or mount.

## Preserved invariants

- Bubblewrap remains fail-closed; no unconfined launch or fallback is introduced.
- `/agent` remains mounted read-only and contains only the generated `models.json`.
- No credential file is copied from the host or mounted into the sandbox.
- The only sandbox credential-store file Pi may create is an empty metadata object on ephemeral `/tmp` tmpfs; it contains no key.
- The OpenRouter key remains only in supervisor memory and the child's clean environment.
- Exact-key transcript detection and redaction remain unchanged.
- Child stdin remains closed by the existing launch behavior.
- No fallback to another harness is added.
- Existing host-auth validation, child-status validation, and cleanup logic remain unchanged.
- No Pi package or dependency is installed, updated, or modified.
