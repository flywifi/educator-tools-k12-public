#!/usr/bin/env python3
"""Student profile helper — lookup, identification mode, ePHI safety, SIS<->local reconcile (offline).

Loads the gitignored local store (students.local.json) if present, else the committed PLACEHOLDER
example (students.example.json). Renders a student reference per the identification mode (name | id),
surfaces plan flags + the medical action plan with a safety banner, and flags SIS<->local conflicts
(never auto-merges). Policy: student-data-policy.md. Stdlib only, no network.

Usage:
  python3 shared/students/students.py --list
  python3 shared/students/students.py --get S-000123 [--mode name|id]
  python3 shared/students/students.py --reconcile <sis_export.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = HERE / "students.local.json"          # gitignored real store (may be absent)
EXAMPLE = HERE / "students.example.json"        # committed placeholders


def load_store() -> tuple[dict, str]:
    """Prefer the gitignored local store; fall back to the placeholder example."""
    path = LOCAL if LOCAL.exists() else EXAMPLE
    return json.loads(path.read_text(encoding="utf-8")), path.name


def _index(store: dict) -> dict:
    return {s["student_id"]: s for s in store.get("students", [])}


def find(store: dict, key: str) -> dict | None:
    by_id = _index(store)
    if key in by_id:
        return by_id[key]
    k = key.strip().lower()
    for s in store.get("students", []):
        full = f"{s.get('first_name', '')} {s.get('last_name', '')}".strip().lower()
        if k in (full, s.get("preferred_name", "").lower()):
            return s
    return None


def render_ref(s: dict, mode: str) -> str:
    """How to refer to the student in a record/handoff, per the identification mode."""
    if mode == "id":
        return f"student {s['student_id']}"
    name = (s.get("preferred_name") or f"{s.get('first_name', '')} {s.get('last_name', '')}").strip()
    return f"{name or '(name unknown)'} ({s['student_id']})"


def show(s: dict, mode: str) -> None:
    print(render_ref(s, mode) + f"   grade {s.get('grade', '?')}")
    flags = [k for k, v in (s.get("plan_flags") or {}).items() if v]
    if flags:
        print("  plan flags:", ", ".join(flags))
    if mode != "id":
        for g in s.get("guardians", []):
            tag = " [emergency]" if g.get("is_emergency_contact") else ""
            primary = "primary " if g.get("primary") else ""
            print(f"  guardian: {primary}{g.get('name')} ({g.get('relationship','?')}) "
                  f"{g.get('phone','')} {g.get('email','')}{tag}")
    else:
        print(f"  guardians: {len(s.get('guardians', []))} on file (names hidden in ID-only mode)")
    for hp in s.get("health_plans", []):
        print("\n  *** STUDENT HEALTH INFO — SAFETY-CRITICAL (ePHI) ***")
        print(f"      condition: {hp.get('condition')}  [{hp.get('severity','')}]")
        print(f"      medications: {', '.join(hp.get('medications', []))}")
        print(f"      when/where: {hp.get('when_where_to_administer') or hp.get('instructions','')}")
        print(f"      protocol:   {hp.get('emergency_protocol')}")
        sig = "signed" if hp.get("signed") else "unsigned"
        print(f"      source:     {hp.get('source_type','?')} [{hp.get('source_authority','?')} authority, {sig}] — "
              f"{hp.get('source','')}  (effective {hp.get('effective_dates','?')})")
        print("      >> Quote verbatim from the source on file (attributed; a signature is not required); "
              "never fabricate. Defer to the school nurse / 911.")


def reconcile(store: dict, sis_path: str, mode: str) -> int:
    """Flag SIS<->local conflicts per field. SIS is authoritative; recommend but do NOT auto-update."""
    sis = json.loads(Path(sis_path).read_text(encoding="utf-8"))
    sis_idx, loc_idx = _index(sis), _index(store)
    conflicts = 0
    for sid, srec in sis_idx.items():
        lrec = loc_idx.get(sid)
        if not lrec:
            print(f"  [SIS only] {sid} — present in SIS, absent locally (add from SIS?)")
            conflicts += 1
            continue
        for field in ("first_name", "last_name", "grade"):
            sv, lv = srec.get(field), lrec.get(field)
            if sv is not None and lv is not None and sv != lv:
                print(f"  [CONFLICT] {sid} {field}: SIS={sv!r} vs local={lv!r}")
                conflicts += 1
        if (srec.get("plan_flags") or {}) != (lrec.get("plan_flags") or {}):
            print(f"  [CONFLICT] {sid} plan_flags: SIS={srec.get('plan_flags')} vs local={lrec.get('plan_flags')}")
            conflicts += 1
    if not conflicts:
        print("  no SIS<->local conflicts found.")
    else:
        print(f"\n  {conflicts} conflict(s). RECOMMENDATION: SIS is authoritative (use SIS-first), but "
              "do NOT auto-update —")
        print("  raise with the user: which source wins, and should the local record be updated? "
              "(see student-data-policy.md)")
    return conflicts


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Student profile helper (offline).")
    ap.add_argument("--list", action="store_true", help="list profiles in the active store")
    ap.add_argument("--get", metavar="ID_OR_NAME", help="show one profile")
    ap.add_argument("--mode", choices=["name", "id"], default="name", help="identification mode (default name)")
    ap.add_argument("--reconcile", metavar="SIS_JSON", help="flag SIS<->local conflicts (no auto-update)")
    a = ap.parse_args(argv)

    store, src = load_store()
    banner = "PLACEHOLDER example" if src == "students.example.json" else "local (gitignored) store"
    print(f"[store: {src} — {banner}]\n")

    if a.reconcile:
        return 1 if reconcile(store, a.reconcile, a.mode) else 0
    if a.get:
        s = find(store, a.get)
        if not s:
            print(f"  no student matches {a.get!r}")
            return 1
        show(s, a.mode)
        return 0
    # default / --list
    print(f"profiles ({len(store.get('students', []))}):  [identification mode: {a.mode}]")
    for s in store.get("students", []):
        flags = [k for k, v in (s.get("plan_flags") or {}).items() if v]
        med = "  [MEDICAL ACTION PLAN]" if s.get("health_plans") else ""
        print(f"  - {render_ref(s, a.mode)}  grade {s.get('grade','?')}  {','.join(flags)}{med}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
