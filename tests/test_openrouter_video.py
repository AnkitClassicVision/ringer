#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "engines" / "openrouter-video.py"
CHECK = ROOT / "templates" / "asset-swarm" / "checks" / "check_generated_video.py"
MODEL = "bytedance/seedance-2.0"
FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 40


class State:
    def __init__(self) -> None:
        self.models = [{
            "id": MODEL,
            "supported_durations": [4, 8],
            "supported_resolutions": ["720p", "1080p"],
            "supported_aspect_ratios": ["16:9", "9:16"],
            "supported_sizes": ["1280x720"],
            "supported_frame_images": ["first_frame", "last_frame"],
            "allowed_passthrough_parameters": ["duration"],
        }]
        self.polls = [{"id": "job-1", "status": "pending"}, {
            "id": "job-1", "status": "completed", "usage": {"cost": 0.12},
            "unsigned_urls": ["https://example.invalid/video.mp4"],
            "delivery": {
                "url": (
                    "https://media.example.invalid/video.mp4?quality=source&token=query-secret-one"
                    "&X-Amz-Credential=query-secret-two&X-Amz-Signature=query-secret-three"
                    "&X-Amz-Security-Token=query-secret-four&expires=123456"
                )
            },
        }]
        self.poll_errors: list[int] = []
        self.posted: list[dict[str, object]] = []
        self.auth_headers: list[str | None] = []
        self.user_agents: list[str | None] = []
        self.poll_count = 0


class Handler(BaseHTTPRequestHandler):
    server: "MockServer"

    def log_message(self, _format: str, *args: object) -> None:
        pass

    def send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        state = self.server.state
        state.auth_headers.append(self.headers.get("Authorization"))
        state.user_agents.append(self.headers.get("User-Agent"))
        if self.path == "/api/v1/videos/models":
            self.send_json(200, {"data": state.models})
        elif self.path == "/api/v1/videos/job-1":
            if state.poll_errors:
                state.poll_count += 1
                self.send_json(state.poll_errors.pop(0), {"error": "temporary"})
                return
            index = min(state.poll_count, len(state.polls) - 1)
            state.poll_count += 1
            self.send_json(200, state.polls[index])
        elif self.path == "/api/v1/videos/job-1/content?index=0":
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(FAKE_MP4)))
            self.end_headers()
            self.wfile.write(FAKE_MP4)
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        state = self.server.state
        state.auth_headers.append(self.headers.get("Authorization"))
        state.user_agents.append(self.headers.get("User-Agent"))
        if self.path != "/api/v1/videos":
            self.send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        state.posted.append(json.loads(self.rfile.read(length)))
        self.send_json(202, {
            "id": "job-1", "polling_url": "/api/v1/videos/job-1", "status": "pending",
            "nested": {
                "callback": (
                    "https://callback.example.invalid/status?signature=query-secret-five"
                    "&GoogleAccessId=query-secret-six&view=compact"
                )
            },
        })


class MockServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], state: State):
        super().__init__(address, Handler)
        self.state = state


class OpenRouterVideoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = State()
        self.server = MockServer(("127.0.0.1", 0), self.state)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}/api/v1"
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def run_adapter(self, *args: str, key: str | None = "test-secret-key", env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        run_env = os.environ.copy()
        run_env.pop("OPENROUTER_API_KEY", None)
        if key is not None:
            run_env["OPENROUTER_API_KEY"] = key
        if env:
            run_env.update(env)
        return subprocess.run(
            [sys.executable, str(ADAPTER), "--base-url", self.base_url, *args],
            cwd=ROOT, env=run_env, text=True, capture_output=True, timeout=10, check=False,
        )

    def generation_args(self) -> list[str]:
        return [
            "--taskdir", str(self.root), "--model", MODEL, "--prompt", "A quiet lake at dawn",
            "--duration", "4", "--resolution", "720p", "--aspect-ratio", "16:9",
            "--size", "1280x720", "--audio", "--seed", "42", "--first-frame", "https://img/first.png",
            "--last-frame", "https://img/last.png", "--input-reference", "image=https://img/ref.png",
            "--input-reference", "audio=https://media/ref.mp3",
            "--input-reference", "video=https://media/ref.mp4",
            "--poll-interval", "0.01", "--timeout", "2",
        ]

    def ffprobe_env(self, payload: object, *, exit_code: int = 0) -> dict[str, str]:
        bindir = self.root / "bin"
        bindir.mkdir(exist_ok=True)
        probe = bindir / "ffprobe"
        probe.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"print(json.dumps({payload!r}))\n"
            f"raise SystemExit({exit_code})\n",
            encoding="utf-8",
        )
        probe.chmod(0o755)
        return {"PATH": str(bindir) + os.pathsep + os.environ.get("PATH", "")}

    def test_public_list_models_needs_no_auth(self) -> None:
        proc = self.run_adapter("--list-models", key=None)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn(MODEL, proc.stdout)
        self.assertEqual([None], self.state.auth_headers)
        self.assertEqual(["ringer-openrouter-video/1.0"], self.state.user_agents)

    def test_env_key_generation_posts_polls_downloads_and_writes_safe_metadata(self) -> None:
        proc = self.run_adapter(*self.generation_args())
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual(1, len(self.state.posted))
        posted = self.state.posted[0]
        self.assertEqual("A quiet lake at dawn", posted["prompt"])
        self.assertEqual(MODEL, posted["model"])
        self.assertEqual(4, posted["duration"])
        self.assertEqual("720p", posted["resolution"])
        self.assertEqual("16:9", posted["aspect_ratio"])
        self.assertEqual("1280x720", posted["size"])
        self.assertIs(True, posted["generate_audio"])
        self.assertEqual(42, posted["seed"])
        self.assertEqual([
            {
                "type": "image_url",
                "image_url": {"url": "https://img/first.png"},
                "frame_type": "first_frame",
            },
            {
                "type": "image_url",
                "image_url": {"url": "https://img/last.png"},
                "frame_type": "last_frame",
            },
        ], posted["frame_images"])
        self.assertEqual([
            {"type": "image_url", "image_url": {"url": "https://img/ref.png"}},
            {"type": "audio_url", "audio_url": {"url": "https://media/ref.mp3"}},
            {"type": "video_url", "video_url": {"url": "https://media/ref.mp4"}},
        ], posted["input_references"])
        self.assertGreaterEqual(self.state.poll_count, 2)
        video = (self.root / "video.mp4").read_bytes()
        self.assertEqual(FAKE_MP4, video)
        metadata_text = (self.root / "generation.json").read_text()
        metadata = json.loads(metadata_text)
        self.assertEqual(MODEL, metadata["model"])
        self.assertEqual("completed", metadata["status"])
        self.assertEqual(hashlib.sha256(video).hexdigest(), metadata["output"]["sha256"])
        self.assertNotIn("test-secret-key", metadata_text)
        self.assertNotIn("A quiet lake at dawn", metadata_text)
        for secret in (
            "query-secret-one", "query-secret-two", "query-secret-three",
            "query-secret-four", "query-secret-five", "query-secret-six", "123456",
        ):
            self.assertNotIn(secret, metadata_text)
        self.assertIn("quality=source", metadata_text)
        self.assertIn("view=compact", metadata_text)
        self.assertTrue(all(header == "Bearer test-secret-key" for header in self.state.auth_headers[1:]))
        self.assertTrue(self.state.user_agents)
        self.assertTrue(all(agent == "ringer-openrouter-video/1.0" for agent in self.state.user_agents))

    def test_opencode_auth_fallback_in_isolated_xdg_data_home(self) -> None:
        xdg = self.root / "xdg-data"
        auth = xdg / "opencode" / "auth.json"
        auth.parent.mkdir(parents=True)
        auth.write_text(json.dumps({"openrouter": {"type": "api", "key": "fallback-secret"}}))
        home = self.root / "home"
        home.mkdir()
        proc = self.run_adapter(
            *self.generation_args(), key=None,
            env={"HOME": str(home), "XDG_DATA_HOME": str(xdg)},
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("Bearer fallback-secret", self.state.auth_headers)
        self.assertNotIn("fallback-secret", (self.root / "generation.json").read_text())

    def test_unsupported_model_fails_before_post(self) -> None:
        proc = self.run_adapter(
            "--taskdir", str(self.root), "--model", "missing/model", "--prompt", "short",
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("not listed", proc.stderr)
        self.assertEqual([], self.state.posted)

    def test_catalog_rejects_unsupported_values_and_frames_before_post(self) -> None:
        cases = [
            (("--duration", "5"), "duration"),
            (("--resolution", "480p"), "resolution"),
            (("--aspect-ratio", "1:1"), "aspect ratio"),
            (("--size", "1920x1080"), "size"),
        ]
        for extra, message in cases:
            with self.subTest(extra=extra):
                proc = self.run_adapter(
                    "--taskdir", str(self.root), "--model", MODEL, "--prompt", "short", *extra,
                )
                self.assertNotEqual(0, proc.returncode)
                self.assertIn(message, proc.stderr)
                self.assertEqual([], self.state.posted)
        self.state.models[0]["supported_frame_images"] = ["first_frame"]
        proc = self.run_adapter(
            "--taskdir", str(self.root), "--model", MODEL, "--prompt", "short",
            "--last-frame", "https://img/last.png",
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("last_frame", proc.stderr)
        self.assertEqual([], self.state.posted)

    def test_invalid_input_references_fail_before_post(self) -> None:
        for value, message in (("https://img/ref.png", "TYPE=URL"), ("text=https://ref", "type 'text'"), ("image=", "must not be empty")):
            with self.subTest(value=value):
                proc = self.run_adapter(
                    "--taskdir", str(self.root), "--model", MODEL, "--prompt", "short",
                    "--input-reference", value,
                )
                self.assertNotEqual(0, proc.returncode)
                self.assertIn(message, proc.stderr)
                self.assertEqual([], self.state.posted)

    def test_output_paths_must_stay_inside_taskdir(self) -> None:
        outside = self.root.parent / "escaped-video.mp4"
        for flag, value in (("--output", "../escaped-video.mp4"), ("--metadata", str(outside))):
            with self.subTest(flag=flag):
                proc = self.run_adapter(
                    "--taskdir", str(self.root), "--model", MODEL, "--prompt", "short", flag, value,
                )
                self.assertNotEqual(0, proc.returncode)
                self.assertIn("taskdir", proc.stderr)
                self.assertEqual([], self.state.auth_headers)
                self.assertFalse(outside.exists())

    def test_failed_job_reports_useful_non_secret_error(self) -> None:
        self.state.polls = [{"id": "job-1", "status": "failed", "error": "provider rejected input"}]
        proc = self.run_adapter(*self.generation_args())
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("status failed", proc.stderr)
        self.assertIn("provider rejected input", proc.stderr)
        self.assertNotIn("test-secret-key", proc.stdout + proc.stderr)
        self.assertNotIn("A quiet lake at dawn", proc.stdout + proc.stderr)

    def test_timeout(self) -> None:
        self.state.polls = [{"id": "job-1", "status": "in_progress"}]
        args = self.generation_args()
        args[args.index("--timeout") + 1] = "0.05"
        proc = self.run_adapter(*args)
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("timed out", proc.stderr)
        self.assertFalse((self.root / "video.mp4").exists())

    def test_poll_retries_one_transient_503_then_completes(self) -> None:
        self.state.poll_errors = [503]
        self.state.polls = [{
            "id": "job-1", "status": "completed",
            "unsigned_urls": ["https://example.invalid/video.mp4"],
        }]
        args = self.generation_args()
        args[args.index("--timeout") + 1] = "3"
        proc = self.run_adapter(*args)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual(2, self.state.poll_count)
        self.assertTrue((self.root / "video.mp4").exists())

    def test_poll_does_not_retry_auth_4xx(self) -> None:
        self.state.poll_errors = [401]
        proc = self.run_adapter(*self.generation_args())
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("HTTP 401", proc.stderr)
        self.assertEqual(1, self.state.poll_count)

    def test_download_timeout_must_be_positive(self) -> None:
        proc = self.run_adapter(
            "--taskdir", str(self.root), "--model", MODEL, "--prompt", "short",
            "--download-timeout", "0",
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("--download-timeout must be positive", proc.stderr)
        self.assertEqual([], self.state.auth_headers)

    def test_generated_video_check_accepts_valid_pair(self) -> None:
        video = self.root / "video.mp4"
        metadata = self.root / "generation.json"
        video.write_bytes(FAKE_MP4)
        metadata.write_text(json.dumps({
            "model": MODEL, "status": "completed",
            "output": {"bytes": len(FAKE_MP4), "sha256": hashlib.sha256(FAKE_MP4).hexdigest()},
        }))
        proc = subprocess.run(
            [sys.executable, str(CHECK), "--video", str(video), "--metadata", str(metadata), "--model", MODEL],
            text=True, capture_output=True, check=False,
            env={**os.environ, **self.ffprobe_env({
                "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
                "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
            })},
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)

    def test_generated_video_check_rejects_missing_video_stream(self) -> None:
        video = self.root / "video.mp4"
        metadata = self.root / "generation.json"
        video.write_bytes(FAKE_MP4)
        metadata.write_text(json.dumps({
            "model": MODEL, "status": "completed",
            "output": {"bytes": len(FAKE_MP4), "sha256": hashlib.sha256(FAKE_MP4).hexdigest()},
        }))
        proc = subprocess.run(
            [sys.executable, str(CHECK), "--video", str(video), "--metadata", str(metadata)],
            text=True, capture_output=True, check=False,
            env={**os.environ, **self.ffprobe_env({
                "format": {"format_name": "mov,mp4"},
                "streams": [{"codec_type": "audio"}],
            })},
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("no video stream", proc.stdout)

    def test_generated_video_check_rejects_invalid_mp4(self) -> None:
        video = self.root / "bad.mp4"
        metadata = self.root / "generation.json"
        video.write_bytes(b"not video")
        metadata.write_text(json.dumps({"model": MODEL, "status": "completed", "output": {}}))
        proc = subprocess.run(
            [
                sys.executable, str(CHECK), "--video", str(video), "--metadata", str(metadata),
                "--skip-ffprobe",
            ],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("not a non-empty MP4", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
