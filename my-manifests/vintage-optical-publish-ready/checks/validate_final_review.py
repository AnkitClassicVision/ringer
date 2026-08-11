#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

EXPECTED_SCORES = {
    "Market Demand-Supply": (61, 60.50),
    "Competitive Pressure Index": (57, 56.75),
    "Room to Win": (43, 43.00),
    "Practice Competitiveness": (61, 60.50),
    "Client Opportunity": (54, 54.45),
    "Digital Presence": (60, 59.75),
    "Dry eye / ocular surface": (53, 53.00),
    "Myopia management": (53, 53.00),
    "Specialty contact lenses": (51, 50.75),
}


def why(message: str) -> None:
    print(f"WHY: {message}")


def execute(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, text=True, capture_output=True, env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return result.returncode, (result.stdout + result.stderr).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("numeric", "logic", "technical"), required=True)
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--render-receipt", type=Path, required=True)
    parser.add_argument("--visual-receipt", type=Path, required=True)
    args = parser.parse_args()
    failures: list[str] = []

    json_path = args.dir / f"{args.kind}-review.json"
    md_path = args.dir / f"{args.kind}-review.md"
    for path in (json_path, md_path):
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing or empty review artifact: {path.name}")
    if failures:
        for item in failures:
            why(item)
        return 1

    try:
        review = json.loads(json_path.read_text())
        scores = json.loads((args.report_root / "scores.json").read_text())
        render = json.loads(args.render_receipt.read_text())
        visual = json.loads(args.visual_receipt.read_text())
    except Exception as exc:
        why(f"parse failed: {exc}")
        return 1

    if review.get("review_type") != args.kind:
        failures.append("review_type does not match the declared lane")
    if review.get("verdict") != "PASS":
        failures.append("review verdict must be PASS")
    if review.get("external_actions_taken") != "none":
        failures.append("review must record no external actions")
    if review.get("blocking_findings") not in ([], None):
        failures.append("review contains blocking findings")
    if not review.get("reviewed_artifact_hashes"):
        failures.append("review lacks artifact hashes")
    else:
        expected_hashes = {
            "onepager_pdf": hashlib.sha256((args.report_root / "onepager.pdf").read_bytes()).hexdigest(),
            "number_explainer_pdf": hashlib.sha256((args.report_root / "number-explainer.pdf").read_bytes()).hexdigest(),
            "scores_json": hashlib.sha256((args.report_root / "scores.json").read_bytes()).hexdigest(),
        }
        template_pdf = args.report_root / "template-framed-onepager.pdf"
        if template_pdf.is_file():
            expected_hashes["template_framed_onepager_pdf"] = hashlib.sha256(template_pdf.read_bytes()).hexdigest()
        for key, value in expected_hashes.items():
            if review["reviewed_artifact_hashes"].get(key) != value:
                failures.append(f"reviewed hash mismatch: {key}")

    code, output = execute([
        "python3",
        "/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_report_build_sources.py",
        "--dir",
        str(args.report_root),
    ])
    if code != 0:
        failures.append(f"source validator failed during fresh review: {output}")
    code, output = execute([
        "python3",
        "/home/ankit114/repos/ringer/my-manifests/vintage-optical-publish-ready/checks/validate_rendered_report.py",
        "--dir",
        str(args.report_root),
        "--receipt",
        str(args.render_receipt),
    ])
    if code != 0:
        failures.append(f"render validator failed during fresh review: {output}")
    if visual.get("verdict") != "PASS" or visual.get("pages_inspected") != visual.get("expected_pages"):
        failures.append("visual QA receipt is missing, incomplete, or not PASS")

    score_rows = scores.get("scores") or {}
    if args.kind == "numeric":
        if review.get("substantive_lineage_coverage_percent") != 100:
            failures.append("numeric review does not verify 100% substantive lineage")
        if review.get("unexplained_substantive_number_count") != 0:
            failures.append("numeric review reports unexplained substantive numbers")
        reviewed_scores = {row.get("score_name"): row for row in review.get("score_checks") or []}
        if set(reviewed_scores) != set(EXPECTED_SCORES):
            failures.append("numeric review does not cover all nine scores")
        for name, (display, full) in EXPECTED_SCORES.items():
            row = reviewed_scores.get(name) or {}
            if row.get("display_score") != display or row.get("full_precision_total") != full or row.get("result") != "PASS":
                failures.append(f"numeric review score check failed: {name}")
        required_facts = {
            "five_window_catchment",
            "population_growth",
            "school_enrollment_growth",
            "focus_route",
            "google_review_sample",
            "birdeye_discrepancies",
            "candidate_supply_counts",
            "null_denominators",
        }
        fact_results = {row.get("fact_group"): row.get("result") for row in review.get("fact_checks") or []}
        for fact in required_facts:
            if fact_results.get(fact) != "PASS":
                failures.append(f"numeric review lacks PASS fact group: {fact}")
        if review.get("cross_document_consistency") != "PASS":
            failures.append("numeric review lacks cross-document consistency PASS")

    elif args.kind == "logic":
        if review.get("directionality_guard") != "Room to Win = 100 - Competitive Pressure Index":
            failures.append("logic review lacks exact directionality guard")
        if review.get("room_to_win_check") != "PASS":
            failures.append("logic review did not pass Room-to-Win inversion")
        nulls = set(review.get("preserved_nulls") or [])
        for field in ("canonical_full_vdu", "canonical_office_count", "rank_grid", "complete_provider_entity_dedupe", "cross_platform_review_total"):
            if field not in nulls:
                failures.append(f"logic review does not preserve null: {field}")
        logic_checks = {row.get("check"): row.get("result") for row in review.get("logic_checks") or []}
        for check in (
            "candidate_supply_not_canonicalized",
            "review_sources_separated",
            "growth_not_forecast",
            "routes_not_patient_choice",
            "unknown_not_zero",
            "three_fix_cards_only",
            "internal_only_boundary",
            "score_band_changes_evidence_supported",
        ):
            if logic_checks.get(check) != "PASS":
                failures.append(f"logic review lacks PASS check: {check}")
        if review.get("fix_card_count") != 3:
            failures.append("logic review must verify exactly three Fix Cards")
        if (args.report_root / "template-framed-onepager.pdf").is_file():
            if review.get("template_framed_fix_card_count") != 3:
                failures.append("logic review must verify exactly three template-framed Fix Cards")
            if logic_checks.get("template_framed_claim_boundary") != "PASS":
                failures.append("logic review lacks PASS check: template_framed_claim_boundary")

    else:
        if review.get("highest_truthful_state") != "RENDERED_QA_PASSED_HUMAN_PROJECT_ROOM_REQUIRED":
            failures.append("technical review overstates or understates the highest truthful state")
        if review.get("external_delivery_authorized") is not False:
            failures.append("technical review must not authorize external delivery")
        rendered_explainer_pages = render.get("explainer_pages", (render.get("number_explainer") or {}).get("pages"))
        if review.get("onepager_pages") != 1 or review.get("explainer_pages") != rendered_explainer_pages:
            failures.append("technical review page counts do not match render receipt")
        template_present = (args.report_root / "template-framed-onepager.pdf").is_file()
        if template_present:
            if review.get("template_framed_onepager_pages") != 1:
                failures.append("technical review does not verify the template-framed one-pager page count")
            if review.get("approved_logo_sha256") != "1e969dcafdefe20f809f4a393b6be0ca41a226ad5efeaa207d683a6c0fa36942":
                failures.append("technical review does not bind the approved MyBCAT logo hash")
            if review.get("embedded_logo_byte_match") is not True:
                failures.append("technical review does not verify embedded logo byte matches")
        if review.get("internal_path_leak_count") != 0 or review.get("stale_route_value_count") != 0:
            failures.append("technical review found path leaks or stale route values")
        if review.get("receipt_integrity") != "PASS" or review.get("visual_qa") != "PASS":
            failures.append("technical review lacks receipt or visual QA PASS")
        required_files = {
            "onepager.html",
            "onepager.pdf",
            "number-explainer.md",
            "number-explainer.html",
            "number-explainer.pdf",
            "scores.json",
            "sources.json",
            "source_inventory.json",
            "missing_evidence.json",
            "receipt_manifest.json",
            "number_inventory.json",
            "runlog.md",
            "render_receipt.json",
            "visual-qa.json",
        }
        if template_present:
            required_files.update({
                "template-framed-onepager.html",
                "template-framed-onepager.pdf",
                "template-render-receipt.json",
            })
        if not required_files.issubset(set(review.get("required_files_verified") or [])):
            failures.append("technical review does not enumerate the full required release set")

    md = md_path.read_text()
    if "—" in md or "/home/" in md or "/mnt/" in md or "CANARY" in md:
        failures.append("review Markdown contains forbidden style, path, or canary text")
    if "Project Room" not in md or "internal" not in md.lower():
        failures.append("review Markdown lacks the internal Project Room boundary")

    if failures:
        for item in failures:
            why(item)
        return 1
    print(f"PASS: fresh {args.kind} review verifies the exact rendered internal package with no blocking findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
