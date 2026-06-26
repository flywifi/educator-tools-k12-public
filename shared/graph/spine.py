#!/usr/bin/env python3
"""Context-confirmation spine (offline, stdlib) — RFC-F001 V2 workstream G (LIGHT shell).

Unifies what the ecosystem knows about ONE teacher's situation into a single snapshot + a light
relationship graph, and produces a confirmation checklist (user-truth vs inference) so the teacher can
confirm/correct before any of it drives behavior. This is the *light* spine the plan calls for — it
composes the existing engines (teacher-profile F4, schools F3, staff F5, context) — NOT the full
knowledge-graph + national-scaling engine, which stays a later vision.

Honest by construction: every node/edge carries provenance + confidence; teacher-stated outranks
crawled/inferred; unresolved links are gaps, not guesses; human_review_required stays true.

Usage:
  python3 shared/graph/spine.py --snapshot                 # unified situation snapshot (JSON)
  python3 shared/graph/spine.py --graph                    # nodes + edges (light relationship graph)
  python3 shared/graph/spine.py --confirm                  # confirmation checklist (what to verify)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))
sys.path.insert(0, str(ROOT / "shared" / "schools"))
sys.path.insert(0, str(ROOT / "shared" / "staff"))

PROFILE_LOCAL = ROOT / "shared" / "context" / "profiles" / "teacher.local.json"
PROFILE_EXAMPLE = ROOT / "shared" / "context" / "profiles" / "teacher.example.json"


def _load_profile() -> tuple[dict, str]:
    path = PROFILE_LOCAL if PROFILE_LOCAL.exists() else PROFILE_EXAMPLE
    return json.loads(path.read_text(encoding="utf-8")), str(path.relative_to(ROOT))


def _resolve_school(msid: str | None) -> dict | None:
    if not msid:
        return None
    try:
        import schools  # type: ignore
        for s in schools.schools():
            if s.get("msid") == msid:
                return s
    except Exception:
        return None
    return None


def _resolve_handoffs(profile: dict) -> list[dict]:
    try:
        import staff  # type: ignore
        store, src = staff.load_store()
    except Exception:
        store, src = {"staff": []}, "unavailable"
    out = []
    for h in profile.get("handoffs", []):
        role = h.get("counterparty_role")
        people = [p for p in store.get("staff", []) if p.get("role") == role]
        out.append({"what": h.get("what"), "direction": h.get("direction"), "counterparty_role": role,
                    "resolved": [{"display_name": p.get("display_name"), "authorized": p.get("authorized")} for p in people],
                    "directory_source": src,
                    "gap": None if people else f"no '{role}' in directory"})
    return out


def snapshot() -> dict:
    profile, psrc = _load_profile()
    teacher = profile.get("teacher", {})
    school = _resolve_school(teacher.get("school_msid"))
    handoffs = _resolve_handoffs(profile)
    roles = profile.get("roles", [])
    # Confidence rollup: teacher-stated facts are high; unresolved/crawled lower the floor.
    floor = "high"
    if any(r.get("provenance") not in ("teacher_stated", None) for r in roles):
        floor = "medium"
    if any(h["gap"] for h in handoffs):
        floor = "medium" if floor == "high" else floor
    return {
        "engine": "context-spine", "mode": "light_shell",
        "profile_source": psrc,
        "teacher": {"display_name": teacher.get("display_name"), "district": teacher.get("district"),
                    "school_msid": teacher.get("school_msid")},
        "school": ({"msid": school.get("msid"), "name": school.get("school_name"),
                    "status": school.get("status"), "programs": [p.get("program_name") for p in school.get("programs", [])]}
                   if school else {"resolved": False, "gap": "school_msid not found in shared/schools/"}),
        "roles": [{"role": r.get("role"), "primary": r.get("primary", False),
                   "provenance": r.get("provenance"), "confidence": r.get("confidence")} for r in roles],
        "handoffs": handoffs,
        "preferences": profile.get("preferences", {}),
        "confidence_floor": floor,
        "human_review_required": True,
    }


def graph(snap: dict | None = None) -> dict:
    snap = snap or snapshot()
    nodes, edges = [], []
    t = snap["teacher"]["display_name"] or "teacher"
    nodes.append({"id": f"teacher:{t}", "type": "teacher", "label": t})
    if snap["school"].get("name"):
        sid = f"school:{snap['school']['msid']}"
        nodes.append({"id": sid, "type": "school", "label": snap["school"]["name"]})
        edges.append({"from": f"teacher:{t}", "rel": "works_at", "to": sid})
        for prog in snap["school"].get("programs", []):
            pid = f"program:{prog}"
            nodes.append({"id": pid, "type": "program", "label": prog})
            edges.append({"from": sid, "rel": "offers", "to": pid})
    for r in snap["roles"]:
        rid = f"role:{r['role']}"
        nodes.append({"id": rid, "type": "role", "label": r["role"], "confidence": r.get("confidence")})
        edges.append({"from": f"teacher:{t}", "rel": "has_role", "to": rid})
    for h in snap["handoffs"]:
        cid = f"role:{h['counterparty_role']}"
        nodes.append({"id": cid, "type": "counterparty_role", "label": h["counterparty_role"]})
        edges.append({"from": f"teacher:{t}", "rel": f"hands_off_{h['direction']}", "to": cid,
                      "what": h["what"], "resolved": bool(h["resolved"]), "gap": h["gap"]})
        for p in h["resolved"]:
            nid = f"person:{p['display_name']}"
            nodes.append({"id": nid, "type": "person", "label": p["display_name"], "authorized": p.get("authorized")})
            edges.append({"from": cid, "rel": "filled_by", "to": nid})
    # de-dup nodes by id
    seen, uniq = set(), []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"]); uniq.append(n)
    return {"nodes": uniq, "edges": edges, "node_count": len(uniq), "edge_count": len(edges),
            "human_review_required": True}


def confirmation_checklist(snap: dict | None = None) -> dict:
    """What the teacher should confirm/correct: anything not teacher_stated/high, or an unresolved link."""
    snap = snap or snapshot()
    items = []
    for r in snap["roles"]:
        if r.get("provenance") != "teacher_stated" or r.get("confidence") != "high":
            items.append({"field": f"role: {r['role']}", "why": f"provenance={r.get('provenance')} "
                          f"confidence={r.get('confidence')}", "action": "confirm or correct"})
    if not snap["school"].get("name"):
        items.append({"field": "school", "why": snap["school"].get("gap", "unresolved"),
                      "action": "set a valid school_msid (shared/schools/)"})
    for h in snap["handoffs"]:
        if h["gap"]:
            items.append({"field": f"handoff: {h['what']} -> {h['counterparty_role']}", "why": h["gap"],
                          "action": "provide the person (authorized source) or confirm role-only"})
    return {"profile_source": snap["profile_source"], "to_confirm": items, "count": len(items),
            "note": "teacher-stated facts need no confirmation; this lists inferences + unresolved links",
            "human_review_required": True}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Light context-confirmation spine (offline).")
    ap.add_argument("--snapshot", action="store_true", help="unified situation snapshot")
    ap.add_argument("--graph", action="store_true", help="light relationship graph (nodes + edges)")
    ap.add_argument("--confirm", action="store_true", help="confirmation checklist")
    a = ap.parse_args(argv)
    if a.graph:
        print(json.dumps(graph(), indent=2, ensure_ascii=False))
    elif a.confirm:
        print(json.dumps(confirmation_checklist(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(snapshot(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
