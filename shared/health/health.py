#!/usr/bin/env python3
"""Skill-health & repair engine (offline, stdlib) — Area 5 of the capability roadmap.

Three jobs, fused from patterns that worked in the prior system (doctor.py readiness, skill-observability
traces, skill-regression suites):
  1. SCAN     — a doctor-style readiness sweep of every skill + shared engine (invariants, MAINTAINER,
                evals, routing membership, importability) -> readiness score + band + blocking issues.
  2. DIAGNOSE — read the audit trail (Quality Ledger + optional runtime traces / decision records with
                execution_trace / minority_report) and summarize recurring problems in plain language.
  3. IMPACT   — when a skill is added/renamed, list every ecosystem file that must be updated so docs,
                routing, ontology, and status never silently drift.
Then it emits a human-readable REPAIR PLAN (ordered, severity-tagged, each step marked mechanical or
judgment) that a human edits or approves — nothing high-stakes is auto-applied. human_review_required.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"
ROUTING = ROOT / "shared" / "routing" / "routing.json"
LEDGER = ROOT / "ledger" / "ledger.json"
ONTOLOGY = ROOT / "shared" / "ontology" / "artifact-types.json"
# Files that must mention a skill so nothing drifts when one is added/renamed (impact analysis targets).
ECOSYSTEM_REFS = ["shared/routing/routing.json", "ROUTING_MODEL.md",
                  "skills/teacher-core/references/routing-map.md", "STATE.md", "METRICS.md",
                  "shared/ontology/artifact-types.json"]
# Shared engines we expect to import cleanly (module, dir-on-path).
ENGINES = [("docintel", "shared"), ("routing.router", "shared"), ("traversal", "shared"),
           ("connectors", "shared/connectors"), ("students", "shared/students"),
           ("records", "shared/records"), ("context", "shared/context")]
BANDS = [(90, "strong"), (70, "usable_with_warnings"), (40, "partial"), (0, "not_ready")]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _band(score: int) -> str:
    for threshold, name in BANDS:
        if score >= threshold:
            return name
    return "not_ready"


def _frontmatter_name(skill_md: Path) -> Optional[str]:
    for line in skill_md.read_text(encoding="utf-8", errors="ignore").splitlines()[:12]:
        if line.strip().startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def discover_skills() -> List[str]:
    return sorted(d.name for d in SKILLS.iterdir() if (d / "SKILL.md").exists()) if SKILLS.exists() else []


def _load_routing() -> dict:
    return json.loads(ROUTING.read_text(encoding="utf-8")) if ROUTING.exists() else {}


# --------------------------------------------------------------------------- 1. SCAN
def scan_skills() -> List[dict]:
    routing = _load_routing()
    routed = set(routing.get("skills", {})) | set(routing.get("meeting_routes", {}).values())
    out = []
    for name in discover_skills():
        d = SKILLS / name
        issues: List[dict] = []
        if _frontmatter_name(d / "SKILL.md") != name:
            issues.append({"severity": "blocking", "issue": "SKILL.md name != folder", "mechanical": False})
        if not (d / "MAINTAINER.md").exists():
            issues.append({"severity": "blocking", "issue": "missing MAINTAINER.md", "mechanical": True})
        ev = d / "evals" / "evals.json"
        if not ev.exists() or not json.loads(ev.read_text(encoding="utf-8") or "{}").get("evals"):
            issues.append({"severity": "warning", "issue": "no eval cases", "mechanical": False})
        for ref in ("references/method.md", "references/quality-gates.md"):
            if not (d / ref).exists():
                issues.append({"severity": "blocking", "issue": f"missing synced {ref}", "mechanical": True})
        if name not in routed and name not in ("teacher-core",):
            issues.append({"severity": "info", "issue": "not referenced in routing.json", "mechanical": True})
        out.append({"skill": name, "issues": issues})
    return out


def scan_engines() -> List[dict]:
    out = []
    for mod, rel in ENGINES:
        p = str(ROOT / rel)
        if p not in sys.path:
            sys.path.insert(0, p)
        try:
            importlib.import_module(mod)
            out.append({"engine": mod, "importable": True})
        except Exception as exc:
            out.append({"engine": mod, "importable": False, "error": f"{exc.__class__.__name__}: {exc}"})
    return out


def check_routing() -> List[dict]:
    routing = _load_routing()
    skills = set(discover_skills())
    problems = []
    targets = set(routing.get("skills", {})) | {
        v for v in routing.get("meeting_routes", {}).values() if v != routing.get("fallback")}
    for t in sorted(targets):
        if t not in skills:
            problems.append({"severity": "blocking", "issue": f"routing target '{t}' is not an installed skill",
                             "mechanical": False})
    return problems


# --------------------------------------------------------------------------- 2. DIAGNOSE
def diagnose(traces_dir: Optional[str] = None) -> dict:
    findings: List[dict] = []
    # Quality Ledger: non-Approved decisions + low composites.
    if LEDGER.exists():
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        not_approved = [r for r in ledger if r.get("decision") not in ("Approved", "Conditionally Approved")]
        low = [r for r in ledger if isinstance(r.get("composite"), (int, float)) and r["composite"] < 3.5]
        findings.append({"source": "quality_ledger", "category": "validation",
                         "records": len(ledger), "not_approved": len(not_approved), "low_composite": len(low),
                         "detail": [f"{r['artifact_id']}: {r['decision']}" for r in not_approved][:10]})
    # Optional runtime traces / decision records (observability-style or classifier execution_trace).
    if traces_dir:
        tdir = Path(traces_dir)
        if not tdir.exists() and (ROOT / traces_dir).exists():
            tdir = ROOT / traces_dir
        classes: Dict[str, int] = {}
        minority = 0
        for jf in tdir.rglob("*.json") if tdir.exists() else []:
            try:
                obj = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            blobs = obj if isinstance(obj, list) else [obj]
            for b in blobs:
                if not isinstance(b, dict):
                    continue
                for ev in b.get("execution_trace", []) or []:
                    cls = ev.get("class") or ev.get("failure_class") or "UNKNOWN"
                    classes[cls] = classes.get(cls, 0) + 1
                if b.get("minority_report"):
                    minority += 1
        if classes or minority:
            findings.append({"source": "runtime_traces", "category": "error",
                             "failure_classes": classes, "minority_reports": minority})
    return {"findings": findings, "note": "Runtime execution_traces are ephemeral; pass --traces <dir> to "
            "include saved decision records / observability traces."}


# --------------------------------------------------------------------------- 3. IMPACT
def impact_analysis(skill: str) -> dict:
    present, missing = [], []
    for rel in ECOSYSTEM_REFS:
        p = ROOT / rel
        if p.exists() and skill in p.read_text(encoding="utf-8", errors="ignore"):
            present.append(rel)
        else:
            missing.append(rel)
    return {"skill": skill, "referenced_in": present, "update_needed_in": missing}


# --------------------------------------------------------------------------- assemble + repair
def build_report(traces_dir: Optional[str] = None) -> dict:
    skills = scan_skills()
    engines = scan_engines()
    routing_problems = check_routing()
    score = 100
    blocking, required = [], []
    for s in skills:
        for i in s["issues"]:
            if i["severity"] == "blocking":
                score -= 10
                blocking.append(f"{s['skill']}: {i['issue']}")
                required.append({"severity": "blocking", "area": f"skill:{s['skill']}", "issue": i["issue"],
                                 "action": f"fix {i['issue']} in skills/{s['skill']}/", "mechanical": i["mechanical"]})
            elif i["severity"] == "warning":
                score -= 4
                required.append({"severity": "warning", "area": f"skill:{s['skill']}", "issue": i["issue"],
                                 "action": f"address {i['issue']} in skills/{s['skill']}/", "mechanical": i["mechanical"]})
    for e in engines:
        if not e["importable"]:
            score -= 20
            blocking.append(f"engine {e['engine']}: not importable")
            required.append({"severity": "blocking", "area": f"engine:{e['engine']}", "issue": e.get("error", ""),
                             "action": f"repair import of {e['engine']}", "mechanical": False})
    for p in routing_problems:
        score -= 15
        blocking.append(p["issue"])
        required.append({"severity": "blocking", "area": "routing", "issue": p["issue"],
                         "action": "add the skill or remove the dangling route in shared/routing/routing.json",
                         "mechanical": False})
    score = max(0, score)
    band = _band(score)
    required.sort(key=lambda r: {"blocking": 0, "warning": 1, "info": 2}.get(r["severity"], 3))
    return {
        "tool": "skill-health", "generated_at": _now(),
        "skills_scanned": len(skills), "engines_scanned": len(engines),
        "readiness_score": score, "readiness_band": band,
        "operator_readiness_state": "blocked" if blocking else ("review" if required else "ready"),
        "release_gate_recommendation": "block_until_resolved" if blocking else ("review_before_proceed" if required else "proceed"),
        "blocking_issues": blocking,
        "skills": skills, "engines": engines, "routing_problems": routing_problems,
        "diagnostics": diagnose(traces_dir),
        "repair_plan": required,
        "must_review_docs": ["CHANGE_MANAGEMENT.md", "tools/skill-maintenance.md", "protocols/quality-gates.md"] if required else [],
        "human_review_required": True,
    }


def to_summary_md(report: dict) -> str:
    lines = ["# Skill-health report", "",
             f"- readiness: **{report['readiness_score']}/100 ({report['readiness_band']})** — "
             f"state: {report['operator_readiness_state']}; gate: {report['release_gate_recommendation']}",
             f"- skills scanned: {report['skills_scanned']} · engines: {report['engines_scanned']}",
             f"- blocking issues: {len(report['blocking_issues'])}", ""]
    if report["blocking_issues"]:
        lines += ["## Blocking", *[f"- {b}" for b in report["blocking_issues"]], ""]
    if report["repair_plan"]:
        lines += ["## Repair plan (edit or approve — nothing high-stakes auto-applies)"]
        for i, step in enumerate(report["repair_plan"], 1):
            tag = "mechanical" if step.get("mechanical") else "judgment"
            lines.append(f"{i}. [{step['severity']}/{tag}] {step['area']} — {step['action']}")
        lines.append("")
    diag = report["diagnostics"]["findings"]
    if diag:
        lines += ["## Diagnostics (from the audit trail)"]
        for f in diag:
            lines.append(f"- {f['source']} ({f['category']}): " +
                         ", ".join(f"{k}={v}" for k, v in f.items() if k not in ("source", "category", "detail")))
        lines.append("")
    lines.append("_Decision support — a human owns the fix. human_review_required: true._")
    return "\n".join(lines) + "\n"


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Skill-health & repair (offline).")
    ap.add_argument("--scan", action="store_true", help="full readiness report (JSON)")
    ap.add_argument("--summary", action="store_true", help="human-readable summary (Markdown)")
    ap.add_argument("--diagnose", action="store_true", help="audit-trail diagnostics only")
    ap.add_argument("--impact", metavar="SKILL", help="which ecosystem files must update for this skill")
    ap.add_argument("--traces", metavar="DIR", help="dir of saved decision records / observability traces")
    a = ap.parse_args(argv)
    if a.impact:
        print(json.dumps(impact_analysis(a.impact), indent=2))
    elif a.diagnose:
        print(json.dumps(diagnose(a.traces), indent=2))
    elif a.summary:
        print(to_summary_md(build_report(a.traces)), end="")
    else:
        print(json.dumps(build_report(a.traces), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
