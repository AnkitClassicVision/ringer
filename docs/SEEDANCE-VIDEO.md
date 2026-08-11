# Seedance video generation

Ringer's `seedance` engine is a first-class media lane backed by OpenRouter's Video API. It submits `POST /videos`, polls the returned job URL, downloads the completed MP4, and writes checked generation metadata. It is not a catalog alias and must not be routed through OpenCode or any other text-model harness.

## Configure

Copy the active `[engines.seedance]` block from `config.sample.toml` into your Ringer config and replace its `bin` with the absolute path to `engines/openrouter-video.py`. The default model is `bytedance/seedance-2.0`; a manifest can override it with `bytedance/seedance-2.0-fast` or `bytedance/seedance-1-5-pro`.

Authentication resolves in this order:

1. `OPENROUTER_API_KEY`
2. `$XDG_DATA_HOME/opencode/auth.json`
3. `~/.local/share/opencode/auth.json`

The auth JSON shape is `{"openrouter":{"key":"..."}}`. The adapter never prints the key. `--list-models` is public and does not require auth; paid generation always requires auth.

## Manifest example

```json
{
  "run_name": "seedance-hero-video",
  "workdir": "/absolute/path/to/scratch/seedance-hero-video",
  "max_parallel": 1,
  "tasks": [
    {
      "key": "hero-video",
      "task_type": "video-gen",
      "engine": "seedance",
      "model": "bytedance/seedance-2.0",
      "engine_args": ["--duration", "4", "--resolution", "720p", "--aspect-ratio", "16:9", "--audio"],
      "spec": "A locked-off cinematic sunrise over a calm mountain lake, natural motion, no text or logos.",
      "expect_files": ["video.mp4", "generation.json"],
      "check": "python3 /absolute/path/to/ringer/templates/asset-swarm/checks/check_generated_video.py --model bytedance/seedance-2.0",
      "verified": "The downloaded file is MP4/ISO-BMFF, ffprobe confirms an MP4/MOV-compatible format with a video stream, and its completed metadata has matching bytes and SHA-256."
    }
  ]
}
```

Running this manifest invokes a paid generation. Linting it does not.

## Adapter flags

The adapter supports `--taskdir`, `--model`, `--prompt`, `--duration`, `--resolution`, `--aspect-ratio`, `--size`, mutually exclusive `--audio`/`--no-audio`, `--seed`, repeatable `--first-frame`, `--last-frame`, and `--input-reference`, `--output`, `--metadata`, `--base-url`, `--poll-interval`, `--timeout`, `--download-timeout`, and `--list-models`. `--download-timeout` defaults to 300 seconds and must be positive.

Use `--input-reference TYPE=URL`, where `TYPE` is `image`, `audio`, or `video`. The flag is repeatable. For example, `--input-reference image=https://example.test/style.png --input-reference audio=https://example.test/guide.mp3` emits the corresponding nested OpenRouter `image_url` and `audio_url` reference objects.

Each repeatable `--first-frame URL` or `--last-frame URL` emits a `FrameImage` with `type: "image_url"`, nested `image_url: {"url": URL}`, and `frame_type: "first_frame"` or `"last_frame"`. These are frame controls, not generic input references.

The adapter fetches `/videos/models` before submission. It validates duration, resolution, aspect ratio, size, and first/last-frame support against the selected catalog row because the Seedance catalog variants can differ. Invalid values are rejected before the generation POST. Poll GETs retry bounded transient HTTP 429, 500, 502, 503, 504, and 529 responses with exponential backoff while remaining inside the overall job timeout; other 4xx responses fail immediately. Output and metadata paths must be relative paths confined to `--taskdir`.

The outputs default to `video.mp4` and `generation.json`. Metadata includes the model, non-secret parameters, job state, usage, output size, and SHA-256. The full prompt is represented by its hash and length. Credentials are omitted, including credential, token, signature, and expiry values embedded in nested URL query strings. OpenRouter's returned `usage` object is the source of truth for generation cost; inspect it in `generation.json` after completion.

The asset-swarm checker runs `ffprobe` by default and requires a successful probe, an MP4/MOV-compatible container, and at least one video stream in addition to the signature, hash, and metadata checks. `--skip-ffprobe` is reserved for isolated synthetic unit fixtures and must not be used in production manifests.
