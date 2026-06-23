#!/usr/bin/env python3
"""Assemble a governed student HANDOFF PACKAGE so information travels consistently across handoffs.

Three package types — `skill_to_skill` (the runtime envelope between TOS skills; primary),
`teacher_to_teacher` (year-end), `school_transfer` (mobility) — composed from the shared Academic
Handoff Package. Identity/guardians/health come from ../students/ (rendered per identification mode);
connector availability/restrictions come from ../connectors/. Core fields are always present; extended
data lives under `modules` and is included only for ENABLED modules (records_modules / --modules), so a
deployment opts in per category rather than to one massive set. Health is surfaced verbatim from the
source on file (attributed; a signature is NOT required), never fabricated; defer to the nurse / 911.

Every package carries the metadata block + `human_review_required: true` (protocols/metadata-schema.md).
Repo data is placeholders only; real records live in records.local.json (gitignored) or a live SIS.
Stdlib only, offline.

Usage:
  python3 shared/records/records.py --list-modules
  python3 shared/records/records.py --setup-module transportation
  python3 shared/records/records.py --package skill_to_skill --student S-000123 [--mode name|id]
       [--modules gradebook,transportation | all] [--flags <connector-flags.json>] [--next-skill ...]
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LOCAL = HERE / "records.local.json"      # gitignored real store (may be absent)
EXAMPLE = HERE / "records.example.json"   # committed placeholders

sys.path.insert(0, str(ROOT / "shared" / "students"))
sys.path.insert(0, str(ROOT / "shared" / "connectors"))
try:
    import students as stu   # type: ignore
except Exception:            # pragma: no cover - optional at runtime
    stu = None
try:
    import connectors as conn  # type: ignore
except Exception:             # pragma: no cover
    conn = None

# Extended-module catalog (core is always on; these are the independently feature-flagged categories).
MODULES = {
    "gradebook":      {"sensitivity": "moderate", "label": "Gradebook — assignments, rubrics, submissions, grade calc, grading policy, competencies"},
    "assessments":    {"sensitivity": "moderate", "label": "Assessments catalog + scores (diagnostic/benchmark/state/AP/IB/SAT/ACT)"},
    "curriculum":     {"sensitivity": "low",      "label": "Course catalog, curriculum, subjects, learning objectives"},
    "scheduling":     {"sensitivity": "low",      "label": "Scheduling & placement, section capacity/occupancy"},
    "transportation": {"sensitivity": "moderate", "label": "Transportation profile + dismissal plan"},
    "activities":     {"sensitivity": "low",      "label": "Athletics, activities, leadership, service learning"},
    "credentials":    {"sensitivity": "low",      "label": "Credentials + portfolio"},
    "discipline":     {"sensitivity": "high",     "label": "Discipline incident detail (beyond core behavior summary)"},
    "counseling":     {"sensitivity": "high",     "label": "Counseling detail (beyond core counseling summary)"},
    "communications": {"sensitivity": "moderate", "label": "Communications log"},
    "documents":      {"sensitivity": "depends_on_content", "label": "Document repository"},
    "health_detail":  {"sensitivity": "high",     "label": "Extended health records — multi-source, attributed (ePHI)"},
    "state_reporting":{"sensitivity": "high",     "label": "State student id + demographics for state reporting"},
}
PACKAGES = ("skill_to_skill", "teacher_to_teacher", "school_transfer")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------- stores
def load_records_store() -> tuple[dict, str]:
    path = LOCAL if LOCAL.exists() else EXAMPLE
    return json.loads(path.read_text(encoding="utf-8")), path.name


def find_record(store: dict, student_id: str) -> dict | None:
    for r in store.get("records", []):
        if r.get("student_id") == student_id:
            return r
    return None


def resolve_modules(flags: dict, cli_modules: str | None) -> list[str]:
    """Enabled modules from --modules (list|all) or the deployment flag `records_modules`; default none."""
    if cli_modules:
        if cli_modules.strip().lower() == "all":
            return list(MODULES)
        wanted = [m.strip() for m in cli_modules.split(",") if m.strip()]
    else:
        raw = flags.get("records_modules", []) or []
        wanted = ["all"] if raw == "all" else list(raw)
        if wanted == ["all"]:
            return list(MODULES)
    return [m for m in wanted if m in MODULES]


# --------------------------------------------------------------------------- people
def render_student(profile: dict, student_id: str, mode: str) -> str:
    if profile and stu is not None:
        return stu.render_ref(profile, mode)
    return f"student {student_id}"


def guardians_block(profile: dict | None, mode: str):
    gs = (profile or {}).get("guardians", []) or []
    if not gs:
        return None
    if mode == "id":
        return {"count": len(gs), "note": "names/contacts hidden in id-only mode; resolve on demand"}
    return [{"name": g.get("name"), "relationship": g.get("relationship"), "phone": g.get("phone"),
             "email": g.get("email"), "primary": g.get("primary", False),
             "emergency_contact": g.get("is_emergency_contact", False)} for g in gs]


def medical_banner(profile: dict | None, include_full: bool):
    """Safety-critical health banner, surfaced verbatim from the source on file (attributed), never made up."""
    hps = (profile or {}).get("health_plans", []) or []
    if not hps:
        return None
    items = []
    for hp in hps:
        item = {
            "condition": hp.get("condition"), "severity": hp.get("severity"),
            "instructions": hp.get("when_where_to_administer") or hp.get("instructions"),
            "medications": hp.get("medications", []),
            "emergency_protocol": hp.get("emergency_protocol"),
            "source_type": hp.get("source_type"), "source_authority": hp.get("source_authority"),
            "signed": hp.get("signed", False), "source": hp.get("source"),
        }
        if include_full:  # health_detail module adds the full record fidelity
            item.update({"action_plan_ref": hp.get("action_plan_ref"),
                         "provided_by": hp.get("provided_by"),
                         "effective_dates": hp.get("effective_dates"),
                         "last_verified": hp.get("last_verified")})
        items.append(item)
    return {
        "safety_critical": True,
        "surface_from": "the source on file (attributed; a signature is NOT required) — never fabricate",
        "defer_to": "school nurse / 911 in an emergency",
        "items": items,
    }


# --------------------------------------------------------------------------- payload
def academic_package(record: dict, modules: list[str]) -> dict:
    pkg = {
        "academic_summary": {
            "grade_level": record.get("current_grade_level"),
            "school": record.get("current_school"),
            "academic_year": record.get("academic_year"),
        },
        "course_history": record.get("course_history", []),
        "course_grades": record.get("course_grades", []),
        "standards_mastery": record.get("standards_mastery", []),
        "active_interventions": record.get("active_interventions", []),
        "active_accommodations": record.get("active_accommodations", []),
        "attendance_summary": record.get("attendance_summary", {}),
        "behavior_summary": record.get("behavior_summary", {}),
        "counseling_summary": record.get("counseling_summary", {}),
        "teacher_recommendations": record.get("teacher_recommendations", []),
        "teacher_notes": record.get("teacher_notes", []),
        "parent_contact_summary": record.get("parent_contact_summary", []),
    }
    available = record.get("modules", {}) or {}
    included = {m: available[m] for m in modules if m in available}
    if included:
        pkg["modules"] = included
    return pkg


def connector_view(flags: dict) -> dict:
    if conn is None:
        return {"states": {}, "active": [], "restrictions": {}, "restricted_notes": [], "gaps": []}
    return conn.resolve(flags)


def metadata_block(package_type: str, record: dict, mode: str, modules: list[str],
                   records_src: str, confidence: str, context: dict | None) -> dict:
    return {
        "decision_id": _id("dec"),
        "artifact_id": _id("pkg"),
        "artifact_type": f"handoff-package:{package_type}",
        "reviewer": "shared/records/records.py (assembler — not a determination)",
        "date": _now(),
        "identification_mode": mode,
        "modules_included": modules,
        "context": context,
        "confidence": confidence,
        "provenance": {
            "generated_by": "shared/records/records.py",
            "records_store": records_src,
            "identity_health_store": "shared/students/",
            "lifecycle_audit_maps_to": "protocols/metadata-schema.md",
        },
        "human_review_required": True,
    }


def build_package(package_type: str, student_id: str, mode: str = "name",
                  modules: list[str] | None = None, flags: dict | None = None,
                  next_skill: str | None = None, context: dict | None = None) -> dict:
    flags = flags or {}
    modules = modules if modules is not None else resolve_modules(flags, None)
    store, records_src = load_records_store()
    record = find_record(store, student_id) or {"student_id": student_id}
    profile = stu.find(stu.load_store()[0], student_id) if stu is not None else None

    plan = connector_view(flags)
    restricted = plan.get("restricted_notes", [])
    blocked = [c for c, s in plan.get("states", {}).items() if s in ("disabled", "permission_blocked")]
    degraded = bool(restricted) or bool(blocked)
    confidence = "medium" if degraded else "high"

    trace = [{"event": "assembled", "class": "SUCCESS",
              "detail": f"record from {records_src}; identity/health from shared/students/"}]
    for n in restricted:
        trace.append({"event": "restricted_source", "class": "PERMISSION",
                      "detail": f"{n['connector']} restricted from {n['evidence']} ({n['reason']})"})
    if degraded:
        trace.append({"event": "degraded_path", "class": "DEGRADED_SUCCESS",
                      "detail": "a source is blocked/restricted; confidence lowered; converge on available evidence"})

    academic = academic_package(record, modules)
    pkg = {
        "package_type": package_type,
        "subject_student": render_student(profile, student_id, mode),
        "identification_mode": mode,
        "modules_included": modules,
        "context": context,
        "academic_package": academic,
        "guardians": guardians_block(profile, mode),
        "medical_safety_banner": medical_banner(profile, include_full=("health_detail" in modules)),
        "source_availability": plan.get("states", {}),
        "restricted_sources": plan.get("restrictions", {}),
        "execution_trace": trace,
        "source_decisions": None,
        "minority_report": None,
        "recommended_next_skill": next_skill,
        "lifecycle": record.get("lifecycle"),
        "human_review_required": True,
        "metadata": metadata_block(package_type, record, mode, modules, records_src, confidence, context),
    }

    if package_type == "teacher_to_teacher":
        # Year-end: focus the payload on what next year's teacher needs.
        keep = ("academic_summary", "course_grades", "standards_mastery", "active_accommodations",
                "active_interventions", "attendance_summary", "behavior_summary",
                "teacher_recommendations", "teacher_notes")
        pkg["academic_package"] = {k: academic[k] for k in keep if k in academic}
        if "modules" in academic:
            pkg["academic_package"]["modules"] = academic["modules"]
    elif package_type == "school_transfer":
        pkg["transition_handoff"] = {
            "handoff_id": _id("ho"),
            "student_id": student_id,
            "origin_school": record.get("current_school"),
            "destination_school": None,  # filled when the receiving school is known
            "effective_date": _now()[:10],
        }
        pkg["mobility_history"] = record.get("mobility_history", [])
        pkg["educational_timeline"] = record.get("educational_timeline", [])
    return pkg


# --------------------------------------------------------------------------- CLI
def cmd_list_modules() -> None:
    print("core baseline: always on (identity, enrollment, grades summary, standards mastery, "
          "interventions/accommodations, attendance/behavior/health/counseling summaries, the 3 packages,\n"
          "               educational timeline, mobility history, transition handoff).\n")
    print(f"extended modules ({len(MODULES)}) — enable per category via records_modules / --modules:")
    for mid, m in MODULES.items():
        print(f"  - {mid:15} [{m['sensitivity']:18}] {m['label']}")
    print('\n"all" enables every module (the "full" shorthand).')


def cmd_setup_module(mid: str) -> int:
    m = MODULES.get(mid)
    if not m:
        print(f"unknown module {mid!r}. See --list-modules.")
        return 1
    print(f"setup checklist — module '{mid}'  [{m['sensitivity']} sensitivity]\n  {m['label']}\n")
    steps = [
        "Confirm the district/school authorizes sharing this category (minimum-necessary).",
        "Identify the source: a live SIS/connector, or an upload read via shared/docintel/.",
        f"Add \"{mid}\" to records_modules in the deployment feature-flags file.",
        "Map only the minimum-necessary fields; keep real data out of any tracked/committed file.",
    ]
    if m["sensitivity"] == "high":
        steps.insert(1, "Run a data-privacy review (high-sensitivity ePHI/PII) and record the basis for access.")
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s}")
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Assemble a governed student handoff package (offline).")
    ap.add_argument("--package", choices=PACKAGES, help="which handoff package to build")
    ap.add_argument("--student", help="student_id (join key)")
    ap.add_argument("--mode", choices=["name", "id"], default="name", help="identification mode")
    ap.add_argument("--modules", help="enabled modules: comma list or 'all' (default: none / core only)")
    ap.add_argument("--flags", metavar="CONFIG", help="per-deployment feature-flags JSON")
    ap.add_argument("--next-skill", dest="next_skill", help="recommended next skill (skill_to_skill)")
    ap.add_argument("--list-modules", action="store_true", help="list the extended-module catalog")
    ap.add_argument("--setup-module", metavar="ID", help="print a module's setup checklist")
    a = ap.parse_args(argv)

    if a.list_modules:
        cmd_list_modules()
        return 0
    if a.setup_module:
        return cmd_setup_module(a.setup_module)
    if not (a.package and a.student):
        ap.error("provide --package and --student (or use --list-modules / --setup-module)")

    flags = json.loads(Path(a.flags).read_text(encoding="utf-8")) if a.flags else {}
    modules = resolve_modules(flags, a.modules)
    pkg = build_package(a.package, a.student, a.mode, modules, flags, a.next_skill)
    print(json.dumps(pkg, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
