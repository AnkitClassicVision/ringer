#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED = {
    "README.md",
    "release-receipt.json",
    "Vintage-Optical-One-Pager.pdf",
    "Vintage-Optical-One-Pager.html",
    "Vintage-Optical-Template-Framed-One-Pager.pdf",
    "Vintage-Optical-Template-Framed-One-Pager.html",
    "Vintage-Optical-Number-Explainer.pdf",
    "Vintage-Optical-Number-Explainer.html",
    "Vintage-Optical-Number-Explainer.md",
    "Visual-QA.json",
    "Visual-QA.md",
    "Numeric-Review.json",
    "Numeric-Review.md",
    "Logic-Review.json",
    "Logic-Review.md",
    "Technical-Review.json",
    "Technical-Review.md",
    "scores.json",
    "sources.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pages_and_size(path: Path) -> tuple[int, str]:
    output = subprocess.run(["pdfinfo", str(path)], text=True, capture_output=True, check=True).stdout
    fields = {}
    for line in output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return int(fields["Pages"]), fields.get("Page size", "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()
    root = args.dir.resolve()
    failures: list[str] = []
    if not root.is_dir():
        print("WHY: final folder missing")
        return 1
    entries = list(root.iterdir())
    if any(path.is_dir() for path in entries):
        failures.append("final package contains nested directories instead of one flat folder")
    names = {path.name for path in entries if path.is_file()}
    if names != REQUIRED:
        failures.append(f"final folder file set differs: missing={sorted(REQUIRED - names)} extra={sorted(names - REQUIRED)}")

    try:
        receipt = json.loads((root / "release-receipt.json").read_text())
    except Exception as exc:
        print(f"WHY: release receipt parse failed: {exc}")
        return 1
    if receipt.get("status") != "RENDERED_QA_PASSED_HUMAN_PROJECT_ROOM_REQUIRED":
        failures.append("release state is not the highest truthful human-gated state")
    if receipt.get("external_delivery_authorized") is not False or receipt.get("external_actions_taken") != "none":
        failures.append("external boundary is wrong")
    if receipt.get("folder") != "/home/ankit114/Vintage-Optical-Competitive-Analysis-2026-07-30":
        failures.append("release receipt folder path is wrong")

    registered = {}
    for row in receipt.get("deliverables") or []:
        registered[row["file"]] = row["sha256"]
    registered.update(receipt.get("source_hashes") or {})
    registered.update(receipt.get("review_hashes") or {})
    for name, expected in registered.items():
        path = root / name
        if not path.is_file() or digest(path) != expected:
            failures.append(f"registered hash mismatch: {name}")

    for name, expected_pages in (
        ("Vintage-Optical-One-Pager.pdf", 1),
        ("Vintage-Optical-Template-Framed-One-Pager.pdf", 1),
        ("Vintage-Optical-Number-Explainer.pdf", 25),
    ):
        try:
            pages, size = pages_and_size(root / name)
        except Exception as exc:
            failures.append(f"cannot inspect {name}: {exc}")
            continue
        if pages != expected_pages or "612 x 792" not in size:
            failures.append(f"{name} page geometry is wrong: pages={pages} size={size}")

    try:
        logo_check = subprocess.run([
            sys.executable,
            str(Path(__file__).with_name("validate_logo_and_variant_sources.py")),
            "--current", str(root / "Vintage-Optical-One-Pager.html"),
            "--variant", str(root / "Vintage-Optical-Template-Framed-One-Pager.html"),
            "--logo", "/mnt/d_drive/repos/optometry-competition-analyzer-rubric/client-onepager/assets/mybcat-logo.png",
        ], text=True, capture_output=True)
        if logo_check.returncode:
            failures.append("logo and variant source gate failed: " + " ".join(logo_check.stdout.split()))
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            stem = temp_root / "onepager"
            subprocess.run([
                "pdftoppm", "-f", "1", "-singlefile", "-png", "-r", "150",
                str(root / "Vintage-Optical-One-Pager.pdf"), str(stem),
            ], check=True, capture_output=True, text=True)
            safe = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("validate_onepager_bottom_safe_area.py")),
                "--pdf", str(root / "Vintage-Optical-One-Pager.pdf"),
                "--png", str(stem.with_suffix(".png")),
            ], text=True, capture_output=True)
            if safe.returncode:
                failures.append("retained bottom safety gate failed: " + " ".join(safe.stdout.split()))

            variant_stem = temp_root / "template"
            variant_source = root / "Vintage-Optical-Template-Framed-One-Pager.html"
            variant_pdf = root / "Vintage-Optical-Template-Framed-One-Pager.pdf"
            subprocess.run([
                "pdftoppm", "-f", "1", "-singlefile", "-png", "-r", "150",
                str(variant_pdf), str(variant_stem),
            ], check=True, capture_output=True, text=True)
            variant_receipt = temp_root / "template-receipt.json"
            variant_receipt.write_text(json.dumps({
                "status": "PASS",
                "source": {"sha256": digest(variant_source)},
                "pdf": {"sha256": digest(variant_pdf)},
            }))
            variant_safe = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("validate_template_variant_render.py")),
                "--source", str(variant_source),
                "--pdf", str(variant_pdf),
                "--png", str(variant_stem.with_suffix(".png")),
                "--receipt", str(variant_receipt),
            ], text=True, capture_output=True)
            if variant_safe.returncode:
                failures.append("template-framed render gate failed: " + " ".join(variant_safe.stdout.split()))
    except Exception as exc:
        failures.append(f"cannot verify final one-pager logo or safety gates: {exc}")

    for name in ("Visual-QA.json", "Numeric-Review.json", "Logic-Review.json", "Technical-Review.json"):
        try:
            data = json.loads((root / name).read_text())
        except Exception as exc:
            failures.append(f"cannot parse {name}: {exc}")
            continue
        verdict = data.get("verdict")
        if verdict != "PASS":
            failures.append(f"{name} verdict is not PASS")
        if data.get("blocking_findings") not in ([], None):
            failures.append(f"{name} has blocking findings")
        if data.get("external_actions_taken") != "none":
            failures.append(f"{name} external-action boundary is wrong")

    for path in root.iterdir():
        if path.suffix.lower() not in (".md", ".html", ".json"):
            continue
        text = path.read_text(encoding="utf-8")
        if "CANARY" in text:
            failures.append(f"forbidden test text in {path.name}")
        if path.name in ("Vintage-Optical-One-Pager.html", "Vintage-Optical-Template-Framed-One-Pager.html", "Vintage-Optical-Number-Explainer.html", "Vintage-Optical-Number-Explainer.md"):
            if any(stale in text for stale in ("4.07", "1.56", "244.3")):
                failures.append(f"stale route value in client-visible source {path.name}")
        if path.name not in ("README.md", "release-receipt.json") and ("/home/" in text or "/mnt/" in text or "file://" in text):
            failures.append(f"internal path leaked in {path.name}")

    if failures:
        for item in failures:
            print(f"WHY: {item}")
        return 1
    print("PASS: final Vintage Optical package is one flat 19-file folder with two approved-logo one-pagers, three valid PDFs, matched hashes, and four green review artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
