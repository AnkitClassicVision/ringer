#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

START = "<!-- RINGER-RENDER-RECEIPT:START -->"
END = "<!-- RINGER-RENDER-RECEIPT:END -->"


def run(cmd):
    print("RUN:", " ".join(map(str, cmd)))
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.stdout.strip(): print(p.stdout.strip())
    if p.returncode:
        raise SystemExit(f"WHY: command failed with exit {p.returncode}: {' '.join(map(str, cmd))}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()
    dest = Path(args.dest).resolve()
    html = dest / "onepager.html"
    pdf = dest / "onepager.pdf"
    png = dest / "onepager-qa.png"
    text = dest / "data/onepager-text.txt"
    runlog = dest / "runlog.md"
    for p in [html, runlog]:
        if not p.is_file():
            print(f"WHY: missing prerequisite {p}")
            return 1
    for p in [pdf, png, text]:
        p.unlink(missing_ok=True)
    run([
        "/usr/bin/google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu",
        "--allow-file-access-from-files", "--no-pdf-header-footer",
        f"--print-to-pdf={pdf}", html.as_uri(),
    ])
    run(["pdftoppm", "-png", "-singlefile", "-r", "150", str(pdf), str(dest / "onepager-qa")])
    run(["pdftotext", "-layout", str(pdf), str(text)])
    body = runlog.read_text(encoding="utf-8", errors="replace")
    receipt = (
        f"{START}\n"
        "## Deterministic render receipt\n\n"
        "- Render status: PASS\n"
        "- Renderer: Google Chrome 150 headless, local-shell via Ringer\n"
        "- PDF: `onepager.pdf`\n"
        "- Visual QA image: `onepager-qa.png` at 150 DPI\n"
        "- Extracted text: `data/onepager-text.txt`\n"
        "- External delivery: none\n"
        f"{END}"
    )
    if START in body and END in body:
        before = body.split(START, 1)[0].rstrip()
        after = body.split(END, 1)[1].lstrip()
        body = before + "\n\n" + receipt + ("\n\n" + after if after else "\n")
    else:
        body = body.rstrip() + "\n\n" + receipt + "\n"
    runlog.write_text(body, encoding="utf-8")
    print(f"PASS: rendered {pdf} and {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
