#!/usr/bin/env python3
"""Generate video through OpenRouter's first-class Video API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
USER_AGENT = "ringer-openrouter-video/1.0"
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired"}
TRANSIENT_POLL_STATUS_CODES = {429, 500, 502, 503, 504, 529}
POLL_RETRY_DELAYS = (1.0, 2.0, 4.0)
SENSITIVE_QUERY_KEYS = {
    "accesstoken",
    "expires",
    "googleaccessid",
    "sig",
    "signature",
    "token",
}


class AdapterError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taskdir", default=".")
    parser.add_argument("--model", default="bytedance/seedance-2.0")
    parser.add_argument("--prompt")
    parser.add_argument("--duration", type=int)
    parser.add_argument("--resolution")
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--size")
    audio = parser.add_mutually_exclusive_group()
    audio.add_argument("--audio", dest="generate_audio", action="store_true")
    audio.add_argument("--no-audio", dest="generate_audio", action="store_false")
    parser.set_defaults(generate_audio=None)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--first-frame", action="append", default=[])
    parser.add_argument("--last-frame", action="append", default=[])
    parser.add_argument("--input-reference", action="append", default=[])
    parser.add_argument("--output", default="video.mp4")
    parser.add_argument("--metadata", default="generation.json")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--download-timeout", type=float, default=300.0)
    parser.add_argument("--list-models", action="store_true")
    return parser.parse_args()


def api_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def resolve_url(base_url: str, value: str) -> str:
    if urllib.parse.urlparse(value).scheme:
        return value
    if value.startswith("/"):
        parsed = urllib.parse.urlparse(base_url)
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, value, "", "", ""))
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", value)


def load_key() -> str | None:
    env_key = os.environ.get("OPENROUTER_API_KEY")
    if env_key:
        return env_key
    xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    auth_path = xdg_data / "opencode" / "auth.json"
    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = data.get("openrouter", {}).get("key")
    return value if isinstance(value, str) and value else None


def request_json(
    url: str,
    *,
    key: str | None = None,
    method: str = "GET",
    payload: Any = None,
    transient_retries: bool = False,
    deadline: float | None = None,
) -> Any:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    body = None
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    attempt = 0
    while True:
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            raise AdapterError(f"timed out before {method} {url} completed")
        request_timeout = 30 if remaining is None else min(30, max(0.001, remaining))
        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if (
                transient_retries
                and method == "GET"
                and exc.code in TRANSIENT_POLL_STATUS_CODES
                and attempt < len(POLL_RETRY_DELAYS)
            ):
                exc.close()
                delay = POLL_RETRY_DELAYS[attempt]
                attempt += 1
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise AdapterError(f"timed out retrying {method} {url}") from None
                    delay = min(delay, remaining)
                time.sleep(delay)
                continue
            detail = exc.read(1000).decode("utf-8", errors="replace")
            if key:
                detail = detail.replace(key, "[REDACTED]")
            raise AdapterError(f"OpenRouter HTTP {exc.code} for {method} {url}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AdapterError(f"OpenRouter request failed for {method} {url}: {exc}") from None


def model_list(payload: Any) -> list[dict[str, Any]]:
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise AdapterError("/videos/models returned an unexpected response shape")
    return [row for row in rows if isinstance(row, dict)]


def catalog_values(model: dict[str, Any], field: str) -> list[Any]:
    value = model.get(field)
    return value if isinstance(value, list) else []


def validate_catalog_value(model: dict[str, Any], field: str, value: Any, label: str) -> None:
    supported = catalog_values(model, field)
    if value is not None and value not in supported:
        choices = ", ".join(str(item) for item in supported) or "none"
        raise AdapterError(f"model {model.get('id')} does not support {label} {value!r}; supported: {choices}")


def validate_request(args: argparse.Namespace, models: list[dict[str, Any]], request: dict[str, Any]) -> None:
    model = next((row for row in models if row.get("id") == args.model), None)
    if model is None:
        raise AdapterError(f"video model is not listed by OpenRouter: {args.model}")
    validate_catalog_value(model, "supported_durations", args.duration, "duration")
    validate_catalog_value(model, "supported_resolutions", args.resolution, "resolution")
    validate_catalog_value(model, "supported_aspect_ratios", args.aspect_ratio, "aspect ratio")
    validate_catalog_value(model, "supported_sizes", args.size, "size")
    supported_frames = catalog_values(model, "supported_frame_images")
    for frame_type, values in (("first_frame", args.first_frame), ("last_frame", args.last_frame)):
        if values and frame_type not in supported_frames:
            raise AdapterError(f"model {args.model} does not support {frame_type}")


def parse_input_reference(value: str) -> dict[str, Any]:
    if "=" not in value:
        raise AdapterError(f"invalid --input-reference {value!r}; expected TYPE=URL")
    reference_type, url = value.split("=", 1)
    if reference_type not in {"image", "audio", "video"}:
        raise AdapterError(
            f"invalid --input-reference type {reference_type!r}; expected image, audio, or video"
        )
    if not url:
        raise AdapterError(f"invalid --input-reference {value!r}; URL must not be empty")
    api_type = f"{reference_type}_url"
    return {"type": api_type, api_type: {"url": url}}


def confined_path(taskdir: Path, value: str, label: str) -> Path:
    supplied = Path(value)
    if supplied.is_absolute():
        raise AdapterError(f"--{label} must be a relative path inside --taskdir")
    resolved = (taskdir / supplied).resolve()
    try:
        resolved.relative_to(taskdir)
    except ValueError:
        raise AdapterError(f"--{label} escapes --taskdir: {value}") from None
    return resolved


def build_request(args: argparse.Namespace) -> dict[str, Any]:
    if not args.prompt:
        raise AdapterError("--prompt is required for video generation")
    request: dict[str, Any] = {"prompt": args.prompt, "model": args.model}
    for arg_name, api_name in (
        ("duration", "duration"),
        ("resolution", "resolution"),
        ("aspect_ratio", "aspect_ratio"),
        ("size", "size"),
        ("generate_audio", "generate_audio"),
        ("seed", "seed"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            request[api_name] = value
    frames = (
        [
            {"type": "image_url", "image_url": {"url": value}, "frame_type": "first_frame"}
            for value in args.first_frame
        ]
        + [
            {"type": "image_url", "image_url": {"url": value}, "frame_type": "last_frame"}
            for value in args.last_frame
        ]
    )
    if frames:
        request["frame_images"] = frames
    if args.input_reference:
        request["input_references"] = [parse_input_reference(value) for value in args.input_reference]
    return request


def is_sensitive_query_key(key: str) -> bool:
    normalized = "".join(character for character in key.lower() if character.isalnum())
    return (
        normalized in SENSITIVE_QUERY_KEYS
        or "credential" in normalized
        or "signature" in normalized
        or normalized.endswith("token")
    )


def scrub_url_query(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if not parsed.query:
        return value
    clean_query = urllib.parse.urlencode(
        [(key, item) for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
         if not is_sensitive_query_key(key)],
        doseq=True,
    )
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, clean_query, parsed.fragment))


def scrub(value: Any, secret: str | None = None) -> Any:
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"key", "secret"} or any(
                word in lowered for word in ("authorization", "credential", "api_key", "apikey", "token")
            ):
                continue
            clean[key] = scrub(item, secret)
        return clean
    if isinstance(value, list):
        return [scrub(item, secret) for item in value]
    if isinstance(value, str):
        clean = value.replace(secret, "[REDACTED]") if secret else value
        return scrub_url_query(clean)
    return value


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def download_video(url: str, key: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}", "Accept": "video/mp4", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise AdapterError(f"video download failed from {url}: {exc}") from None
    if len(data) < 12 or data[4:8] != b"ftyp":
        raise AdapterError("downloaded content is empty or not an MP4/ISO-BMFF file")
    return data


def run(args: argparse.Namespace) -> int:
    if args.download_timeout <= 0:
        raise AdapterError("--download-timeout must be positive")
    taskdir = Path(args.taskdir).resolve()
    output_path = confined_path(taskdir, args.output, "output")
    metadata_path = confined_path(taskdir, args.metadata, "metadata")
    models_payload = request_json(api_url(args.base_url, "videos/models"))
    models = model_list(models_payload)
    if args.list_models:
        print(json.dumps(models_payload, indent=2, sort_keys=True))
        return 0

    key = load_key()
    if not key:
        raise AdapterError(
            "OpenRouter authentication required: set OPENROUTER_API_KEY or configure opencode/auth.json"
        )
    request = build_request(args)
    validate_request(args, models, request)
    submitted = request_json(api_url(args.base_url, "videos"), key=key, method="POST", payload=request)
    if not isinstance(submitted, dict) or not submitted.get("id") or not submitted.get("polling_url"):
        raise AdapterError("video submission response omitted id or polling_url")
    polling_url = resolve_url(args.base_url, str(submitted["polling_url"]))
    deadline = time.monotonic() + args.timeout
    job: dict[str, Any] = submitted
    while True:
        status = str(job.get("status", "")).lower()
        if status in TERMINAL_STATUSES:
            break
        if time.monotonic() >= deadline:
            raise AdapterError(f"timed out waiting for video job {submitted['id']}")
        time.sleep(max(0.0, min(args.poll_interval, deadline - time.monotonic())))
        if time.monotonic() >= deadline:
            raise AdapterError(f"timed out waiting for video job {submitted['id']}")
        next_job = request_json(
            polling_url, key=key, transient_retries=True, deadline=deadline,
        )
        if not isinstance(next_job, dict):
            raise AdapterError("video polling response had an unexpected shape")
        job = next_job
    status = str(job.get("status", "")).lower()
    if status != "completed":
        message = job.get("error") or job.get("message") or "no provider detail"
        if key and isinstance(message, str):
            message = message.replace(key, "[REDACTED]")
        raise AdapterError(f"video job {submitted['id']} ended with status {status}: {message}")

    content_url = api_url(args.base_url, f"videos/{urllib.parse.quote(str(submitted['id']), safe='')}/content?index=0")
    video = download_video(content_url, key, args.download_timeout)
    digest = hashlib.sha256(video).hexdigest()
    safe_request = {key_: value for key_, value in request.items() if key_ != "prompt"}
    safe_request["prompt_sha256"] = hashlib.sha256(args.prompt.encode("utf-8")).hexdigest()
    safe_request["prompt_length"] = len(args.prompt)
    metadata = {
        "model": args.model,
        "status": status,
        "request": safe_request,
        "job": scrub(job, key),
        "submission": scrub({**submitted, "polling_url": submitted["polling_url"]}, key),
        "usage": scrub(job.get("usage", submitted.get("usage")), key),
        "output": {"path": args.output, "bytes": len(video), "sha256": digest},
    }
    atomic_write(output_path, video)
    atomic_write(metadata_path, (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(f"completed video job {submitted['id']}: wrote {args.output} ({len(video)} bytes)")
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except AdapterError as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
