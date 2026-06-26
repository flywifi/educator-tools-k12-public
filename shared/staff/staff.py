#!/usr/bin/env python3
"""Staff / role directory (offline, stdlib) — RFC-F001 V2 workstream D. GATED + authorized-first.

Resolves a teacher-profile handoff ROLE (case_manager, assistant_principal, counselor, ...) to a real
person, so a handoff can name who it goes to. This is the privacy-sensitive workstream: it is OFF by
default and authorized-first (see staff-data-policy.md). With no authorization it runs in read-only
PLACEHOLDER mode and never ingests; any ingest path is a recorded gap, not a silent crawl.

Loads the gitignored local store (staff.local.json) when present + authorized, else the committed
PLACEHOLDER example. Querying placeholders is fine (it's fake data); the gate governs INGEST, not lookup.

Usage:
  python3 shared/staff/staff.py --status                         # gate state + source
  python3 shared/staff/staff.py --role case_manager             # resolve a role -> person(s)
  python3 shared/staff/staff.py --school 480002 --list          # directory for a school
  python3 shared/staff/staff.py --resolve-handoffs              # map teacher-profile handoffs -> people
  python3 shared/staff/staff.py --ingest teacher_provided --file people.json   # gated; needs authorization
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LOCAL = HERE / "staff.local.json"            # gitignored real store (may be absent)
EXAMPLE = HERE / "staff.example.json"          # committed placeholders
PROFILE_LOCAL = ROOT / "shared" / "context" / "profiles" / "teacher.local.json"
PROFILE_EXAMPLE = ROOT / "shared" / "context" / "profiles" / "teacher.example.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def authorized() -> bool:
    """Ingest is allowed ONLY under an explicit, recorded deployment authorization."""
    return os.environ.get("STAFF_INGEST_AUTHORIZED", "").lower() in ("1", "true", "yes")


def load_store() -> tuple[dict, str]:
    """Prefer the gitignored local store (only if authorized); else the placeholder example."""
    if LOCAL.exists() and authorized():
        return json.loads(LOCAL.read_text(encoding="utf-8")), "staff.local.json"
    return json.loads(EXAMPLE.read_text(encoding="utf-8")), "staff.example.json"


def status() -> dict:
    store, src = load_store()
    return {"gate": "authorized" if authorized() else "off (default)",
            "ingest_allowed": authorized(),
            "source": src,
            "ingest_mode": store.get("ingest_mode", "off"),
            "records": len(store.get("staff", [])),
            "note": "set STAFF_INGEST_AUTHORIZED=true + choose a source to ingest; see staff-data-policy.md",
            "human_review_required": True}


def by_role(store: dict, role: str) -> list[dict]:
    return [s for s in store.get("staff", []) if s.get("role") == role]


def ingest(mode: str, file: str | None) -> dict:
    """Gated ingest. Without authorization this records a GAP and writes nothing."""
    if not authorized():
        return {"status": "refused", "reason": "STAFF_INGEST_AUTHORIZED not set — ingest is off by default",
                "recorded_as": "gap", "policy": "shared/staff/staff-data-policy.md",
                "human_review_required": True}
    if mode == "public_crawl":
        # The shell does not crawl; a real deployment must additionally honor robots.txt + ToS per-fetch.
        return {"status": "not_implemented_in_shell", "reason": "public crawl is robots/ToS-gated; "
                "use the traversal crawler under authorization, then import the result",
                "human_review_required": True}
    if mode in ("authorized_directory", "teacher_provided"):
        if not file or not Path(file).exists():
            return {"status": "error", "detail": f"--file required and must exist for mode '{mode}'"}
        incoming = json.loads(Path(file).read_text(encoding="utf-8"))
        members = incoming.get("staff", incoming if isinstance(incoming, list) else [])
        for m in members:
            m.setdefault("provenance", mode)
            m["authorized"] = True
            m.setdefault("consent", f"authorized via {mode} on {_now()}")
        out = {"school_msid": incoming.get("school_msid", "unknown"),
               "school_name": incoming.get("school_name"),
               "ingest_mode": mode, "authorized": True, "generated": _now(), "staff": members}
        LOCAL.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        return {"status": "ingested", "mode": mode, "records": len(members),
                "path": "shared/staff/staff.local.json (gitignored)", "human_review_required": True}
    return {"status": "error", "detail": f"unknown ingest mode '{mode}'"}


def resolve_handoffs() -> dict:
    """Map the teacher profile's handoff counterparty_roles to people in the directory (best-effort)."""
    ppath = PROFILE_LOCAL if PROFILE_LOCAL.exists() else PROFILE_EXAMPLE
    profile = json.loads(ppath.read_text(encoding="utf-8"))
    store, src = load_store()
    out = []
    for h in profile.get("handoffs", []):
        role = h.get("counterparty_role")
        people = by_role(store, role)
        out.append({"what": h.get("what"), "direction": h.get("direction"), "counterparty_role": role,
                    "resolved": [{"display_name": p.get("display_name"), "work_email": p.get("work_email"),
                                  "authorized": p.get("authorized")} for p in people],
                    "gap": None if people else f"no '{role}' in directory ({src})"})
    return {"profile_source": str(ppath.relative_to(ROOT)), "directory_source": src,
            "handoffs": out, "note": "person links require an authorized source + teacher confirmation",
            "human_review_required": True}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Staff/role directory — gated, authorized-first (offline).")
    ap.add_argument("--status", action="store_true", help="gate state + source")
    ap.add_argument("--role", help="resolve a role to person(s)")
    ap.add_argument("--school", help="filter by school MSID")
    ap.add_argument("--list", action="store_true", help="list the directory")
    ap.add_argument("--resolve-handoffs", action="store_true", help="map teacher-profile handoffs to people")
    ap.add_argument("--ingest", choices=["authorized_directory", "teacher_provided", "public_crawl"],
                    help="gated ingest (requires STAFF_INGEST_AUTHORIZED)")
    ap.add_argument("--file", help="source file for --ingest")
    a = ap.parse_args(argv)

    if a.ingest:
        print(json.dumps(ingest(a.ingest, a.file), indent=2))
        return 0
    if a.status:
        print(json.dumps(status(), indent=2))
        return 0
    if a.resolve_handoffs:
        print(json.dumps(resolve_handoffs(), indent=2, ensure_ascii=False))
        return 0
    store, src = load_store()
    rows = store.get("staff", [])
    if a.school:
        rows = [s for s in rows if s.get("school_msid") == a.school]
    if a.role:
        rows = [s for s in rows if s.get("role") == a.role]
    banner = "PLACEHOLDER example" if src == "staff.example.json" else "local (gitignored) store"
    print(json.dumps({"source": f"{src} ({banner})", "count": len(rows), "staff": rows,
                      "human_review_required": True}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
