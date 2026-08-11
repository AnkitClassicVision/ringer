#!/usr/bin/env python3
"""Validate an OpenRouter-generated MP4 and its sanitized metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


COMPATIBLE_FORMATS = {"mov", "mp4", "m4a", "3gp", "3g2", "mj2"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default="video.mp4")
    parser.add_argument("--metadata", default="generation.json")
    parser.add_argument("--model")
    parser.add_argument(
        "--skip-ffprobe", action="store_true",
        help="skip media probing only for isolated synthetic unit fixtures",
    )
    args = parser.parse_args()
    failures: list[str] = []
    video_path = Path(args.video)
    metadata_path = Path(args.metadata)
    try:
        video = video_path.read_bytes()
    except OSError as exc:
        failures.append(f"cannot read video {video_path}: {exc}")
        video = b""
    if len(video) < 12 or video[4:8] != b"ftyp":
        failures.append(f"{video_path} is not a non-empty MP4/ISO-BMFF file")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"cannot read valid metadata {metadata_path}: {exc}")
        metadata = {}
    if metadata.get("status") != "completed":
        failures.append("metadata status is not completed")
    if args.model and metadata.get("model") != args.model:
        failures.append(f"metadata model is not {args.model}")
    output = metadata.get("output", {})
    if video and output.get("bytes") != len(video):
        failures.append("metadata output byte count does not match video")
    if video and output.get("sha256") != hashlib.sha256(video).hexdigest():
        failures.append("metadata output sha256 does not match video")
    serialized = json.dumps(metadata).lower()
    if "authorization" in serialized or "bearer " in serialized:
        failures.append("metadata contains authorization material")
    if not args.skip_ffprobe and video:
        try:
            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "format=format_name:stream=codec_type", "-of", "json", str(video_path),
                ],
                text=True, capture_output=True, check=False, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            failures.append(f"ffprobe could not inspect {video_path}: {exc}")
        else:
            if probe.returncode != 0:
                detail = probe.stderr.strip() or f"exit {probe.returncode}"
                failures.append(f"ffprobe rejected {video_path}: {detail}")
            else:
                try:
                    probe_data = json.loads(probe.stdout)
                except json.JSONDecodeError as exc:
                    failures.append(f"ffprobe returned invalid JSON for {video_path}: {exc}")
                else:
                    format_data = probe_data.get("format", {}) if isinstance(probe_data, dict) else {}
                    format_name = format_data.get("format_name", "") if isinstance(format_data, dict) else ""
                    format_names = set(format_name.split(","))
                    if not format_names.intersection(COMPATIBLE_FORMATS):
                        failures.append("ffprobe format is not MP4/MOV compatible")
                    streams = probe_data.get("streams", []) if isinstance(probe_data, dict) else []
                    if not isinstance(streams, list):
                        streams = []
                    if not any(
                        isinstance(stream, dict) and stream.get("codec_type") == "video"
                        for stream in streams
                    ):
                        failures.append("ffprobe found no video stream")
    if failures:
        print("FAIL:")
        for failure in failures:
            print(f" - {failure}")
        return 1
    probe_status = "signature-only synthetic fixture" if args.skip_ffprobe else "ffprobe-verified media"
    print(f"PASS: {video_path} is {probe_status} with matching completed metadata")
    return 0


if __name__ == "__main__":
    sys.exit(main())
