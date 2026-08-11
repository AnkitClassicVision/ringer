#!/usr/bin/env python3
"""Round B check for the v62 build lane (mk2-number-and-comeback).

Two layers, both required:
  1. Independent structural assertions on v62_graph.json — these do not trust
     any worker-authored code.
  2. Execution of the worker's own toolchain: builder reproducibility, candidate
     gate green on v62 and RED on v61, redproof mutation coverage.
Every failure prints WHY. Exit 0 is the only PASS.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

CLOSE = "You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"
DEFER = "For that you'll have to contact the MK2 Optical office at (212) 219-2219"
OLD_NUMBERS = ["855) 750-6688", "855-750-6688", "8557506688"]
CARRIERS = ["n_confirm", "n_office", "n_faq", "e_safe_identity", "e_safe_failure",
            "e_booking_failed", "e_office", "e_declined", "e_stop", "e_not_me", "e_existing"]
BOOKING_NODES = {"n_search", "n_verify_1", "n_verify_2", "n_book_1", "n_book_2",
                 "n_gate_1", "n_gate_2", "n_office", "n_faq", "n_negotiate",
                 "n_offer", "n_offer_2", "n_offer_3", "n_offer_near"}

fails = []


def fail(msg):
    fails.append(msg)


def run(cmd, cwd, timeout=90):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})


def main():
    lane = pathlib.Path(".").resolve()
    expected = ["build_v62.py", "v62_graph.json", "scenarios.py",
                "check_candidate_gate.py", "redproof_run.py", "report.md"]
    missing = [f for f in expected if not (lane / f).is_file()]
    if missing:
        print(f"FAIL: missing deliverables: {', '.join(missing)}")
        return 1

    raw = (lane / "v62_graph.json").read_text(encoding="utf-8")
    try:
        g = json.loads(raw)
    except Exception as e:
        print(f"FAIL: v62_graph.json is not valid JSON: {e}")
        return 1
    nodes = {n.get("id"): n for n in g.get("nodes", [])}
    edges = g.get("edges", [])

    # --- Layer 1: independent structural assertions -------------------------
    for old in OLD_NUMBERS:
        if old in raw:
            fail(f"old office number variant '{old}' still present in v62_graph.json (G1)")

    for nid in CARRIERS + ["e_defer"]:
        node = nodes.get(nid)
        if node is None:
            fail(f"node {nid} missing from v62 graph")
            continue
        blob = json.dumps(node)
        if "(212) 219-2219" not in blob:
            fail(f"{nid} does not carry (212) 219-2219 (G1)")

    close_holders = [nid for nid, n in nodes.items() if CLOSE in json.dumps(n)]
    if close_holders != ["n_confirm"]:
        fail(f"mandated CLOSE must live in n_confirm and nowhere else; found in {close_holders or 'no node'} (G2)")

    e_defer = nodes.get("e_defer")
    if e_defer is not None:
        if e_defer.get("type") != "End Call":
            fail(f"e_defer type is {e_defer.get('type')!r}, expected 'End Call' (G3)")
        if e_defer.get("data", {}).get("text") != DEFER:
            fail(f"e_defer text is not the verbatim mandated deferral (G3): {e_defer.get('data', {}).get('text')!r}")
        outgoing = [e for e in edges if e.get("source") == "e_defer"]
        if outgoing:
            fail(f"e_defer has {len(outgoing)} outgoing edge(s); it must be terminal (G3)")

    confirm_targets = {e.get("target") for e in edges if e.get("source") == "n_confirm"}
    illegal = confirm_targets - {"e_booked", "e_defer"}
    if illegal:
        fail(f"n_confirm routes to {sorted(illegal)}; adjacency must be within {{e_booked, e_defer}} (G4)")
    if "e_defer" not in confirm_targets:
        fail("n_confirm has no edge to e_defer — post-booking asks have nowhere safe to go (G4)")
    booking_reach = confirm_targets & BOOKING_NODES
    if booking_reach:
        fail(f"n_confirm can reach booking-capable nodes {sorted(booking_reach)} (G4)")

    def routes(node_data):
        out = []
        for rp in node_data.get("responsePathways", []):
            try:
                var, op, val, target = rp[0], rp[1], rp[2], rp[3]
            except Exception:
                continue
            tid = target.get("id") if isinstance(target, dict) else target
            out.append((var, op, str(val), tid))
        return out

    ident = nodes.get("n_identity", {}).get("data", {})
    ident_routes = routes(ident)
    count1 = [r for r in ident_routes if r[0] == "count" and r[1] == "==" and r[2] == "1"]
    if not count1:
        fail("n_identity lost its count == 1 route (G5)")
    elif count1[0][3] != "n_appt_check":
        fail(f"n_identity count==1 routes to {count1[0][3]!r}; must route to n_appt_check so every thread start is appointment-checked (G5)")

    appt = nodes.get("n_appt_check")
    if appt is None:
        fail("n_appt_check node missing — Ankit's revision uses the existing /appt-list endpoint via a silent webhook (G5)")
    else:
        ad = appt.get("data", {})
        if appt.get("type") != "Webhook":
            fail(f"n_appt_check type is {appt.get('type')!r}, expected Webhook (G5)")
        if not str(ad.get("url", "")).endswith("/appt-list"):
            fail(f"n_appt_check url is {ad.get('url')!r}; must call the existing /appt-list endpoint (G5)")
        if not ad.get("modelOptions", {}).get("skipUserResponse"):
            fail("n_appt_check must be silent (skipUserResponse) — the patient never sees this check (G5)")
        body = ad.get("body", "")
        if "{{patient_id}}" not in body or "{{store}}" not in body:
            fail(f"n_appt_check body must send patient_id and store: {body!r} (G5)")
        appt_routes = routes(ad)
        defer_idx = ask_idx = None
        for i, (var, op, val, tid) in enumerate(appt_routes):
            if var == "appt_count" and op == ">=" and val == "1" and tid == "e_defer" and defer_idx is None:
                defer_idx = i
            if tid == "n_ask" and ask_idx is None:
                ask_idx = i
        if defer_idx is None:
            fail("n_appt_check has no appt_count >= 1 -> e_defer route (G5)")
        if ask_idx is None:
            fail("n_appt_check has no fallthrough route to n_ask — a gateway outage would strand the recall (G5)")
        if defer_idx is not None and ask_idx is not None and defer_idx > ask_idx:
            fail("appt_count >= 1 -> e_defer must be ordered BEFORE any route to n_ask (G5)")
        resp_names = {r.get("name"): r.get("data") for r in ad.get("responseData", [])}
        if resp_names.get("appt_count") != "$.result.count":
            fail(f"n_appt_check must map appt_count <- $.result.count; got {resp_names.get('appt_count')!r} (G5)")

    for stale in ("campaign_booked", "upcoming_appointment", "booked_already"):
        if stale in raw:
            fail(f"graph still references the retired '{stale}' mechanism")

    for nid in ("n_office", "n_faq"):
        label = nodes.get(nid, {}).get("data", {}).get("globalLabel", "")
        if not re.search(r"booking is confirmed", label, re.I):
            fail(f"{nid} globalLabel lacks the post-booking exclusion wording (G6): {label!r}")
    exist_label = nodes.get("e_existing", {}).get("data", {}).get("globalLabel", "")
    if not re.search(r"outside this conversation", exist_label, re.I):
        fail(f"e_existing globalLabel not tightened to appointments made outside this conversation: {exist_label!r}")

    for nid, n in nodes.items():
        d = n.get("data", {})
        for field in ("prompt", "text"):
            v = d.get(field) or ""
            if "Mott Optical" in v:
                fail(f"{nid}.{field} still says 'Mott Optical' — brand decision is MK2 Optical everywhere")
    if "MK2 Optical" not in (nodes.get("n_ask", {}).get("data", {}).get("prompt") or ""):
        fail("opener n_ask does not introduce MK2 Optical")
    confirm_prompt = nodes.get("n_confirm", {}).get("data", {}).get("prompt") or ""
    if "预约成功" in confirm_prompt:
        fail("Chinese close still uses 预约成功 ('booking succeeded') — must match the English 'You're all set' statement, not strengthen it")
    if not re.search(r"[一-鿿]", confirm_prompt):
        fail("n_confirm prompt carries no Chinese close at all")
    elif "MK2 Optical" not in confirm_prompt or confirm_prompt.count("(212) 219-2219") < 2:
        fail("Chinese close in n_confirm must carry MK2 Optical and (212) 219-2219 (expected the number in both language closes)")
    if "deferred_after_booking" not in raw:
        fail("outcome 'deferred_after_booking' missing from graph/analysis_options")
    booked_text = nodes.get("e_booked", {}).get("data", {}).get("text", "")
    if re.search(r"all set|book", booked_text, re.I):
        fail(f"e_booked text carries a booking claim; invariant 5 reserves claims for n_confirm: {booked_text!r}")

    scen = (lane / "scenarios.py").read_text(encoding="utf-8")
    if "855" in scen:
        fail("scenarios.py still references 855 — stale expectations")
    n_scen = len(re.findall(r"^\s*(?:\{\s*)?['\"]name['\"]\s*:", scen, re.M)) or scen.count("'name':") + scen.count('"name":')
    if n_scen < 40:
        fail(f"scenario inventory looks like {n_scen} entries; spec requires >= 40 (30 prior + ~12 new)")

    # --- Layer 2: execute the worker's toolchain ----------------------------
    with tempfile.TemporaryDirectory() as td:
        tdp = pathlib.Path(td)
        for f in expected:
            shutil.copy(lane / f, tdp / f)
        r = run([sys.executable, "build_v62.py"], cwd=tdp)
        if r.returncode != 0:
            fail(f"build_v62.py exited {r.returncode}: {(r.stderr or r.stdout)[-400:]}")
        else:
            rebuilt = tdp / "v62_graph.json"
            if not rebuilt.is_file():
                fail("build_v62.py did not produce v62_graph.json")
            elif json.loads(rebuilt.read_text()) != g:
                fail("build_v62.py output differs from submitted v62_graph.json — graph drifted from builder")

        r = run([sys.executable, "check_candidate_gate.py", "v62_graph.json"], cwd=tdp)
        if r.returncode != 0:
            fail(f"worker gate FAILS its own v62 graph: {(r.stdout + r.stderr)[-600:]}")

        v61 = lane / "source" / "v61_graph.json"
        if v61.is_file():
            shutil.copy(v61, tdp / "v61_graph.json")
            r = run([sys.executable, "check_candidate_gate.py", "v61_graph.json"], cwd=tdp)
            if r.returncode == 0:
                fail("worker gate PASSES the old v61 graph — the new rules have no teeth")
        else:
            fail("source/v61_graph.json not found; cannot prove the gate rejects the old graph")

        r = run([sys.executable, "redproof_run.py"], cwd=tdp, timeout=180)
        out = r.stdout + r.stderr
        m = re.search(r"mutations_caught\s*=\s*(\d+)", out)
        if r.returncode != 0:
            fail(f"redproof_run.py exited {r.returncode}: {out[-400:]}")
        elif not m:
            fail("redproof_run.py printed no mutations_caught=N count")
        elif int(m.group(1)) < 15:
            fail(f"redproof caught only {m.group(1)} mutations; floor is 15 (11 prior + new M-rules)")

    if fails:
        print(f"FAIL: {len(fails)} requirement(s) unmet:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("PASS: v62 structural rules hold, builder reproduces the graph, gate is green on v62 and red on v61, redproof coverage met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
