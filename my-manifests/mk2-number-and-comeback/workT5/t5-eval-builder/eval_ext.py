#!/usr/bin/env python3
"""Compare Mott raw and Bedrock phrase-picking date interpretation."""

from __future__ import annotations

import importlib.util
import json
import os
import statistics
import sys
import time
import types
from datetime import datetime
from pathlib import Path


RAW_SOURCE = Path(
    "/home/ankit114/repos/ringer/my-manifests/mott-raw-text/work2/"
    "raw-text-authority-v2/bland_gateway_live.py"
)
LLM_SOURCE = Path(
    "/home/ankit114/repos/ringer/my-manifests/mott-llm-intent/work2/"
    "llm-intent-v2/bland_gateway.py"
)


class QueryError(Exception):
    pass


def _no_op(*_args, **_kwargs):
    return None


def install_registry_stub() -> None:
    stub = types.ModuleType("capability_registry")
    stub.QueryError = QueryError
    stub.load_manifest = _no_op
    stub.prepare_query = _no_op
    stub.render_query_result = _no_op
    sys.modules["capability_registry"] = stub


def load_source(name: str, source: Path):
    stubbed = {"capability_registry"}
    while True:
        spec = importlib.util.spec_from_file_location(name, source)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load source module: {source}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
            return module
        except ModuleNotFoundError as exc:
            sys.modules.pop(name, None)
            missing = exc.name
            if not missing or missing in stubbed or len(stubbed) >= 5:
                raise
            if (source.parent / (missing.replace(".", "/") + ".py")).exists():
                raise
            stub = types.ModuleType(missing)
            stub.__getattr__ = lambda _name: _no_op
            sys.modules[missing] = stub
            stubbed.add(missing)


def parse_now(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def conversation(case: dict) -> list[dict]:
    phrase = str(case.get("phrase", ""))
    if case.get("context") == "correction-after-offer":
        offer = (
            f"I have Thursday {case.get('prior_offer')} 10:30 am or ... "
            "Reply 1 or 2 to take one, or tell me another day or time."
        )
        return [
            {"sender": "ASSISTANT", "message": offer},
            {"sender": "USER", "message": phrase},
        ]
    return [{"sender": "USER", "message": phrase}]


def probe_model(llm, candidates: list[str]) -> str | None:
    client = llm._bedrock()
    if client is None:
        return None
    for model_id in candidates:
        try:
            client.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": "Reply only OK"}]}],
                inferenceConfig={"temperature": 0, "maxTokens": 4},
            )
            return model_id
        except Exception:
            continue
    return None


def display_phrase(value: object) -> str:
    return " ".join(str(value or "").split())[:40]


def print_case(index: int, mode: str, case: dict, got: str, latency) -> bool:
    expected = str(case.get("expected", ""))
    ok = got == expected
    ctx = "corr" if case.get("context") == "correction-after-offer" else "plain"
    lat = "NA" if latency is None else str(latency)
    print(
        f"CASE={index} mode={mode} ctx={ctx} got={got} want={expected} "
        f"ok={int(ok)} lat_ms={lat} phrase={display_phrase(case.get('phrase'))}"
    )
    return ok


def run_raw(cases: list[dict], raw) -> None:
    passed = 0
    for index, case in enumerate(cases, 1):
        try:
            now = parse_now(case["now"])
            raw._eastern_today = lambda now=now: now
            resolved, _ = raw.resolve_from_conversation(conversation(case))
            got = resolved if isinstance(resolved, str) else "NONE"
        except Exception as exc:
            got = f"ERROR:{type(exc).__name__}"
        passed += print_case(index, "raw", case, got, None)
    print(f"TOTAL mode=raw model=none ok={passed}/{len(cases)} median_lat_ms=NA")


def run_llm(cases: list[dict], raw, llm, model_id: str) -> None:
    passed = 0
    latencies = []
    for index, case in enumerate(cases, 1):
        latency = None
        started = None
        try:
            now = parse_now(case["now"])
            raw._eastern_today = lambda now=now: now
            llm._eastern_today = lambda now=now: now
            picked = []

            def capture_phrase(value):
                picked.append(str(value or ""))
                return raw.resolve_relative_date(value)

            llm.extract_date_from_text = capture_phrase
            started = time.perf_counter()
            llm.llm_interpret_intent(str(case.get("phrase", "")), now)
            latency = round((time.perf_counter() - started) * 1000)
            latencies.append(latency)
            got = raw.resolve_relative_date(picked[-1]) if picked else None
            got = got if isinstance(got, str) else "NONE"
        except Exception as exc:
            if latency is None and started is not None:
                latency = round((time.perf_counter() - started) * 1000)
                latencies.append(latency)
            got = f"ERROR:{type(exc).__name__}"
        passed += print_case(index, "llm", case, got, latency)
    median = round(statistics.median(latencies)) if latencies else "NA"
    print(
        f"TOTAL mode=llm model={model_id} ok={passed}/{len(cases)} "
        f"median_lat_ms={median}"
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} <eval_cases.json>")
        return 2
    mode = os.environ.get("MODE", "both").strip().lower()
    if mode not in {"raw", "llm", "both"}:
        print("usage: MODE=raw|llm|both eval_ext.py <eval_cases.json>")
        return 2
    try:
        with Path(argv[1]).open(encoding="utf-8") as handle:
            cases = json.load(handle)
        if not isinstance(cases, list):
            raise ValueError("corpus must be a JSON array")
        os.environ["ECP_TENANT_ID"] = "mott"
        install_registry_stub()
        raw = load_source("t5_mott_raw", RAW_SOURCE)
        llm = None
        model_id = None
        if mode in {"llm", "both"}:
            explicit = os.environ.get("ECP_LLM_MODEL_ID", "").strip()
            candidates = [x.strip() for x in os.environ.get("MODEL_CANDIDATES", "").split(",") if x.strip()]
            if not explicit and not candidates:
                raise ValueError("ECP_LLM_MODEL_ID or MODEL_CANDIDATES is required for llm mode")
            if explicit:
                os.environ["ECP_LLM_MODEL_ID"] = explicit
            else:
                os.environ["ECP_LLM_MODEL_ID"] = candidates[0]
            llm = load_source("t5_mott_llm", LLM_SOURCE)
            if candidates and not explicit:
                model_id = probe_model(llm, candidates)
                if model_id is None:
                    print("MODEL_PROBE_FAILED")
                    return 1
                llm._LLM_MODEL_ID = model_id
                print(f"MODEL_USED={model_id}")
            else:
                model_id = explicit
        if mode in {"raw", "both"}:
            run_raw(cases, raw)
        if mode in {"llm", "both"}:
            run_llm(cases, raw, llm, model_id)
        return 0
    except Exception as exc:
        print(f"ERROR:{type(exc).__name__}:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
