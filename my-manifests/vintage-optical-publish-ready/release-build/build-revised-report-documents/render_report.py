#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def run(cmd):
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(map(str, cmd))}\n{result.stdout}\n{result.stderr}")
    return result.stdout

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def page_info(pdf):
    info = run(["pdfinfo", str(pdf)])
    values = {}
    for line in info.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return int(values["Pages"]), values.get("Page size", "")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    root = args.dir.resolve()
    if not root.is_dir():
        raise RuntimeError(f"Build directory does not exist: {root}")
    receipt = (args.receipt if args.receipt else root / "render_receipt.json").resolve()
    if root not in receipt.parents:
        raise RuntimeError("--receipt must remain inside --dir")
    sources = [root / "onepager.html", root / "number-explainer.html"]
    for source in sources:
        if not source.is_file() or not source.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"Missing or blank source: {source.name}")
    stale_files = [
        root / "onepager.pdf", root / "number-explainer.pdf",
        root / "onepager.txt", root / "number-explainer.txt", receipt,
    ]
    for path in stale_files:
        if path.exists():
            path.unlink()
    for directory in [root / "page-images/onepager", root / "page-images/explainer"]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    chrome = "/usr/bin/google-chrome"
    common = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
              "--allow-file-access-from-files", "--no-pdf-header-footer"]
    for source, pdf in zip(sources, [root / "onepager.pdf", root / "number-explainer.pdf"]):
        run(common + [f"--print-to-pdf={pdf}", source.as_uri()])
        if not pdf.is_file() or pdf.stat().st_size < 1000:
            raise RuntimeError(f"Missing, stale, or blank PDF: {pdf.name}")
        if pdf.stat().st_mtime_ns <= source.stat().st_mtime_ns:
            raise RuntimeError(f"Rendered PDF is not newer than its HTML source: {pdf.name}")
    one_pages, one_size = page_info(root / "onepager.pdf")
    exp_pages, exp_size = page_info(root / "number-explainer.pdf")
    if one_pages != 1 or "612 x 792" not in one_size:
        raise RuntimeError(f"One-pager must be exactly one Letter page; got {one_pages}, {one_size}")
    if exp_pages < 8 or "612 x 792" not in exp_size:
        raise RuntimeError(f"Explainer must be at least 8 Letter pages; got {exp_pages}, {exp_size}")
    run(["pdftoppm", "-png", "-r", "150", str(root / "onepager.pdf"), str(root / "page-images/onepager/page")])
    run(["pdftoppm", "-png", "-r", "150", str(root / "number-explainer.pdf"), str(root / "page-images/explainer/page")])
    run(["pdftotext", str(root / "onepager.pdf"), str(root / "onepager.txt")])
    run(["pdftotext", str(root / "number-explainer.pdf"), str(root / "number-explainer.txt")])
    for text_path in [root / "onepager.txt", root / "number-explainer.txt"]:
        if not text_path.read_text(encoding="utf-8", errors="replace").strip():
            raise RuntimeError(f"Blank text extract: {text_path.name}")
    one_pngs = sorted((root / "page-images/onepager").glob("*.png"))
    exp_pngs = sorted((root / "page-images/explainer").glob("*.png"))
    if len(one_pngs) != one_pages or len(exp_pngs) != exp_pages or any(p.stat().st_size == 0 for p in one_pngs + exp_pngs):
        raise RuntimeError("Missing or blank page image output")
    timestamp = datetime.now(timezone.utc).isoformat()
    data = {
        "rendered_at_utc": timestamp,
        "network_used": False,
        "onepager": {"pages": one_pages, "page_size": one_size, "sha256": digest(root / "onepager.pdf")},
        "number_explainer": {"pages": exp_pages, "page_size": exp_size, "sha256": digest(root / "number-explainer.pdf")},
        "page_images": {"onepager": len(one_pngs), "explainer": len(exp_pngs)},
        "status": "PASS",
    }
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    with (root / "runlog.md").open("a", encoding="utf-8") as stream:
        stream.write(f"\n## Render result\n\n- rendered_at_utc: {timestamp}\n- status: PASS\n- onepager_pages: {one_pages}\n- explainer_pages: {exp_pages}\n- render_receipt: {receipt.name}\n")
    print(f"PASS: onepager={one_pages} Letter page; explainer={exp_pages} Letter pages")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
