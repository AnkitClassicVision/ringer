#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WRAPPER = ROOT / "gemini-oauth.sh"
SECRET = "secret-sentinel-must-not-leak"
SCRUBBED = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_GEMINI_BASE_URL", "GEMINI_CLI_HOME", "GEMINI_SYSTEM_MD",
    "RINGER_OAUTH_TEST_MODE", "RINGER_TEST_GEMINI_BIN",
)


class GeminiOAuthWrapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.home = base / "home"
        self.bin = base / "bin"
        self.marker = base / "invoked.json"
        (self.home / ".gemini").mkdir(parents=True)
        self.bin.mkdir()
        (self.home / ".gemini" / "settings.json").write_text(
            json.dumps({"security": {"auth": {"selectedType": "oauth-personal"}}}),
            encoding="utf-8",
        )
        (self.home / ".gemini" / "oauth_creds.json").write_text(SECRET, encoding="utf-8")
        fake = self.bin / "gemini"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            f"keys = {SCRUBBED!r}\n"
            "payload = {'argv': sys.argv[1:], "
            "'scrubbed_present': {k: k in os.environ for k in keys}, "
            "'settings_path': os.environ.get('GEMINI_CLI_SYSTEM_SETTINGS_PATH')}\n"
            "open(os.environ['FAKE_MARKER'], 'w', encoding='utf-8').write(json.dumps(payload))\n"
            "print(json.dumps(payload))\n",
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

    def run_wrapper(self, argv: list[str], env_extra: dict[str, str] | None = None):
        env = os.environ.copy()
        env.update({
            "HOME": str(self.home),
            "PATH": f"{self.bin}{os.pathsep}{env.get('PATH', '')}",
            "FAKE_MARKER": str(self.marker),
        })
        env.update(env_extra or {})
        return subprocess.run([str(WRAPPER), *argv], text=True, capture_output=True, env=env)

    def valid_args(self, model: str = "gemini-3.5-flash") -> list[str]:
        return ["-m", model, "--approval-mode", "auto_edit", "--output-format", "json",
                "--skip-trust", "-p", "literal $HOME `id` $(uname) ; & | prompt"]

    def payload(self, result: subprocess.CompletedProcess[str]) -> dict[str, object]:
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def assert_blocked(self, argv: list[str]) -> None:
        result = self.run_wrapper(argv)
        self.assertEqual(64, result.returncode)
        self.assertFalse(self.marker.exists())
        self.assertNotIn(SECRET, result.stdout + result.stderr)

    def test_valid_oauth_routing_and_prompt_preservation(self) -> None:
        data = self.payload(self.run_wrapper(self.valid_args()))
        self.assertEqual(self.valid_args(), data["argv"])

    def test_environment_scrubbing_and_fixed_settings_path(self) -> None:
        hostile = {key: SECRET for key in SCRUBBED}
        hostile["GEMINI_CLI_SYSTEM_SETTINGS_PATH"] = "/tmp/hostile-settings.json"
        data = self.payload(self.run_wrapper(self.valid_args(), hostile))
        self.assertTrue(all(value is False for value in data["scrubbed_present"].values()))
        self.assertEqual(str(ROOT / "gemini-oauth-settings.json"), data["settings_path"])

    def test_google_selector_normalization(self) -> None:
        data = self.payload(self.run_wrapper(self.valid_args("google/gemini-3.5-flash")))
        self.assertEqual("gemini-3.5-flash", data["argv"][1])

    def test_wrong_auth_refused_without_secret_exposure(self) -> None:
        (self.home / ".gemini" / "settings.json").write_text(
            json.dumps({"security": {"auth": {"selectedType": "api-key"}, "secret": SECRET}}),
            encoding="utf-8",
        )
        self.assert_blocked(self.valid_args())

    def test_missing_credential_cache_metadata_refused(self) -> None:
        (self.home / ".gemini" / "oauth_creds.json").unlink()
        self.assert_blocked(self.valid_args())

    def test_unsafe_arguments_refused(self) -> None:
        unsafe = (
            ["--"], ["--yolo"], ["-y"], ["--approval-mode", "yolo"],
            ["--approval-mode", "default"], ["--settings", "/tmp/x"],
            ["--include-directories", "/tmp"], ["--allowed-mcp-server-names", "x"],
            ["--extensions", "x"], ["--resume", "latest"], ["--worktree", "x"],
            ["--model", "openrouter/google/gemini-3.5-flash"],
            ["--model", "other/gemini-3.5-flash"], ["--model", ""],
            ["--model", "gemini-a", "-m", "gemini-b"], ["--model="],
        )
        for extra in unsafe:
            with self.subTest(extra=extra):
                if self.marker.exists():
                    self.marker.unlink()
                self.assert_blocked(extra)


if __name__ == "__main__":
    unittest.main(verbosity=2)
