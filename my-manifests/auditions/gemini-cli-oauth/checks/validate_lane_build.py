#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import tomllib

ROOT = Path.cwd()
WRAPPER = ROOT / "gemini-oauth.sh"
SETTINGS = ROOT / "gemini-oauth-settings.json"
SNIPPET = ROOT / "gemini-engine.toml"
WORKER_TEST = ROOT / "test_gemini_oauth_wrapper.py"

required = (WRAPPER, SETTINGS, SNIPPET, WORKER_TEST)
for path in required:
    assert path.is_file() and path.stat().st_size > 0, f"missing or empty: {path.name}"

syntax = subprocess.run(["bash", "-n", str(WRAPPER)], text=True, capture_output=True)
assert syntax.returncode == 0, f"bash syntax failed: {syntax.stderr}"

settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
assert settings["security"]["auth"]["enforcedType"] == "oauth-personal", "OAuth must be enforced"
assert settings["admin"]["secureModeEnabled"] is True, "secure mode must be on"
assert settings["admin"]["extensions"]["enabled"] is False, "extensions must be disabled"
assert settings["admin"]["mcp"]["enabled"] is False, "MCP must be disabled"
assert settings["admin"]["skills"]["enabled"] is False, "skills must be disabled"
assert settings["skills"]["enabled"] is False, "skills discovery must be disabled"
assert settings["hooksConfig"]["enabled"] is False, "hooks must be disabled"
assert settings["experimental"]["enableAgents"] is False, "subagents must be disabled"
assert settings["telemetry"]["enabled"] is False, "telemetry must be disabled"
assert settings["context"]["fileName"] == ".ringer-no-context.md", "ambient GEMINI.md loading must be neutralized"

snippet = tomllib.loads(SNIPPET.read_text(encoding="utf-8"))
engine = snippet["engines"]["gemini"]
assert engine["model_default"] == "gemini-3.5-flash"
assert engine["auth_routing_trusted"] is True
assert engine["bin"].endswith("/engines/gemini-oauth.sh")
args = engine["args_template"]
for needed in ("{model}", "{spec}", "{engine_args}", "--approval-mode", "auto_edit", "--output-format", "json"):
    assert needed in args, f"engine args missing {needed}"

worker_test = subprocess.run(["python3", str(WORKER_TEST)], text=True, capture_output=True)
assert worker_test.returncode == 0, f"worker test failed:\n{worker_test.stdout}\n{worker_test.stderr}"

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    home = root / "home"
    bindir = root / "bin"
    home_settings = home / ".gemini" / "settings.json"
    home_settings.parent.mkdir(parents=True)
    bindir.mkdir()
    home_settings.write_text(json.dumps({"security": {"auth": {"selectedType": "oauth-personal"}}}), encoding="utf-8")
    (home / ".gemini" / "oauth_creds.json").write_text("{}", encoding="utf-8")
    marker = root / "invoked"
    fake = bindir / "gemini"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "open(os.environ['FAKE_MARKER'], 'w').write('yes')\n"
        "keys=['GEMINI_API_KEY','GOOGLE_API_KEY','GOOGLE_APPLICATION_CREDENTIALS','GOOGLE_GENAI_USE_VERTEXAI','GOOGLE_GEMINI_BASE_URL','GEMINI_CLI_HOME']\n"
        "print(json.dumps({'argv':sys.argv[1:],'present':{k:k in os.environ for k in keys},'system_settings':os.environ.get('GEMINI_CLI_SYSTEM_SETTINGS_PATH')}))\n",
        encoding="utf-8",
    )
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "PATH": f"{bindir}{os.pathsep}{env.get('PATH','')}",
        "FAKE_MARKER": str(marker),
        "GEMINI_API_KEY": "sentinel",
        "GOOGLE_API_KEY": "sentinel",
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/sentinel.json",
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
        "GOOGLE_GEMINI_BASE_URL": "https://invalid.example",
        "GEMINI_CLI_HOME": "/tmp/alternate-gemini-home",
        "GEMINI_CLI_SYSTEM_SETTINGS_PATH": "/tmp/alternate-settings.json",
    })
    ok = subprocess.run(
        [str(WRAPPER), "-m", "google/gemini-3.5-flash", "--approval-mode", "auto_edit", "--output-format", "json", "-p", "write the requested file"],
        text=True, capture_output=True, env=env,
    )
    assert ok.returncode == 0, f"valid OAuth invocation failed: {ok.stderr}"
    payload = json.loads(ok.stdout)
    assert payload["argv"] == ["-m", "gemini-3.5-flash", "--approval-mode", "auto_edit", "--output-format", "json", "-p", "write the requested file"], payload["argv"]
    assert not any(payload["present"].values()), payload["present"]
    assert Path(payload["system_settings"]).resolve() == SETTINGS.resolve(), payload["system_settings"]

    marker.unlink()
    home_settings.write_text(json.dumps({"security": {"auth": {"selectedType": "gemini-api-key"}}}), encoding="utf-8")
    bad_auth = subprocess.run([str(WRAPPER), "-m", "gemini-3.5-flash", "-p", "x"], text=True, capture_output=True, env=env)
    assert bad_auth.returncode == 64, f"wrong auth was not blocked: {bad_auth.returncode}"
    assert not marker.exists(), "wrong auth invoked Gemini"

    home_settings.write_text(json.dumps({"security": {"auth": {"selectedType": "oauth-personal"}}}), encoding="utf-8")
    for bad_args in (
        ["-m", "openrouter/google/gemini-3.5-flash", "-p", "x"],
        ["-m", "gemini-3.5-flash", "--yolo", "-p", "x"],
        ["-m", "gemini-3.5-flash", "--approval-mode", "yolo", "-p", "x"],
        ["-m", "gemini-3.5-flash", "--extensions", "example", "-p", "x"],
        ["-m", "gemini-3.5-flash", "--include-directories", "/tmp", "-p", "x"],
    ):
        blocked = subprocess.run([str(WRAPPER), *bad_args], text=True, capture_output=True, env=env)
        assert blocked.returncode == 64, f"unsafe route not blocked: {bad_args} -> {blocked.returncode}"
        assert not marker.exists(), f"unsafe route invoked Gemini: {bad_args}"

print("GEMINI_OAUTH_LANE_BUILD_OK")
