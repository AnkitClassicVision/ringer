#!/usr/bin/env python3
"""Render a portable reader report from validated Mission Fit JSON."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from validate_mission_audit import ValidationError, validate_payload


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def list_items(items: list[Any], empty: str = "None recorded.") -> str:
    if not items:
        return f"<p class=\"muted\">{esc(empty)}</p>"
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def badge(value: str) -> str:
    slug = value.lower().replace("_", "-")
    return f'<span class="badge badge-{esc(slug)}">{esc(value.replace("_", " "))}</span>'


def evidence_refs(values: list[str]) -> str:
    if not values:
        return ""
    return f'<p class="refs">Evidence: {esc(", ".join(values))}</p>'


def mission_markup(mission: dict[str, Any]) -> str:
    checks = []
    for label, key in (
        ("Outcome", "outcome"),
        ("Access", "access"),
        ("Quality", "quality"),
        ("Evidence", "evidence"),
        ("Supervision", "supervision"),
    ):
        check = mission[key]
        checks.append(
            "<div class=\"check\">"
            f"<div><strong>{esc(label)}</strong>{badge(check['verdict'])}</div>"
            f"<p>{esc(check['summary'])}</p>"
            f"{evidence_refs(check['evidence_ids'])}"
            "</div>"
        )

    findings_markup = "".join(
        "<li>"
        f"{badge(item['result'])} <strong>{esc(item['run_id'])}</strong> — {esc(item['summary'])}"
        f"{evidence_refs(item['evidence_ids'])}"
        "</li>"
        for item in mission["run_findings"]
    )
    if not findings_markup:
        findings_markup = '<li class="muted">No run evidence was available.</li>'

    patterns = mission["repeated_patterns"]
    pattern_markup = "".join(
        "<li>"
        f"<strong>{esc(item['pattern'])}</strong> "
        f"<span class=\"muted\">{esc(item['count'])} runs · {esc(item['failure_mode'])}</span>"
        f"{evidence_refs(item['evidence_ids'])}"
        "</li>"
        for item in patterns
    )
    if not pattern_markup:
        pattern_markup = '<li class="muted">No repeated pattern met the evidence threshold.</li>'

    replay_markup = "".join(
        "<li>"
        f"<strong>{esc(case['name'])}</strong> — {esc(case['expected_outcome'])}"
        "</li>"
        for case in mission["replay_cases"]
    )
    if not replay_markup:
        replay_markup = '<li class="muted">No replay pack could be built from the available evidence.</li>'

    return (
        "<section class=\"mission\">"
        "<header>"
        f"<div><p class=\"index\">{esc(mission['mission_id'])} · {esc(mission['run_count'])} runs reviewed</p>"
        f"<h2>{esc(mission['name'])}</h2></div>{badge(mission['verdict'])}"
        "</header>"
        f"<p class=\"job\">{esc(mission['job'])}</p>"
        f"<div class=\"checks\">{''.join(checks)}</div>"
        f"<div class=\"runs\"><h3>Recent runs</h3><ul>{findings_markup}</ul></div>"
        "<div class=\"split\">"
        f"<div><h3>Repeated patterns</h3><ul>{pattern_markup}</ul></div>"
        f"<div><h3>Replay pack</h3><ol>{replay_markup}</ol></div>"
        "</div>"
        "</section>"
    )


def recommendation_markup(recommendation: dict[str, Any]) -> str:
    return (
        "<article class=\"recommendation\">"
        "<header>"
        f"<span class=\"number\">{esc(recommendation['number'])}</span>"
        f"<div><p class=\"index\">{esc(recommendation['action'])}</p>"
        f"<h3>{esc(recommendation['title'])}</h3></div>{badge(recommendation['status'])}"
        "</header>"
        f"<p>{esc(recommendation['why'])}</p>"
        f"{evidence_refs(recommendation['evidence_ids'])}"
        "<dl>"
        f"<div><dt>Risk</dt><dd>{esc(recommendation['risk'])}</dd></div>"
        f"<div><dt>Approver</dt><dd>{esc(recommendation['approver'])}</dd></div>"
        f"<div><dt>Rollback</dt><dd>{esc(recommendation['rollback'])}</dd></div>"
        "</dl>"
        "</article>"
    )


def render(data: dict[str, Any]) -> str:
    mission_sections = "".join(mission_markup(mission) for mission in data["missions"])
    if not mission_sections:
        mission_sections = '<section class="empty"><h2>More evidence is needed.</h2><p>Add 3–10 representative runs or an accessible export, then run Mission Fit again.</p></section>'

    recommendations = "".join(recommendation_markup(item) for item in data["recommendations"])
    if not recommendations:
        recommendations = '<p class="muted">No harness change is supported by the available evidence.</p>'

    source_labels = [f"{item['label']} ({item['evidence_status']})" for item in data["coverage"]["sources"]]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your Mission Fit</title>
<style>
:root {{ color-scheme: dark; --bg:#1c1c1c; --panel:#242424; --line:#3a3a3a; --text:#eae6df; --muted:#a9a6a0; --cyan:#18c1e8; --green:#3ae88d; --yellow:#ffdf43; --red:#f2453d; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:Avenir, "Avenir Next", system-ui, sans-serif; line-height:1.55; }}
main {{ width:min(1080px, calc(100% - 32px)); margin:0 auto; padding:48px 0 80px; }}
h1,h2,h3,p {{ margin-top:0; }}
h1 {{ max-width:820px; font-size:clamp(2.3rem, 7vw, 5.8rem); line-height:.94; letter-spacing:-.055em; margin-bottom:20px; }}
h2 {{ font-size:clamp(1.5rem, 3vw, 2.4rem); line-height:1.08; letter-spacing:-.035em; }}
h3 {{ font-size:1rem; }}
.lead {{ max-width:760px; font-size:1.15rem; color:#d4d0c9; }}
.index {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.12em; font-weight:700; font-size:.72rem; margin-bottom:8px; }}
.summary {{ display:grid; grid-template-columns:repeat(3,1fr); border-top:1px solid var(--line); border-bottom:1px solid var(--line); margin:34px 0 48px; }}
.summary div {{ padding:18px 20px; border-right:1px solid var(--line); }}
.summary div:last-child {{ border-right:0; }}
.summary strong {{ display:block; font-size:1.1rem; }}
.summary span {{ color:var(--muted); font-size:.86rem; }}
.badge {{ display:inline-flex; align-items:center; width:max-content; padding:5px 9px; border:1px solid var(--line); border-radius:999px; text-transform:uppercase; letter-spacing:.08em; font-size:.68rem; font-weight:800; color:var(--text); }}
.badge-ready,.badge-found {{ border-color:rgba(58,232,141,.55); color:var(--green); }}
.badge-blocked,.badge-no-safe-change {{ border-color:rgba(242,69,61,.55); color:var(--red); }}
.badge-needs-change,.badge-gap,.badge-needs-input,.badge-review-required {{ border-color:rgba(255,223,67,.55); color:var(--yellow); }}
.badge-inaccessible {{ color:var(--muted); }}
.badge-used,.badge-applied,.badge-approved {{ border-color:rgba(58,232,141,.55); color:var(--green); }}
.badge-changed,.badge-proposed,.badge-unknown {{ border-color:rgba(255,223,67,.55); color:var(--yellow); }}
.badge-dropped,.badge-rejected {{ border-color:rgba(242,69,61,.55); color:var(--red); }}
.mission {{ border-top:1px solid var(--line); padding:34px 0 44px; }}
.mission>header {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-start; }}
.job {{ max-width:820px; font-size:1.05rem; color:#d4d0c9; }}
.checks {{ display:grid; grid-template-columns:repeat(5,1fr); border:1px solid var(--line); margin:26px 0; }}
.check {{ padding:16px; border-right:1px solid var(--line); min-width:0; }}
.check:last-child {{ border-right:0; }}
.check strong {{ display:block; margin-bottom:8px; }}
.check .badge {{ margin-bottom:12px; }}
.check p {{ color:var(--muted); font-size:.86rem; overflow-wrap:anywhere; }}
.split {{ display:grid; grid-template-columns:1fr 1fr; gap:34px; }}
.runs {{ margin:0 0 28px; padding:18px 20px; background:var(--panel); border-left:2px solid var(--cyan); }}
.runs .badge {{ margin-right:8px; }}
ul,ol {{ padding-left:1.25rem; }}
li+li {{ margin-top:8px; }}
.refs {{ margin:7px 0 0; color:var(--muted); font-size:.72rem; letter-spacing:.02em; overflow-wrap:anywhere; }}
.recommendations {{ border-top:1px solid var(--line); padding-top:38px; }}
.recommendation {{ display:grid; grid-template-columns:minmax(0,1fr); padding:26px 0; border-bottom:1px solid var(--line); }}
.recommendation header {{ display:flex; gap:16px; align-items:flex-start; }}
.number {{ display:grid; place-items:center; width:34px; height:34px; flex:0 0 34px; border-radius:50%; background:var(--cyan); color:#07181c; font-weight:900; }}
dl {{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; margin:8px 0 0; }}
dl div {{ border-left:2px solid var(--line); padding-left:12px; }}
dt {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.1em; font-size:.68rem; font-weight:800; }}
dd {{ margin:5px 0 0; color:var(--muted); font-size:.88rem; }}
.coverage {{ margin-top:46px; padding-top:30px; border-top:1px solid var(--line); }}
.muted {{ color:var(--muted); }}
.empty {{ border:1px solid var(--line); padding:28px; margin:30px 0; }}
@media (max-width:800px) {{ .summary,.checks,dl {{ grid-template-columns:1fr; }} .summary div,.check {{ border-right:0; border-bottom:1px solid var(--line); }} .summary div:last-child,.check:last-child {{ border-bottom:0; }} .split {{ grid-template-columns:1fr; }} .mission>header {{ flex-direction:column; }} main {{ padding-top:28px; }} }}
</style>
</head>
<body>
<main>
  <p class="index">Clean My AI Harness · Mission Fit</p>
  <h1>Your agent’s jobs, checked against reality.</h1>
  <p class="lead">This report compares the work you ask for with the tools, data, standards, supervision, and evidence the visible setup can support. Nothing in this report is approval to change the harness.</p>
  <div class="summary">
    <div><strong>{esc(data['surface']['name'])}</strong><span>Surface</span></div>
    <div><strong>{esc(data['cleaner_install']['status'])}</strong><span>Cleaner installation</span></div>
    <div><strong>{esc(len(data['missions']))}</strong><span>Missions reviewed</span></div>
  </div>
  {mission_sections}
  <section class="recommendations">
    <p class="index">Review before changing anything</p>
    <h2>Numbered recommendations</h2>
    {recommendations}
  </section>
  <section class="coverage">
    <p class="index">Coverage</p>
    <h2>What this audit could see</h2>
    <p><strong>Target:</strong> {esc(data['coverage']['target'])}</p>
    {list_items(source_labels, 'No sources were available.')}
    <h3>Inaccessible</h3>
    {list_items(data['coverage']['inaccessible'])}
    <h3>Excluded</h3>
    {list_items(data['coverage']['excluded'])}
    <h3>Limits</h3>
    {list_items(data['limits'])}
    <p>{badge(data['overall_status'])}</p>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = json.loads(args.audit.read_text(encoding="utf-8"))
        validate_payload(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"INVALID: {error}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(payload), encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
