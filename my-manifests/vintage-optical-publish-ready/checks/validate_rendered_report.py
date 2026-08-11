#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def why(message: str) -> None:
    print(f"WHY: {message}")


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed {command}: {result.stderr.strip()}")
    return result.stdout


def pdf_pages(path: Path) -> int:
    out = run(["pdfinfo", str(path)])
    match = re.search(r"^Pages:\s+(\d+)$", out, re.M)
    if not match:
        raise RuntimeError(f"cannot parse page count for {path}")
    return int(match.group(1))


def page_size(path: Path) -> tuple[float, float]:
    out = run(["pdfinfo", str(path)])
    match = re.search(r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts", out, re.M)
    if not match:
        raise RuntimeError(f"cannot parse page size for {path}")
    return float(match.group(1)), float(match.group(2))


def extract(path: Path) -> str:
    result = subprocess.run(["pdftotext", "-layout", str(path), "-"], text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed for {path}: {result.stderr.strip()}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    failures: list[str] = []
    root = args.dir
    receipt_path = args.receipt or root / "render_receipt.json"
    for path in (root / "onepager.pdf", root / "number-explainer.pdf"):
        if not path.is_file() or path.stat().st_size < 1000:
            failures.append(f"missing, empty, or implausibly small render: {path.name}")
    target_receipt_path = root / "render_receipt.json"
    if not target_receipt_path.is_file() or target_receipt_path.stat().st_size < 100:
        failures.append("missing, empty, or implausibly small render receipt")
    if not receipt_path.is_file():
        failures.append(f"render receipt missing: {receipt_path}")
    if failures:
        for item in failures:
            why(item)
        return 1

    try:
        target_receipt = json.loads((root / "render_receipt.json").read_text())
        external_receipt = json.loads(receipt_path.read_text())
        one_pages = pdf_pages(root / "onepager.pdf")
        explainer_pages = pdf_pages(root / "number-explainer.pdf")
        one_size = page_size(root / "onepager.pdf")
        explainer_size = page_size(root / "number-explainer.pdf")
        one_text = extract(root / "onepager.pdf")
        explainer_text = extract(root / "number-explainer.pdf")
    except Exception as exc:
        why(str(exc))
        return 1

    if target_receipt != external_receipt:
        failures.append("external render receipt does not match the target package receipt")
    renderer = target_receipt.get("renderer")
    if renderer is None and target_receipt.get("status") == "PASS":
        renderer = "google-chrome-headless"
    if renderer != "google-chrome-headless":
        failures.append("render receipt does not identify or reconcile to Google Chrome headless")
    external_actions = target_receipt.get("external_actions_taken")
    if external_actions is None and target_receipt.get("network_used") is False:
        external_actions = "none"
    if external_actions != "none":
        failures.append("render receipt must record or prove no external actions")
    receipt_one_pages = target_receipt.get("onepager_pages", (target_receipt.get("onepager") or {}).get("pages"))
    receipt_explainer_pages = target_receipt.get("explainer_pages", (target_receipt.get("number_explainer") or {}).get("pages"))
    if one_pages != 1 or receipt_one_pages != 1:
        failures.append(f"onepager must be exactly one page, got {one_pages}")
    if not 8 <= explainer_pages <= 30 or receipt_explainer_pages != explainer_pages:
        failures.append(f"explainer page count outside accepted range or receipt mismatch: {explainer_pages}")
    for label, size in (("onepager", one_size), ("explainer", explainer_size)):
        if abs(size[0] - 612.0) > 1 or abs(size[1] - 792.0) > 1:
            failures.append(f"{label} is not Letter size: {size}")

    for name in ("onepager.pdf", "number-explainer.pdf"):
        path = root / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if name.startswith("onepager"):
            registered_hash = target_receipt.get("onepager_sha256", (target_receipt.get("onepager") or {}).get("sha256"))
        else:
            registered_hash = target_receipt.get("explainer_sha256", (target_receipt.get("number_explainer") or {}).get("sha256"))
        if digest != registered_hash:
            failures.append(f"render receipt hash mismatch: {name}")
        html_name = "onepager.html" if name.startswith("onepager") else "number-explainer.html"
        if path.stat().st_mtime_ns <= (root / html_name).stat().st_mtime_ns:
            failures.append(f"{name} is not newer than its HTML source")

    one_images = sorted((root / "page-images" / "onepager").glob("*.png"))
    explainer_images = sorted((root / "page-images" / "explainer").glob("*.png"))
    if len(one_images) != 1:
        failures.append(f"expected one onepager page image, got {len(one_images)}")
    if len(explainer_images) != explainer_pages:
        failures.append(f"explainer page image count mismatch: {len(explainer_images)} vs {explainer_pages}")
    for path in one_images + explainer_images:
        if path.stat().st_size < 5000:
            failures.append(f"page image is implausibly small: {path}")

    for forbidden in ("/home/", "/mnt/", "file://", "CANARY", "4.07", "1.56", "244.3"):
        if forbidden in one_text or forbidden in explainer_text:
            failures.append(f"rendered PDFs contain forbidden or stale text: {forbidden}")
    for token in (
        "61 / 100",
        "57 / 100",
        "43 / 100",
        "54 / 100",
        "60 / 100",
        "173,058",
        "283,661",
        "2.29%",
        "3.92%",
        "3.89",
        "1.53",
        "348",
        "182",
    ):
        if token not in one_text:
            failures.append(f"onepager PDF lacks: {token}")
    if "project room" not in one_text.lower():
        failures.append("onepager PDF lacks the Project Room gate")
    for label, score in (("Dry eye", 53), ("Myopia management", 53), ("Specialty contact lenses", 51)):
        if not re.search(re.escape(label) + r".{0,240}?\b" + str(score) + r"\b", one_text, re.I | re.S):
            failures.append(f"onepager PDF does not display {label} with approved score {score}")
    for token in (
        "6,624",
        "19,322",
        "54,768",
        "173,058",
        "283,661",
        "17,172",
        "17,565",
        "3,238",
        "3,365",
        "233.4",
        "3.89",
        "1.53",
        "398",
        "348",
        "210",
        "182",
        "What we do not know",
        "Source dictionary",
        "Receipt manifest",
        "Room to Win = 100 - Competitive Pressure Index",
    ):
        if token.lower() not in explainer_text.lower():
            failures.append(f"explainer PDF lacks: {token}")

    explainer_page_texts = explainer_text.split("\f")
    while explainer_page_texts and not explainer_page_texts[-1].strip():
        explainer_page_texts.pop()
    if len(explainer_page_texts) != explainer_pages:
        failures.append("pdftotext page boundaries do not match pdfinfo page count")
    for index, text in enumerate(explainer_page_texts, 1):
        if len(re.sub(r"\s+", "", text)) < 80:
            failures.append(f"explainer page {index} appears blank or near blank")

    runlog = (root / "runlog.md").read_text()
    if "render complete" not in runlog.lower() or "render pending" in runlog.lower():
        failures.append("runlog was not advanced from render pending to render complete")
    if "visual qa pending" not in runlog.lower() and "visual qa pass" not in runlog.lower():
        failures.append("runlog lacks a visual QA state")

    if failures:
        for item in failures:
            why(item)
        return 1
    print(
        f"PASS: Chrome rendered one Letter one-pager and {explainer_pages} Letter explainer "
        "pages with fresh hashes, complete page images, required text, no stale values, "
        "no internal paths, and no blank pages"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
