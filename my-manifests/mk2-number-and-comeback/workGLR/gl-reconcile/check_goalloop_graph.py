#!/usr/bin/env python3
"""Offline structural/semantic validator for the v94 goal-loop graph."""
import argparse, json, re, sys
from pathlib import Path

DEFAULT_SPEC = "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/workV94d4/amend-reference-point/SPEC-v94-draft4.md"
V92 = "/home/ankit114/repos/ringer/my-manifests/mk2-number-and-comeback/pathway-v92.json"
NODE_IDS = {"n_identity","n_appt_check","n_goal_update","n_availability","n_goal_response","n_select","n_consent","n_atomic_book","n_reconcile","n_confirm","n_service_guard","n_suppress","e_close"}
GOAL_FIELDS = {"goal_intent","goal_from","goal_to","time_from","time_to","anchor","relation","goal_status","goal_revision","goal_clarify_count","goal_ambiguity_key","last_offered_dates","offer_id","offer_expires_at","selected_slot"}
SOURCE_IDS = set("n_identity n_ask n_date_conflict n_miss_empty n_miss_thin n_miss_unbookable n_clarify n_miss_time n_offer n_offer_2 n_offer_3 n_offer_near n_recheck n_miss_unread n_which_intent n_gate_1 n_gate_2 n_negotiate n_search n_page_2 n_page_3 n_page_near n_verify_1 n_verify_2 n_book_1 n_book_2 n_confirm n_help n_office n_faq e_safe_identity e_safe_failure e_booking_failed e_book_unknown e_booked e_office e_declined e_stop e_not_me e_existing e_timeout e_defer n_suppress_stop n_suppress_not_me n_appt_check n_reconcile_1 n_reconcile_2 e_booked_recovered".split())
GUARDS = {"n_identity","n_appt_check","n_service_guard","n_suppress","n_confirm","n_atomic_book","n_reconcile","e_close"}
TERMINAL_SOURCES = {"n_identity","n_appt_check","n_service_guard","n_suppress","n_confirm","n_atomic_book","n_reconcile","n_goal_update"}
OFFER_NODES = {"n_goal_response"}
BANNED = re.compile(r"one moment|let me check|checking availability|please hold|give me a (?:moment|second)", re.I)
CLOCK = re.compile(r"\b\d{1,2}:\d{2}\s*[ap]m\b", re.I)

def flat_text(x):
    if isinstance(x, str): return x
    if isinstance(x, dict): return "\n".join(flat_text(v) for v in x.values())
    if isinstance(x, list): return "\n".join(flat_text(v) for v in x)
    return ""

def scalar_items(x, path=""):
    """Yield (json path, scalar) pairs so failures can name their location."""
    if isinstance(x, dict):
        for k, val in x.items():
            yield from scalar_items(val, f"{path}.{k}" if path else str(k))
    elif isinstance(x, list):
        for i, val in enumerate(x): yield from scalar_items(val, f"{path}[{i}]")
    else: yield path, x

def endpoint(n):
    d=n.get("data",{})
    return str(d.get("url", n.get("url", d.get("endpoint", n.get("endpoint",""))))).lower()

def edge_kind(e):
    return flat_text({k:v for k,v in e.items() if k not in ("id","source","target")}).lower()

class V:
    def __init__(self): self.errors=[]; self.count=0
    def check(self, ok, why):
        self.count += 1
        if not ok: self.errors.append(why)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--draft", required=True); ap.add_argument("--spec", default=DEFAULT_SPEC); a=ap.parse_args()
    v=V()
    try: g=json.loads(Path(a.draft).read_text())
    except Exception as e: print(f"FAIL: draft: invalid JSON: {e}"); return 1
    try: spec=Path(a.spec).read_text()
    except Exception as e: print(f"FAIL: spec: cannot read {a.spec}: {e}"); return 1
    v.check("## 9. VALIDATOR PLAN" in spec, f"spec {a.spec}: missing validator plan")
    nodes=g.get("nodes",[]); edges=g.get("edges",[]); by={n.get("id"):n for n in nodes}; ids=[n.get("id") for n in nodes]
    v.check(len(nodes)==13, f"graph.nodes: expected exactly 13 nodes, got {len(nodes)}")
    v.check(len(ids)==len(set(ids)), "graph.nodes: duplicate node id(s)")
    v.check(set(ids)==NODE_IDS, f"graph.nodes: ids differ; missing={sorted(NODE_IDS-set(ids))}, extra={sorted(set(ids)-NODE_IDS)}")
    for e in edges:
        v.check(e.get("source") in by and e.get("target") in by, f"edge {e.get('id')}: unresolved {e.get('source')} -> {e.get('target')}")
    mig=g.get("source_id_map", g.get("migration_map",{})); mapped=[]
    if isinstance(mig,dict): mapped=list(mig.keys())
    elif isinstance(mig,list): mapped=[x.get("source") if isinstance(x,dict) else x for x in mig]
    v.check(len(mapped)==48 and set(mapped)==SOURCE_IDS, f"source_id_map: each of 48 v92 ids required exactly once; missing={sorted(SOURCE_IDS-set(mapped))}, duplicates={[x for x in set(mapped) if mapped.count(x)>1]}")

    contract=g.get("contract",{}); goal=contract.get("goal_object",g.get("goal_object",{})); fields=goal.get("fields",goal.get("schema",{}))
    fset=set(fields) if isinstance(fields,dict) else {x.get("name") for x in fields if isinstance(x,dict)}
    v.check(goal.get("name")=="scheduling_goal_v94", "goal_object.name: must be scheduling_goal_v94")
    v.check(fset==GOAL_FIELDS, f"goal schema: exact fields required; missing={sorted(GOAL_FIELDS-fset)}, extra={sorted(fset-GOAL_FIELDS)}")
    v.check("direction" not in flat_text(goal).lower(), "goal schema: banned legacy direction field retained")
    gt=flat_text(goal).lower()
    for word in ("retain","replace","clear","unsatisfied","offered","confirmed","abandoned"):
        v.check(word in gt, f"goal_object: missing required patch/lifecycle term {word!r}")
    v.check(goal.get("persistent_objects",1)==1, "goal_object: exactly one persistent object required")
    v.check(goal.get("authoritative_writer")=="n_availability", "goal_object.authoritative_writer: only n_availability gateway echo may write authoritative fields")

    out={i:[] for i in by}
    for e in edges:
        if e.get("source") in out: out[e["source"]].append(e.get("target"))
    for e in edges: v.check(e.get("source")!=e.get("target"), f"edge {e.get('id')}: self-loop/fail-stay at {e.get('source')}")
    for nid in ("n_goal_update","n_availability","n_goal_response"):
        expected={"n_goal_update":"n_availability","n_availability":"n_goal_response","n_goal_response":"n_goal_update"}[nid]
        v.check(expected in out.get(nid,[]), f"loop node {nid}: missing required edge to {expected}")
    for nid,n in by.items():
        waiting=bool(n.get("data",{}).get("userWait") or n.get("userWait") or n.get("waits_for_user"))
        # Static proof of no fail-stay: a waiting non-guard must have an exit;
        # the self-loop assertion above separately forbids remaining in place.
        if waiting and nid not in GUARDS:
            v.check(bool(out.get(nid)), f"node {nid}: waiting state has no outbound target (fail-stay generalized [35])")
    for e in edges:
        if e.get("target")=="e_close": v.check(e.get("source") in TERMINAL_SOURCES, f"edge {e.get('id')}: mid-negotiation node {e.get('source')} illegally targets terminal e_close")
    v.check(contract.get("loop_cap")==8, "contract.loop_cap: must prove cap 8")
    v.check(contract.get("ninth_update_target")=="e_close", "contract.ninth_update_target: ninth scheduling update must reach e_close")
    v.check("I’m sorry I couldn’t finish scheduling here. Please call MK2 Optical at (212) 219-2219 for help." in flat_text(by.get("e_close",{})), "node e_close: missing exact loop-cap sentence")
    # Migration provenance must contain the retired ids named in SPEC §3.
    # Search executable graph/config only, not source_id_map provenance.
    alltxt=flat_text({k:val for k,val in g.items() if k not in ("source_id_map","migration_map")})
    for banned in ("conflict node","page_2","page_3","page_near","compensation paging","before=none"):
        v.check(banned not in alltxt.lower(), f"graph: banned legacy branch/config {banned!r}")

    webhook_nodes=[]; availability_sites=[]
    for nid,n in by.items():
        data=n.get("data",{}); prompt=str(data.get("prompt",n.get("prompt","")))
        m=BANNED.search(prompt); v.check(not m, f"node {nid}: banned promise in prompt: {m.group(0)!r}" if m else f"node {nid}: no banned promise")
        if CLOCK.search(prompt): v.check(nid in OFFER_NODES and any(x in prompt.lower() for x in ("offer","nearest","slot_")), f"node {nid}: clock time outside offer/nearest rendering prompt")
        ishook="webhook" in str(n.get("type","")).lower() or bool(data.get("url") or n.get("url"))
        if ishook:
            webhook_nodes.append(nid)
            if nid=="n_availability" or "availability" in endpoint(n): availability_sites.append(nid)
    v.check(availability_sites==["n_availability"], f"availability: expected sole call site n_availability, found={availability_sites}")
    av=flat_text(by.get("n_availability",{}));
    for term in ("goal_from","goal_to","time_from","time_to","anchor","relation","prior_goal","patch","raw_text","goal_echo","decision_source","disagreement","pathway_read","gateway_read","slot_minutes"):
        v.check(term in av, f"node n_availability: request/response contract missing {term}")
    for term in ("distance","directional","top two","one inventory query"):
        v.check(term in av.lower() or term in flat_text(contract).lower(), f"availability contract: missing reference-point rule {term!r}")

    offer=contract.get("offer",{}); ot=flat_text(offer).lower()
    for term in ("offer_id","offer_issued_at","offer_expires_at","inventory_token","exactly two","normalized","invalidat","silent","stale","nearest","real"):
        v.check(term in ot, f"offer contract: missing {term!r}")
    v.check(offer.get("ttl_minutes")==10, "offer.ttl_minutes: missing/stated TTL must be 10")
    choices=offer.get("choices", offer.get("choice_count",2))
    v.check(choices==2 or (isinstance(choices,list) and len(choices)==2), f"offer.choices: expected exactly two normalized choices, got {choices!r}")
    extract_nodes=[]
    for nid,n in by.items():
        t=flat_text(n)
        if "EXTRACT_GOAL_UPDATE_V94" in t or n.get("data",{}).get("extractVars") or n.get("extraction") or n.get("data",{}).get("extraction"): extract_nodes.append(nid)
    v.check(extract_nodes==["n_goal_update"], f"extraction: EXACTLY ONE config/reference on n_goal_update required; found {extract_nodes}")
    ext=flat_text(by.get("n_goal_update",{}))
    for term in ("user_verbatim","intent_update","from_update","to_update","time_from_update","time_to_update","anchor_update","relation_update","selection_update"):
        v.check(term in ext, f"node n_goal_update extraction: missing exact output {term}")

    safety=contract.get("safety",{}); st=flat_text(safety).lower()
    v.check(safety.get("clarify_max_questions")==2, "safety.clarify_max_questions: one question plus one re-ask requires 2")
    v.check(safety.get("appt_check_fail_target") in ("n_service_guard","e_close"), "safety: appt_check ok!=true must route to guard/close")
    v.check(safety.get("blank_conflict_target") in ("n_goal_update","n_reconcile","e_close"), "safety: blank/non-boolean slot_conflict must not book/confirm")
    for e in edges:
        k=edge_kind(e)
        if e.get("source")=="n_appt_check" and any(x in k for x in ("error","timeout","blank","malformed","ok != true","ok=false")):
            v.check(e.get("target") in ("n_service_guard","e_close"), f"edge {e.get('id')}: appt-check non-true branch illegally schedules via {e.get('target')}")
        if e.get("source")=="n_atomic_book" and any(x in k for x in ("blank","missing","non-boolean","unknown conflict")):
            v.check(e.get("target") not in ("n_confirm","n_atomic_book"), f"edge {e.get('id')}: blank/non-boolean conflict may book or confirm via {e.get('target')}")
    atomic=contract.get("atomic_booking",{}); at=flat_text(atomic).lower()
    for term in ("check_and_book","/sign","offer_id","slot_id","conversation_id + ':' + offer_id","identical","idempotency"):
        v.check(term in at, f"atomic_booking: missing {term!r}")
    v.check(atomic.get("max_retries")==2, "atomic_booking.max_retries: must be 2")
    v.check(out.get("n_select",[]).count("n_consent")==1 and "n_atomic_book" in out.get("n_consent",[]), "booking path: must include n_select -> n_consent -> n_atomic_book")
    rec=flat_text(contract.get("reconciliation",{})).lower()
    for term in ("one read","offer_id","slot_id","store","patient","date","start","unique exact match"):
        v.check(term in rec, f"reconciliation: missing {term!r}")
    v.check(contract.get("affirmative_claim_owner")=="n_confirm", "contract.affirmative_claim_owner: only n_confirm may claim booking")

    try:
        old=json.loads(Path(V92).read_text()); oldby={n["id"]:n for n in old["nodes"]}
        en="You're all set. If you have further questions, please call MK2 Optical at (212) 219-2219"
        zh="您都安排好了。如有其他问题，请致电 MK2 Optical，电话：(212) 219-2219"
        defer=oldby["e_defer"]["data"]["text"]
        v.check(en in flat_text(by.get("n_confirm",{})), "node n_confirm: mandated EN close differs from v92 bytes")
        v.check(zh in flat_text(by.get("n_confirm",{})), "node n_confirm: mandated ZH close differs from v92 bytes")
        v.check(defer in flat_text(by.get("e_close",{})), "node e_close defer mode: mandated deferral differs from v92 bytes")
    except Exception as e: v.check(False, f"copy reference {V92}: {e}")
    # SPEC §10 assigns measured turn latency and p95 to the runtime harness.
    # A static graph can only declare the limit and harness requirement.
    tel=contract.get("latency",{})
    v.check(tel.get("max_visible_answer_seconds")==15.0, "latency contract: max visible answer must be 15.0s")
    v.check(tel.get("measurement_owner")=="harness", "latency contract: runtime measurement must be assigned to harness")
    v.check(tel.get("p95_required") is True, "latency contract: p95 must be required by harness")
    if v.errors:
        for x in v.errors: print("FAIL:",x)
        print(f"FAIL: {len(v.errors)} of {v.count} assertions failed")
        return 1
    print(f"PASS: {v.count} assertions")
    return 0
if __name__=="__main__": raise SystemExit(main())
