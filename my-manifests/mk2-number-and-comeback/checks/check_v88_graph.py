#!/usr/bin/env python3
"""Validate pathway-v88-draft.json against SPEC-v88.md, diffed from pathway-v87.json.

Asserts the EXACT spec'd change set and that everything else is byte-identical.
Every failure prints WHY. Exit 0 is the only PASS.
"""
import argparse
import json
import sys

FAILS = []


def fail(msg):
    FAILS.append(msg)


UNKNOWN_TEXT = ("I wasn't able to confirm whether that booking went through. "
                "The MK2 Optical office will double-check it and reach out to you. "
                "If you'd like, you can also call them at (212) 219-2219.")
CLOSE_TEXT = ("You're all set. If you have further questions, please call MK2 Optical "
              "at (212) 219-2219")

NEW_NODES = {"n_reconcile_1", "n_reconcile_2", "e_booked_recovered", "e_book_unknown"}
CHANGED_NODES = {"n_book_1", "n_book_2", "e_booking_failed"}
DROPPED_EDGES = {"edge-n_book_1-e_booking_failed-book-success-true",
                 "edge-n_book_2-e_booking_failed-book-success-true"}
NEW_EDGES = {
    "edge-n_book_1-n_reconcile_1-book-success-not-true": ("n_book_1", "n_reconcile_1", "book_success != true"),
    "edge-n_book_2-n_reconcile_2-book-success-not-true": ("n_book_2", "n_reconcile_2", "book_success != true"),
    "edge-n_reconcile_1-e_book_unknown-recon-ok-not-true": ("n_reconcile_1", "e_book_unknown", "recon_ok != true"),
    "edge-n_reconcile_1-e_booked_recovered-recon-count-ge-1": ("n_reconcile_1", "e_booked_recovered", "recon_count >= 1"),
    "edge-n_reconcile_1-e_book_unknown-recon-count-0": ("n_reconcile_1", "e_book_unknown", "recon_count == 0"),
    "edge-n_reconcile_2-e_book_unknown-recon-ok-not-true": ("n_reconcile_2", "e_book_unknown", "recon_ok != true"),
    "edge-n_reconcile_2-e_booked_recovered-recon-count-ge-1": ("n_reconcile_2", "e_booked_recovered", "recon_count >= 1"),
    "edge-n_reconcile_2-e_book_unknown-recon-count-0": ("n_reconcile_2", "e_book_unknown", "recon_count == 0"),
}


def canon(obj):
    return json.dumps(obj, sort_keys=True)


def check_untouched(base, draft):
    for key in ("analysis_options", "entity_schemas", "memory_enabled", "post_call_actions"):
        if canon(base.get(key)) != canon(draft.get(key)):
            fail(f"top-level '{key}' changed; spec says untouched")

    bnodes = {n["id"]: n for n in base["nodes"]}
    dnodes = {n["id"]: n for n in draft["nodes"]}
    if len(draft["nodes"]) != 46:
        fail(f"node count {len(draft['nodes'])}, expected 46")
    if len(draft["edges"]) != 121:
        fail(f"edge count {len(draft['edges'])}, expected 121")
    missing = set(bnodes) - set(dnodes)
    if missing:
        fail(f"v87 nodes missing from draft: {sorted(missing)}")
    unexpected = set(dnodes) - set(bnodes) - NEW_NODES
    if unexpected:
        fail(f"unexpected new nodes: {sorted(unexpected)}")
    for nid, bnode in bnodes.items():
        if nid in CHANGED_NODES or nid not in dnodes:
            continue
        if canon(bnode) != canon(dnodes[nid]):
            fail(f"node '{nid}' changed but is not in the spec'd change set")

    bedges = {e["id"]: e for e in base["edges"]}
    dedges = {e["id"]: e for e in draft["edges"]}
    for eid in DROPPED_EDGES:
        if eid in dedges:
            fail(f"edge '{eid}' should have been deleted")
    for eid, bedge in bedges.items():
        if eid in DROPPED_EDGES:
            continue
        if eid not in dedges:
            fail(f"v87 edge '{eid}' missing from draft")
        elif canon(bedge) != canon(dedges[eid]):
            fail(f"edge '{eid}' changed but is not in the spec'd change set")
    unexpected_e = set(dedges) - set(bedges) - set(NEW_EDGES)
    if unexpected_e:
        fail(f"unexpected new edges: {sorted(unexpected_e)}")
    return bnodes, dnodes, dedges


def check_book_nodes(bnodes, dnodes):
    for nid, recon in (("n_book_1", "n_reconcile_1"), ("n_book_2", "n_reconcile_2")):
        b, d = bnodes[nid]["data"], dnodes[nid]["data"]
        rp = d.get("responsePathways") or []
        if len(rp) != 3:
            fail(f"{nid}: expected 3 responsePathways, got {len(rp)}")
            continue
        if rp[0][:3] != b["responsePathways"][0][:3] or rp[0][3].get("id") != b["responsePathways"][0][3]["id"]:
            fail(f"{nid}: pathway[0] (slot_conflict) must be unchanged, got {rp[0]}")
        if rp[1][:3] != b["responsePathways"][1][:3] or rp[1][3].get("id") != b["responsePathways"][1][3]["id"]:
            fail(f"{nid}: pathway[1] (success) must be unchanged, got {rp[1]}")
        if rp[2][:3] != ["book_success", "!=", "true"]:
            fail(f"{nid}: pathway[2] condition must stay book_success != true, got {rp[2][:3]}")
        if rp[2][3].get("id") != recon:
            fail(f"{nid}: pathway[2] must target {recon}, got {rp[2][3].get('id')}")
        for k in ("url", "method", "headers", "body", "responseData", "modelOptions", "name"):
            if canon(b.get(k)) != canon(d.get(k)):
                fail(f"{nid}: data.{k} changed; only the catch-all destination may change")


def check_reconcile_nodes(bnodes, dnodes):
    appt = bnodes["n_appt_check"]["data"]
    for nid in ("n_reconcile_1", "n_reconcile_2"):
        node = dnodes.get(nid)
        if not node:
            fail(f"missing node {nid}")
            continue
        if node.get("type") != "Webhook":
            fail(f"{nid}: type must be Webhook, got {node.get('type')}")
        d = node.get("data") or {}
        if d.get("url") != appt["url"]:
            fail(f"{nid}: url must equal n_appt_check's ({appt['url']}), got {d.get('url')}")
        if d.get("method") != "POST":
            fail(f"{nid}: method must be POST")
        if canon(d.get("headers")) != canon(appt["headers"]):
            fail(f"{nid}: headers must be copied exactly from n_appt_check")
        if canon(d.get("body")) != canon(appt["body"]):
            fail(f"{nid}: body must be copied exactly from n_appt_check")
        rd = {r.get("name"): r.get("data") for r in (d.get("responseData") or [])}
        if rd != {"recon_ok": "$.ok", "recon_count": "$.result.count"}:
            fail(f"{nid}: responseData must be recon_ok<-$.ok and recon_count<-$.result.count, got {rd}")
        mo = d.get("modelOptions") or {}
        if mo.get("retryAttempts") != 0 or mo.get("skipUserResponse") is not True:
            fail(f"{nid}: modelOptions must be retryAttempts 0 + skipUserResponse true, got {mo}")
        rp = d.get("responsePathways") or []
        want = [(["recon_ok", "!=", "true"], "e_book_unknown"),
                (["recon_count", ">=", "1"], "e_booked_recovered"),
                (["recon_count", "==", "0"], "e_book_unknown")]
        if len(rp) != 3:
            fail(f"{nid}: expected 3 responsePathways in conservative-first order, got {len(rp)}")
        for i, (cond, dest) in enumerate(want):
            if i >= len(rp):
                break
            if rp[i][:3] != cond or rp[i][3].get("id") != dest:
                fail(f"{nid}: pathway[{i}] must be {cond} -> {dest}, got {rp[i][:3]} -> {rp[i][3].get('id')}")


def check_end_nodes(bnodes, dnodes):
    spec = {
        "e_booked_recovered": ("booked_after_reconcile", CLOSE_TEXT),
        "e_book_unknown": ("booking_unverified", UNKNOWN_TEXT),
    }
    for nid, (outcome, text) in spec.items():
        node = dnodes.get(nid)
        if not node:
            fail(f"missing End node {nid}")
            continue
        if node.get("type") != "End Call":
            fail(f"{nid}: type must be 'End Call', got {node.get('type')}")
        d = node.get("data") or {}
        if d.get("text") != text:
            fail(f"{nid}: text must be EXACTLY the spec'd copy.\n  want: {text}\n  got:  {d.get('text')}")
        if d.get("outcome") != outcome:
            fail(f"{nid}: outcome must be {outcome}, got {d.get('outcome')}")
        tag = d.get("tag") or {}
        if tag.get("name") != f"outcome:{outcome}":
            fail(f"{nid}: tag.name must be outcome:{outcome}, got {tag.get('name')}")

    b, d = bnodes["e_booking_failed"], dnodes.get("e_booking_failed")
    if not d:
        fail("e_booking_failed must be kept as the safety net")
    else:
        if d["data"].get("text") != UNKNOWN_TEXT:
            fail("e_booking_failed: text must be reworded to the exact e_book_unknown copy, got: "
                 + str(d["data"].get("text")))
        for k, v in b["data"].items():
            if k != "text" and canon(v) != canon(d["data"].get(k)):
                fail(f"e_booking_failed: data.{k} changed; only text may change")


def check_edges(dnodes, dedges):
    for eid, (src, tgt, label) in NEW_EDGES.items():
        e = dedges.get(eid)
        if not e:
            fail(f"missing edge {eid}")
            continue
        if e.get("source") != src or e.get("target") != tgt:
            fail(f"{eid}: must run {src} -> {tgt}, got {e.get('source')} -> {e.get('target')}")
        if e.get("type") != "custom":
            fail(f"{eid}: type must be 'custom' (load-bearing for routing), got {e.get('type')}")
        if (e.get("data") or {}).get("label") != label:
            fail(f"{eid}: data.label must be '{label}', got {(e.get('data') or {}).get('label')}")
    inbound_failed = [e for e in dedges.values() if e.get("target") == "e_booking_failed"]
    if inbound_failed:
        fail(f"e_booking_failed must have zero inbound edges, found {[e['id'] for e in inbound_failed]}")
    # every responsePathways destination has a matching edge
    for nid in ("n_book_1", "n_book_2", "n_reconcile_1", "n_reconcile_2"):
        for rp in dnodes[nid]["data"]["responsePathways"]:
            dest = rp[3].get("id")
            if not any(e.get("source") == nid and e.get("target") == dest for e in dedges.values()):
                fail(f"{nid}: responsePathways targets {dest} but no edge {nid}->{dest} exists")


def check_text_invariants(draft):
    blob = json.dumps(draft)
    if "855" in blob:
        fail("retired '855' number appears in the draft")
    carriers = sorted(n["id"] for n in draft["nodes"]
                      if "(212) 219-2219" in json.dumps(n.get("data", {}).get("text") or ""))
    for must in ("e_booked_recovered", "e_book_unknown", "e_booking_failed"):
        if must not in carriers:
            fail(f"'{must}' must carry the (212) 219-2219 number in its text")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--draft", required=True)
    args = ap.parse_args()
    try:
        base = json.load(open(args.base))
        draft = json.load(open(args.draft))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: cannot load inputs: {exc}")
        sys.exit(1)

    bnodes, dnodes, dedges = check_untouched(base, draft)
    if not FAILS:
        check_book_nodes(bnodes, dnodes)
        check_reconcile_nodes(bnodes, dnodes)
        check_end_nodes(bnodes, dnodes)
        check_edges(dnodes, dedges)
        check_text_invariants(draft)

    if FAILS:
        print(f"FAIL: {len(FAILS)} violation(s):")
        for f in FAILS:
            print(" -", f)
        sys.exit(1)
    print("PASS: draft matches SPEC-v88 exactly; 46 nodes, 121 edges, no unspec'd mutations")


if __name__ == "__main__":
    main()
