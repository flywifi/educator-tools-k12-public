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
import re
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
ECOSYSTEM_REFS = ["shared/routing/routing.json", "docs/ROUTING_MODEL.md",
                  "skills/core/teacher-core/references/routing-map.md", "STATE.md", "docs/METRICS.md",
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


def _skill_dirs() -> List[Path]:
    # Skills are sub-grouped (core/ educator/ operations/ atoms/); a skill is any dir holding a
    # SKILL.md, found recursively. Leaf folder names stay unique across groups.
    return sorted((p.parent for p in SKILLS.rglob("SKILL.md")), key=lambda p: p.name) if SKILLS.exists() else []


def discover_skills() -> List[str]:
    return [d.name for d in _skill_dirs()]


def _load_routing() -> dict:
    return json.loads(ROUTING.read_text(encoding="utf-8")) if ROUTING.exists() else {}


# --------------------------------------------------------------------------- 1. SCAN
def scan_skills() -> List[dict]:
    routing = _load_routing()
    routed = set(routing.get("skills", {})) | set(routing.get("meeting_routes", {}).values())
    out = []
    for d in _skill_dirs():
        name = d.name
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


# Packages that build a C/C++/Rust extension from source when no prebuilt wheel matches the
# platform/Python version — the "dependency hell" class. Listing one in a requirements file
# without an --only-binary guard risks a compiler error (e.g. lxml needing libxml2) on a
# teacher's machine. Map: dist name -> why it's risky / the safer alternative.
COMPILE_FROM_SOURCE = {
    "lxml": "needs libxml2+libxslt; use stdlib html.parser or --only-binary",
    "numpy": "C/Fortran build; install via wheel only (--only-binary)",
    "scipy": "C/Fortran build; wheel only",
    "pandas": "C build; wheel only",
    "pillow": "C imaging libs; ships wheels — pin --only-binary",
    "pymupdf": "C (MuPDF); ships wheels — pin --only-binary",
    "cryptography": "Rust/OpenSSL build; ships wheels — pin --only-binary",
    "hnswlib": "C++ build, often NO wheel — avoid or --only-binary",
    "annoy": "C++ build, often NO wheel — avoid or --only-binary",
    "faiss-cpu": "C++ build; wheel only",
    "tokenizers": "Rust build; ships wheels — pin --only-binary",
    "psycopg2": "needs libpq+compiler; use psycopg2-binary instead",
    "python-levenshtein": "C build; use the pure-Python 'rapidfuzz' instead",
    "sqlite-vec": "C extension; ships wheels — pin --only-binary",
}


def scan_dependencies() -> List[dict]:
    """Audit every requirements-*.txt for compile-from-source packages without an --only-binary
    guard, and for packages declared but never imported (dead weight). This is the proactive
    'dependency-hell' guard — the failure class is a build error on a teacher's machine, not ours."""
    problems: List[dict] = []
    req_files = sorted(ROOT.glob("tools/requirements-*.txt")) + sorted(ROOT.glob("requirements*.txt"))
    # Cheap "is it imported anywhere" index (import name may differ from dist name).
    import_alias = {"beautifulsoup4": "bs4", "pillow": "PIL", "pymupdf": "fitz",
                    "python-docx": "docx", "python-pptx": "pptx", "scikit-learn": "sklearn",
                    "pyyaml": "yaml", "opencv-python": "cv2"}
    py_text = ""
    for pyf in ROOT.rglob("*.py"):
        if ".harvest-venv" in str(pyf) or "/_" in str(pyf):
            continue
        try:
            py_text += pyf.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    for rf in req_files:
        try:
            lines = rf.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        has_only_binary = any("--only-binary" in ln for ln in lines)  # documented guard counts
        rel = rf.relative_to(ROOT).as_posix()
        for ln in lines:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue  # comments / commented-out deps are not active installs
            name = re.split(r"[<>=!~;\[\s]", s, 1)[0].strip().lower()
            if not name:
                continue
            if name in COMPILE_FROM_SOURCE and not has_only_binary:
                problems.append({
                    "severity": "warning", "mechanical": False, "file": rel, "package": name,
                    "issue": f"compile-from-source dep '{name}' without --only-binary guard "
                             f"({COMPILE_FROM_SOURCE[name]})",
                    "action": f"add '--only-binary=:all:' guidance in {rel}, or drop '{name}' if unused"})
            # dead-weight: a heavy dep that is never imported anywhere
            alias = import_alias.get(name, name.replace("-", "_"))
            if name in COMPILE_FROM_SOURCE and alias not in py_text and f"import {name}" not in py_text:
                problems.append({
                    "severity": "warning", "mechanical": False, "file": rel, "package": name,
                    "issue": f"'{name}' is declared but never imported (dead weight that can still "
                             f"trigger a source build)",
                    "action": f"remove '{name}' from {rel} unless a runtime path needs it"})
    return problems


URL_PROVENANCE = ROOT / "tools" / "url-provenance.json"
# Skip well-known infra/spec hosts that aren't fetch targets we'd ever fabricate.
_URL_SKIP = ("schemastore", "json-schema.org", "w3.org", "python.org", "example.com",
             "localhost", "127.0.0.1", "0.0.0.0", "anthropic.com")
_URL_RE = re.compile(r"https?://[a-zA-Z0-9.\-_/]+")


def scan_url_provenance() -> List[dict]:
    """Every external URL hardcoded in tools/*.py and shared/**/*.py must be DECLARED in
    tools/url-provenance.json with an honest status. An undeclared URL is the fabrication risk
    (an AI can emit a plausible-looking URL that was never verified); this catches it at check
    time instead of as a dead link / 403 on a user's machine."""
    problems: List[dict] = []
    declared: Dict[str, str] = {}
    if URL_PROVENANCE.exists():
        try:
            reg = json.loads(URL_PROVENANCE.read_text(encoding="utf-8"))
            declared = {u["url"].rstrip("/"): u.get("status", "unverified") for u in reg.get("urls", [])}
        except Exception as exc:
            return [{"severity": "blocking", "mechanical": False, "file": "tools/url-provenance.json",
                     "issue": f"url-provenance.json unreadable: {exc}", "action": "fix the JSON"}]
    else:
        return [{"severity": "blocking", "mechanical": False, "file": "tools/url-provenance.json",
                 "issue": "url-provenance.json missing", "action": "create the URL provenance registry"}]

    scan_dirs = [ROOT / "tools", ROOT / "shared"]
    for base in scan_dirs:
        for pyf in base.rglob("*.py"):
            if ".harvest-venv" in str(pyf):
                continue
            try:
                text = pyf.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            rel = pyf.relative_to(ROOT).as_posix()
            for m in _URL_RE.findall(text):
                url = m.rstrip("/.,)\"'")
                if any(s in url for s in _URL_SKIP):
                    continue
                if url.rstrip("/") not in declared:
                    problems.append({
                        "severity": "warning", "mechanical": False, "file": rel, "url": url,
                        "issue": f"undeclared external URL '{url}' — not in url-provenance.json "
                                 f"(could be fabricated/unverified)",
                        "action": f"add '{url}' to tools/url-provenance.json with an honest status, "
                                  f"or remove it"})
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
    dependency_problems = scan_dependencies()
    url_problems = scan_url_provenance()
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
    for p in dependency_problems:
        score -= 4
        required.append({"severity": p["severity"], "area": f"dependency:{p['file']}",
                         "issue": p["issue"], "action": p["action"], "mechanical": p["mechanical"]})
    for p in url_problems:
        score -= (10 if p["severity"] == "blocking" else 4)
        if p["severity"] == "blocking":
            blocking.append(p["issue"])
        required.append({"severity": p["severity"], "area": f"url:{p['file']}",
                         "issue": p["issue"], "action": p["action"], "mechanical": p["mechanical"]})
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
        "dependency_problems": dependency_problems,
        "url_provenance_problems": url_problems,
        "diagnostics": diagnose(traces_dir),
        "repair_plan": required,
        "must_review_docs": ["changes/CHANGE_MANAGEMENT.md", "tools/skill-maintenance.md", "protocol-layer/quality-gates.md"] if required else [],
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
    ap.add_argument("--capabilities", action="store_true", help="optional-dependency + font + cloud preflight")
    ap.add_argument("--traces", metavar="DIR", help="dir of saved decision records / observability traces")
    ap.add_argument("--out", metavar="PATH", help="write the full JSON report (incl. repair_plan) to a file")
    a = ap.parse_args(argv)
    if a.capabilities:
        from capabilities import report as cap_report, to_summary as cap_summary  # type: ignore
        print(cap_summary(cap_report()), end="")
    elif a.impact:
        print(json.dumps(impact_analysis(a.impact), indent=2))
    elif a.diagnose:
        print(json.dumps(diagnose(a.traces), indent=2))
    elif a.summary:
        print(to_summary_md(build_report(a.traces)), end="")
    else:
        rep = build_report(a.traces)
        if a.out:
            __import__("pathlib").Path(a.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"wrote health report (readiness {rep['readiness_score']}/100, "
                  f"{len(rep['repair_plan'])} repair step(s)) -> {a.out}")
        else:
            print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
