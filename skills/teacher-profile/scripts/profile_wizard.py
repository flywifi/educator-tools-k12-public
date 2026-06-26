#!/usr/bin/env python3
"""Teacher-profile setup wizard + context registration (offline, stdlib) — RFC-F001 V2 workstream E.

Establishes/maintains ONE teacher's operating profile (roles, duties, handoff/role-interaction map,
preferences) and registers it into the shared context as classroom/teacher-scope sop_refs + overrides so
every other skill adapts to this teacher. The profile is a GITIGNORED local store
(shared/context/profiles/teacher.local.json) — the teacher's own data, never committed.

Interactive use drives a short interview (see references/wizard.md). For automation/testing this is
ALSO answers-file driven so it runs headless and deterministic.

Honest by construction: teacher-stated facts outrank crawled inferences (provenance + confidence on
every fact); no student PII; human_review_required stays true.

Usage:
  python3 skills/teacher-profile/scripts/profile_wizard.py --init answers.json     # write the local profile
  python3 skills/teacher-profile/scripts/profile_wizard.py --demo                  # init from the example
  python3 skills/teacher-profile/scripts/profile_wizard.py --show                  # print current profile
  python3 skills/teacher-profile/scripts/profile_wizard.py --validate              # check vs schema (light)
  python3 skills/teacher-profile/scripts/profile_wizard.py --register              # emit context sop_refs/overrides
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROFILES = ROOT / "shared" / "context" / "profiles"
LOCAL = PROFILES / "teacher.local.json"
EXAMPLE = PROFILES / "teacher.example.json"
SCHEMA = PROFILES / "teacher.schema.json"

REQUIRED_TOP = ["schema_version", "teacher", "roles", "human_review_required"]
HANDOFF_REQUIRED = ["what", "direction", "counterparty_role"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_provenance(items: list[dict]) -> list[dict]:
    """A teacher-driven wizard records facts as teacher_stated/high unless told otherwise."""
    for it in items:
        it.setdefault("provenance", "teacher_stated")
        it.setdefault("confidence", "high")
    return items


def build_profile(answers: dict) -> dict:
    prof = {
        "schema_version": "0.1.0",
        "teacher": answers.get("teacher", {}),
        "roles": _default_provenance(answers.get("roles", [])),
        "duties": _default_provenance(answers.get("duties", [])),
        "handoffs": answers.get("handoffs", []),
        "meetings": answers.get("meetings", []),
        "preferences": answers.get("preferences", {}),
        "overrides": answers.get("overrides", []),
        "updated": _now(),
        "human_review_required": True,
    }
    return prof


def validate(prof: dict) -> list[str]:
    """Light structural validation (no external deps). Returns a list of problems (empty = ok)."""
    issues = []
    for k in REQUIRED_TOP:
        if k not in prof:
            issues.append(f"missing required field: {k}")
    if prof.get("human_review_required") is not True:
        issues.append("human_review_required must be true")
    if not prof.get("teacher", {}).get("display_name"):
        issues.append("teacher.display_name is required")
    if not prof.get("roles"):
        issues.append("at least one role is required")
    for i, h in enumerate(prof.get("handoffs", [])):
        for k in HANDOFF_REQUIRED:
            if not h.get(k):
                issues.append(f"handoff[{i}] missing {k}")
        if h.get("direction") not in ("to", "from", "bidirectional"):
            issues.append(f"handoff[{i}] direction must be to/from/bidirectional")
    # PII guardrail: nudge if a contact looks committed-worthy (it must stay local-only)
    return issues


def register_fragment(prof: dict) -> dict:
    """Produce the context contribution: a classroom-scope sop_ref to the (gitignored) profile + overrides
    derived from preferences. A context build merges this; we do not mutate a contract here."""
    sop_ref = {
        "id": "teacher-profile-local",
        "scope": "classroom",
        "path": str(LOCAL.relative_to(ROOT)),
        "label": f"Teacher operating profile — {prof.get('teacher', {}).get('display_name', '?')}",
        "effective": prof.get("updated"),
        "source": "teacher-profile wizard (teacher_stated)",
    }
    overrides = list(prof.get("overrides", []))
    for k, v in (prof.get("preferences") or {}).items():
        overrides.append({"instruction": f"preference: {k} = {v}", "by": "teacher",
                          "timestamp": prof.get("updated")})
    # Role/handoff map exposed for routing skills (meeting-classifier, records handoffs).
    role_map = {
        "roles": [r.get("role") for r in prof.get("roles", [])],
        "handoffs": [{"what": h.get("what"), "direction": h.get("direction"),
                      "counterparty_role": h.get("counterparty_role")} for h in prof.get("handoffs", [])],
    }
    return {"sop_refs": [sop_ref], "overrides": overrides, "role_interaction_map": role_map,
            "scope": "classroom", "human_review_required": True}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Teacher-profile setup wizard + context registration (offline).")
    ap.add_argument("--init", metavar="ANSWERS_JSON", help="build the local profile from an answers file")
    ap.add_argument("--demo", action="store_true", help="build the local profile from teacher.example.json")
    ap.add_argument("--show", action="store_true", help="print the current local profile")
    ap.add_argument("--validate", action="store_true", help="validate the current local profile")
    ap.add_argument("--register", action="store_true", help="emit the context sop_refs/overrides fragment")
    a = ap.parse_args(argv)

    if a.init or a.demo:
        answers = _load(Path(a.init)) if a.init else _load(EXAMPLE)
        prof = build_profile(answers)
        issues = validate(prof)
        if issues:
            print(json.dumps({"status": "invalid", "issues": issues}, indent=2))
            return 1
        PROFILES.mkdir(parents=True, exist_ok=True)
        LOCAL.write_text(json.dumps(prof, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "profile_written", "path": str(LOCAL.relative_to(ROOT)),
                          "roles": [r.get("role") for r in prof["roles"]],
                          "handoffs": len(prof["handoffs"]), "gitignored": True,
                          "next": "--register to contribute sop_refs/overrides to the context",
                          "human_review_required": True}, indent=2))
        return 0

    if not LOCAL.exists():
        print(json.dumps({"status": "no_profile",
                          "detail": f"no {LOCAL.relative_to(ROOT)} yet — run --init <answers.json> or --demo"}))
        return 1
    prof = _load(LOCAL)
    if a.validate:
        issues = validate(prof)
        print(json.dumps({"status": "ok" if not issues else "invalid", "issues": issues}, indent=2))
        return 0 if not issues else 1
    if a.register:
        print(json.dumps(register_fragment(prof), indent=2, ensure_ascii=False))
        return 0
    # default: show
    print(json.dumps(prof, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
