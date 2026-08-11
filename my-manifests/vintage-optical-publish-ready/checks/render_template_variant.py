#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    root = args.dir.resolve()
    source = root / "template-framed-onepager.html"
    pdf = root / "template-framed-onepager.pdf"
    text_path = root / "template-framed-onepager.txt"
    image_dir = root / "page-images/template-framed-onepager"
    receipt = (args.receipt or root / "template-render-receipt.json").resolve()
    if root not in receipt.parents:
        raise RuntimeError("receipt must remain inside report directory")
    if not source.is_file() or source.stat().st_size < 100000:
        raise RuntimeError("template-framed source missing, blank, or lacks embedded logo")
    for path in (pdf, text_path, receipt):
        if path.exists():
            path.unlink()
    if image_dir.exists():
        shutil.rmtree(image_dir)
    image_dir.mkdir(parents=True)
    chrome = "/usr/bin/google-chrome"
    run([
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--allow-file-access-from-files", "--no-pdf-header-footer",
        f"--print-to-pdf={pdf}", source.as_uri(),
    ])
    if not pdf.is_file() or pdf.stat().st_size < 1000 or pdf.stat().st_mtime_ns <= source.stat().st_mtime_ns:
        raise RuntimeError("template-framed PDF is missing, blank, or stale")
    info = run(["pdfinfo", str(pdf)])
    if not re_search(r"^Pages:\s+1$", info) or "612 x 792" not in info:
        raise RuntimeError("template-framed PDF is not exactly one Letter page")
    run(["pdftoppm", "-png", "-r", "150", str(pdf), str(image_dir / "page")])
    run(["pdftotext", str(pdf), str(text_path)])
    images = sorted(image_dir.glob("*.png"))
    if len(images) != 1 or images[0].stat().st_size < 5000:
        raise RuntimeError("template-framed page image missing or implausibly small")
    if not text_path.read_text(encoding="utf-8", errors="replace").strip():
        raise RuntimeError("template-framed PDF text extract is blank")
    timestamp = datetime.now(timezone.utc).isoformat()
    data = {
        "rendered_at_utc": timestamp,
        "network_used": False,
        "source": {"file": source.name, "sha256": digest(source)},
        "pdf": {"file": pdf.name, "pages": 1, "page_size": "612 x 792 pts (letter)", "sha256": digest(pdf)},
        "page_images": 1,
        "status": "PASS",
    }
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    with (root / "runlog.md").open("a", encoding="utf-8") as stream:
        stream.write(
            f"\n## Template-framed render result\n\n- rendered_at_utc: {timestamp}\n"
            f"- status: PASS\n- pages: 1\n- render_receipt: {receipt.name}\n"
        )
    print("PASS: template-framed one-pager rendered as one fresh Letter page")
    return 0


def re_search(pattern: str, text: str) -> bool:
    import re
    return re.search(pattern, text, re.M) is not None


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
