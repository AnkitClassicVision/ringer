#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_builder(path: Path):
    spec = importlib.util.spec_from_file_location("report_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load report builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    root = args.report_dir.resolve()
    receipt = args.receipt.resolve()
    if not candidate.is_file() or not root.is_dir():
        raise SystemExit("FAIL: candidate or report directory missing")
    if root in candidate.parents:
        raise SystemExit("FAIL: candidate must come from the isolated redesign task")

    target = root / "onepager.html"
    if not target.is_file():
        raise SystemExit("FAIL: report onepager.html missing")
    before_hash = digest(target)
    candidate_hash = digest(candidate)
    history = root / "history"
    history.mkdir(exist_ok=True)
    backup = history / f"onepager-before-gauge-{before_hash[:12]}.html"
    if not backup.exists():
        shutil.copy2(target, backup)
    shutil.copy2(candidate, target)
    if digest(target) != candidate_hash:
        raise SystemExit("FAIL: candidate copy hash mismatch")

    for name in ("visual-qa.json", "visual-qa.md"):
        path = root / name
        if path.exists():
            stale = history / f"{path.stem}-before-gauge-{before_hash[:12]}{path.suffix}"
            if not stale.exists():
                shutil.copy2(path, stale)
            path.unlink()
    contact = root / "page-images" / "contact-sheets"
    if contact.exists():
        shutil.rmtree(contact)

    builder = load_builder(root / "build_report.py")
    artifacts = {
        "onepager.html": (root / "onepager.html").read_text(encoding="utf-8"),
        "number-explainer.md": (root / "number-explainer.md").read_text(encoding="utf-8"),
        "number-explainer.html": (root / "number-explainer.html").read_text(encoding="utf-8"),
    }
    number_inventory = builder.build_number_inventory(artifacts)
    (root / "number_inventory.json").write_text(json.dumps(number_inventory, indent=2) + "\n", encoding="utf-8")

    runlog = root / "runlog.md"
    text = runlog.read_text(encoding="utf-8")
    for old in ("- render: render complete", "- render: render pending"):
        text = text.replace(old, "- render: render pending")
    for old in ("- visual_qa: visual QA PASS", "- visual_qa: visual QA pending"):
        text = text.replace(old, "- visual_qa: visual QA pending")
    text += (
        "\n## Gauge-template redesign\n\n"
        f"- candidate_sha256: `{candidate_hash}`\n"
        "- template_spine: MyBCAT sample one-pager dark hero, circular gauge, colored meters, numbered zones\n"
        "- external_actions_taken: none\n"
        "- render: pending after source integration\n"
    )
    runlog.write_text(text, encoding="utf-8")

    data = {
        "status": "PASS",
        "onepager_before_sha256": before_hash,
        "onepager_after_sha256": candidate_hash,
        "backup": backup.name,
        "number_inventory_entries": len(number_inventory["entries"]),
        "substantive_lineage_coverage_percent": number_inventory["substantive_lineage_coverage_percent"],
        "unexplained_substantive_number_count": number_inventory["unexplained_substantive_number_count"],
        "visual_qa_reset": True,
        "external_actions_taken": "none",
    }
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("PASS: gauge-template one-pager integrated; inventory rebuilt; render and visual QA reset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
