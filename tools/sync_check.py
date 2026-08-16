#!/usr/bin/env python3
"""Drift guard for the TOS SKILL.md ecosystem.

Asserts INVARIANTS (not textual diffs) so that:
  - the governed core (shared/, protocol-layer/) and each skill's synced copies can
    never silently diverge, and
  - every skill honors the Quality Gates repository invariants and governance wiring.

Uses an invariants-based approach (assert invariants, not textual diffs; exit codes).

Run:   python3 tools/sync_check.py
Exit:  0 if every invariant holds, 1 (with a report) otherwise.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "tools" / "sync_manifest.json"

# Quality Gates §96 repository invariants (canonical phrases) must appear in the
# authoritative quality files.
REPO_INVARIANTS = [
    "Integrity precedes approval",
    "Evidence precedes certification",
    "Validation precedes release",
    "Audits remain independent",
    "Critical failures block approval",
    "Repository history remains traceable",
    "Quality decisions remain auditable",
    "Certification requires evidence",
]
INVARIANT_FILES = [ROOT / "protocol-layer" / "quality-gates.md", ROOT / "docs" / "QUALITY_MODEL.md"]

# Markers every SKILL.md must contain: the pipeline pointer, the metadata schema,
# and the always-on human-review flag.
REQUIRED_IN_SKILL = ["method.md", "metadata-schema.md", "human_review_required"]

# Every skill ships update instructions (MAINTAINER.md) with these sections (lowercased match),
# so skills stay consistent and route conflicts through the canonical resolver (tools/skill-maintenance.md).
REQUIRED_IN_MAINTAINER = [
    "non-negotiable invariants", "known failure modes", "regression cases",
    "approval-gated", "minority-report", "update checklist",
]

# Tokens that must never ship inside a skill's markdown.
FORBIDDEN = ["TODO", "FIXME", "PLACEHOLDER", "<<<<<<<", ">>>>>>>"]

# SKILL.md frontmatter rules (Claude Skill spec): only these top-level keys are allowed,
# name is hyphen-case <=64, description is <=1024 chars with no angle brackets.
ALLOWED_FRONTMATTER = {"name", "description", "license", "allowed-tools", "metadata"}
MAX_NAME, MAX_DESC = 64, 1024

# Resource-integrity: backticked repo paths in a SKILL.md must exist. A reference is valid if it
# resolves under the skill dir OR the repo root (so skill-local `examples/...` and repo-root
# `shared/...` both work). Conservative anchors/extensions on purpose; assets/ is intentionally
# excluded (output templates may be absent by design).
_REF_ANCHORS = ("references/", "scripts/", "evals/", "examples/",
                "protocol-layer/", "protocols/", "shared/", "tools/", "ledger/")
_REF_EXTS = (".md", ".py", ".json", ".yaml", ".yml", ".txt", ".csv")

# --- Doc-drift guards (checks 15-24) ---------------------------------------------------------------
# New in the maintainer/README audit. They land in REPORT-ONLY first (so the backfill PR stays green
# while docs are filled in), then flip to CI-blocking. Set True to enforce.
DOC_GUARDS_ENFORCE = True

# Check 15 (doc-path drift): backticked repo-relative paths in prose must resolve. Anchors mirror the
# repo layout; runtime stores (*.local.json) and historical records are excluded so the guard only
# fires on real drift.
_DOC_ANCHORS = ("skills/", "shared/", "protocol-layer/", "canonical-sources/", "tools/", "docs/",
                "implementation/", "examples/", "ledger/", "security/", "changes/")
DOC_PATH_ALLOW_FILES = {          # historical records — the paths in them are frozen at write time
    "ledger/quality-ledger.md", "changes/CHANGELOG.md",
}
DOC_RUNTIME_ARTIFACTS = {         # produced at runtime, legitimately absent from a clean checkout
    "ledger/rollback-log.json",
}

# Check 17 (component-doc coverage): every engine/bucket under these roots must carry >=1 .md doc.
COVERAGE_ROOTS = ("shared", "canonical-sources")
COVERAGE_SKIP = {"index"}         # index/ ships data + its own README; add non-component dirs here

# Check 18 (doc freshness): a missing stamp or a stamp older than this hard-fails (on enforce); a
# sibling changed after the stamp is an advisory reminder only.
DOC_FRESHNESS_MAX_AGE_DAYS = 365

# WHAT COUNTS AS A MAINTAINER-CLASS DOC — one definition, because there were two. Check 18 used
# ("*README.md", "*MAINTAINER.md") while check 20 used {CLAUDE.md, docs/MACOS.md,
# docs/DEPLOYMENT*.md, *MAINTAINER.md}. Neither was wrong; having both meant a doc could be held to
# the source-provenance rule while being exempt from the freshness rule, and vice versa.
#
# Adding a path here REQUIRES adding its `last_reviewed` stamp in the same commit — a missing stamp
# is a hard failure by design. Deliberately NOT widened into shared/** or protocol-layer/**: those
# are the canonical halves of the two-copy sync rule, so a stamp there propagates into the per-skill
# copies and turns a review date into a sync artifact. Their freshness is governed by the sync rule.
# docs/audits/* are also excluded: a dated audit is an immutable record, not a living document, and
# forcing it to be "re-reviewed" every 365 days would make its stamp mean the opposite of what it says.
MAINTAINER_CLASS_GLOBS = ("*README.md", "*MAINTAINER.md")
MAINTAINER_CLASS_FILES = (
    "CLAUDE.md", "STATE.md",
    "docs/ARCHITECTURE.md", "docs/DEPLOYMENT.md", "docs/DEPLOYMENT_SURFACES.md",
    "docs/MACOS.md", "docs/QUALITY_MODEL.md", "docs/RUNBOOK-cpalms.md",
    "security/SECURITY_REVIEW.md", "security/SECURITY_AND_SAFETY.md",
    "shared/health/dependency-policy.md", "changes/CHANGE_MANAGEMENT.md",
)


def maintainer_class_docs(tracked) -> list:
    """Every doc held to the stamp. `tracked` is the _tracked_files helper (git-backed)."""
    docs = set(tracked(*MAINTAINER_CLASS_GLOBS))
    docs |= {ROOT / rel for rel in MAINTAINER_CLASS_FILES if (ROOT / rel).exists()}
    return sorted(docs)


# Check 24: JSONs carrying a human-typed `updated` that NOTHING read. dependencies.json declared
# 2026-06-23 while the mcp_server capability and its isolation flag landed 2026-08-16 — an
# eight-week-old date that survived a full audit. A date a human types and no machine checks is
# decoration; the repo already learned this for versions (version.py gates versions.json.updated)
# and for generated artifacts (checks 16/21/22). These seven were never brought into that discipline.
DATED_MANIFESTS = (
    "tools/dependencies.json", "tools/registry-sources.json", "tools/url-provenance.json",
    "shared/atoms/atoms.json", "shared/connectors/connectors.json",
    "shared/routing/routing.json", "shared/standards/states.json",
)


def git_commit_date(path: Path, exclude_names=()):
    """The date of the last commit touching `path` — or None when git cannot answer.

    None is returned for a `git archive` export or a missing git binary, and callers must treat it
    as "no comparison available", never as "up to date". `exclude_names` drops matching basenames
    anywhere beneath a directory argument via git pathspec magic."""
    try:
        rel = path.relative_to(ROOT).as_posix() if path != ROOT else "."
        spec = [rel] + [f":(exclude){rel}/**/{n}" for n in exclude_names]
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", *spec],
                             cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        return date.fromisoformat(out) if out else None
    except Exception:
        return None


def synced_basenames() -> set:
    """The file names that exist in every skill as byte-identical copies of a canonical source.

    Read from tools/sync_manifest.json rather than hardcoded, so adding a synced reference updates
    every consumer automatically. Check 18 uses this to stop treating a re-sync as a review signal:
    a copy that check 2 already holds byte-identical to canon cannot drift, so its commit date says
    nothing about whether the MAINTAINER doc beside it still describes its skill. That single
    exclusion is worth 43 of the 83 advisories the check used to print — every atom MAINTAINER was
    flagged by references/quality-gates.md being re-synced, and nothing else."""
    try:
        man = json.loads((ROOT / "tools" / "sync_manifest.json").read_text(encoding="utf-8"))
        return set(man.get("synced_references", {}))
    except Exception:
        return set()


def _guard_crashed(guard: str, exc: Exception):
    """The message for a drift check that raised — or None when a developer explicitly allowed it.

    AUDIT G-1: nine of these handlers used to print a lowercase `[note] … skipped` and let CI pass
    green, so a guard that crashed was indistinguishable from a guard that found nothing. Every
    guard here is stdlib, offline and in-repo (verified: health.health, metrics, offline_index and
    mac_audit all import on a bare interpreter; the two that shell out to git already fall back
    internally), so an unexpected exception means the repo or the guard is broken — which is
    exactly what the gate exists to say.

    TOS_SYNC_SKIP is the single escape hatch: a comma-separated list of guard names a developer
    has to type on purpose. It is refused whenever CI is set, so it can never soften the build.
    The only OTHER skip in this file is check 23's ImportError path, where the `mcp` SDK is a
    genuinely optional, off-by-default capability."""
    allowed = {g.strip() for g in os.environ.get("TOS_SYNC_SKIP", "").split(",") if g.strip()}
    if guard in allowed and not os.environ.get("CI"):
        print(f"SKIPPED {guard} — named in TOS_SYNC_SKIP ({exc.__class__.__name__}: {exc}); "
              f"this escape hatch is refused when CI is set")
        return None
    return (f"  x {guard} CRASHED and did not run ({exc.__class__.__name__}: {exc}) — a guard that "
            f"cannot run is a failure, not a pass; fix the guard or what it imports")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def parse_frontmatter(body: str):
    """Return (frontmatter_text|None, keys, name, description) for a SKILL.md body."""
    m = re.match(r"^---\n(.*?)\n---", body, re.DOTALL)
    if not m:
        return None, [], None, None
    fm = m.group(1)
    keys = re.findall(r"^([A-Za-z0-9_-]+):", fm, re.MULTILINE)
    nm = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    dm = re.search(r"^description:\s*(.+)$", fm, re.DOTALL | re.MULTILINE)
    name = nm.group(1).strip().strip('"').strip("'") if nm else None
    desc = dm.group(1).strip().strip('"').strip("'") if dm else None
    return fm, keys, name, desc


def validate_frontmatter(name, desc, keys, folder: str) -> list[str]:
    out: list[str] = []
    if name is None:
        out.append("frontmatter missing 'name'")
    else:
        if name != folder:
            out.append(f"frontmatter name '{name}' != folder '{folder}'")
        if not re.match(r"^[a-z0-9-]+$", name) or "--" in name or name[0] == "-" or name[-1] == "-":
            out.append(f"name '{name}' is not clean hyphen-case")
        if len(name) > MAX_NAME:
            out.append(f"name >{MAX_NAME} chars ({len(name)})")
    if desc is None:
        out.append("frontmatter missing 'description'")
    else:
        if len(desc) > MAX_DESC:
            out.append(f"description >{MAX_DESC} chars ({len(desc)})")
        if "<" in desc or ">" in desc:
            out.append("description contains angle brackets (< or >)")
    bad = sorted(set(keys) - ALLOWED_FRONTMATTER)
    if bad:
        out.append("unexpected frontmatter key(s): " + ", ".join(bad))
    return out


def check_references(sd: Path, text: str) -> list[str]:
    """Every backticked repo path with a known extension must resolve to a real file
    (under the skill dir or the repo root)."""
    out: list[str] = []
    for tok in re.findall(r"`([^`]+)`", text):
        tok = tok.strip()
        if "/" not in tok or not tok.endswith(_REF_EXTS):
            continue
        if any(c in tok for c in "<>*| "):
            continue
        if not tok.startswith(_REF_ANCHORS):
            continue
        if (sd / tok).exists() or (ROOT / tok).exists():
            continue
        out.append(f"broken reference: `{tok}`")
    return out


def main() -> int:
    failures: list[str] = []

    # 0. Manifest + canonical sources exist.
    if not MANIFEST.exists():
        print(f"[!] Missing manifest: {MANIFEST}")
        return 1
    synced = json.loads(read(MANIFEST)).get("synced_references", {})
    canonical: dict[str, str] = {}
    for refname, relpath in synced.items():
        cpath = ROOT / relpath
        if not cpath.exists():
            failures.append(f"  x canonical source missing: {relpath} (for {refname})")
        else:
            canonical[refname] = read(cpath)

    # 1. Repository invariants present in the authoritative quality files.
    for f in INVARIANT_FILES:
        if not f.exists():
            failures.append(f"  x invariant file missing: {f.relative_to(ROOT)}")
            continue
        text = read(f)
        for inv in REPO_INVARIANTS:
            if inv not in text:
                failures.append(f'  x invariant absent: "{inv}" not in {f.relative_to(ROOT)}')

    # Per-skill checks. Skills are now sub-grouped (core/, educator/, operations/, atoms/);
    # find every directory that contains a SKILL.md, recursively.
    skill_dirs = sorted(p.parent for p in SKILLS.rglob("SKILL.md")) if SKILLS.exists() else []
    for sd in skill_dirs:
        rel = sd.relative_to(ROOT)
        skillmd = sd / "SKILL.md"
        if not skillmd.exists():
            failures.append(f"  x {rel}: missing SKILL.md")
            continue
        body = read(skillmd)

        # 2. Synced references present and byte-identical to canon.
        for refname, content in canonical.items():
            rpath = sd / "references" / refname
            if not rpath.exists():
                failures.append(f"  x {rel}: missing synced reference references/{refname}")
            elif read(rpath) != content:
                failures.append(f"  x {rel}: references/{refname} drifted from {synced[refname]}")

        # 3-5. Required governance/pipeline wiring in SKILL.md.
        for marker in REQUIRED_IN_SKILL:
            if marker not in body:
                failures.append(f"  x {rel}: SKILL.md does not reference '{marker}'")

        # 6. No forbidden tokens anywhere in the skill's markdown.
        for md in sorted(sd.rglob("*.md")):
            mtext = read(md)
            for tok in FORBIDDEN:
                if tok in mtext:
                    failures.append(f"  x {md.relative_to(ROOT)}: forbidden token '{tok}'")

        # 7. SKILL.md frontmatter is a valid Claude Skill header.
        fm, keys, name, desc = parse_frontmatter(body)
        if fm is None:
            failures.append(f"  x {rel}: SKILL.md has no YAML frontmatter")
        else:
            for w in validate_frontmatter(name, desc, keys, sd.name):
                failures.append(f"  x {rel}: {w}")

        # 8. Resource integrity: referenced repo files must exist.
        for w in check_references(sd, body):
            failures.append(f"  x {rel}: {w}")

        # 9. Update instructions: a MAINTAINER.md with the required sections must exist.
        maint = sd / "MAINTAINER.md"
        if not maint.exists():
            failures.append(f"  x {rel}: missing MAINTAINER.md (update instructions; see tools/skill-maintenance.md)")
        else:
            low = read(maint).lower()
            for marker in REQUIRED_IN_MAINTAINER:
                if marker not in low:
                    failures.append(f"  x {rel}: MAINTAINER.md missing section '{marker}'")

    # 10. Routing integrity: every shared/routing/routing.json target is a real skill (or the fallback).
    routing_path = ROOT / "shared" / "routing" / "routing.json"
    # skill_names is bound OUTSIDE the exists() branch on purpose (audit G-7): check 11 below uses
    # it too, so a missing routing.json used to raise NameError mid-run — a traceback instead of a
    # finding. routing.json is a TRACKED file, so its absence is itself a failure, not a skip.
    skill_names = {d.name for d in skill_dirs}  # leaf names are stable after sub-grouping
    if not routing_path.exists():
        failures.append("  x shared/routing/routing.json is missing — it is a tracked file, and "
                        "without it neither route targets nor workflow atoms can be resolved; "
                        "restore it from git")
    else:
        rj = json.loads(read(routing_path))
        fallback = rj.get("fallback", "manual_review")
        targets = set(rj.get("skills", {})) | set(rj.get("meeting_routes", {}).values())
        for t in sorted(targets):
            if t != fallback and t not in skill_names:
                failures.append(f"  x routing.json: route target '{t}' is not an installed skill")
        for t in sorted(rj.get("atom_routes", {})):
            if t.startswith("_"):
                continue
            if t not in skill_names:
                failures.append(f"  x routing.json: atom_route '{t}' is not an installed skill")

    # 11. Workflow atom resolution: every atom named in a workflow.json must be an installed skill.
    for wf_path in sorted(SKILLS.rglob("workflow.json")):
        try:
            wf = json.loads(read(wf_path))
        except Exception:
            failures.append(f"  x {wf_path.relative_to(ROOT)}: invalid JSON")
            continue
        wf_atoms = set()
        for step in wf.get("steps", []):
            if "atom" in step:
                wf_atoms.add(step["atom"])
        for a in wf.get("shortcut_atoms", []):
            wf_atoms.add(a)
        for a in sorted(wf_atoms):
            if a not in skill_names:
                failures.append(f"  x {wf_path.relative_to(ROOT)}: atom '{a}' not an installed skill")

    # 12. Dependency-safety guard (anti "dependency hell"): no compile-from-source package may be
    # listed in a requirements file without an --only-binary guard. Reuses the health engine so
    # there is one source of truth. Catches the lxml-class build failures before they reach a teacher.
    sys.path.insert(0, str(ROOT / "shared"))
    try:
        from health.health import scan_dependencies
        for p in scan_dependencies():
            if "without --only-binary guard" in p["issue"]:
                failures.append(f"  x {p['file']}: {p['issue']}")
    except Exception as e:  # health engine optional — never let it crash the guard
        _crash = _guard_crashed("dependency guard", e)
        if _crash:
            failures.append(_crash)

    # 13. URL-provenance guard (anti-fabrication): every external URL hardcoded in tools/*.py and
    # shared/**/*.py must be DECLARED in tools/url-provenance.json. An undeclared URL is the
    # confabulation risk — a plausible-looking address that was never verified. Catch it here, not
    # as a 403 on a teacher's machine.
    try:
        from health.health import scan_url_provenance
        for p in scan_url_provenance():
            failures.append(f"  x {p['file']}: {p['issue']}")
    except Exception as e:
        _crash = _guard_crashed("url-provenance guard", e)
        if _crash:
            failures.append(_crash)

    # 14. Offline-index freshness guard: the gitignored canonical-sources/index/offline.db is built
    # from committed JSON. If a source changed since the last build, the committed
    # index-manifest.json no longer matches — the index is STALE and would serve out-of-date text.
    # Compares committed sources to the committed manifest (needs neither the db nor a prior build),
    # so it fires in CI and on a fresh clone. A missing manifest degrades to a note, not a failure.
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        from offline_index import drift_report
        rep = drift_report()
        if rep.get("stale"):
            # a missing/unreadable manifest reports stale with a `reason` (no changed/added/removed);
            # a genuine source change reports the file lists. Surface whichever applies.
            detail = rep.get("reason") or (f"changed={rep['changed']} added={rep['added']} "
                                           f"removed={rep['removed']}")
            failures.append(
                "  x offline index stale vs canonical-sources/index/index-manifest.json "
                f"({detail}) — run: python3 tools/offline_index.py --build && commit the manifest")
    except Exception as e:  # index tool import optional — never let it crash the guard
        _crash = _guard_crashed("index-freshness guard", e)
        if _crash:
            failures.append(_crash)

    # --- Doc-drift guards (checks 15-24) -----------------------------------------------------------
    # Each emits into `failures` when DOC_GUARDS_ENFORCE, else prints a [note] (report-only). All are
    # wrapped so an unexpected error degrades to a note and never crashes the gate (as with 12-14).
    def _emit(msg: str) -> None:
        failures.append(msg) if DOC_GUARDS_ENFORCE else print(f"[note]{msg[3:]}")

    def _skill_dir_of(md: Path):
        for anc in md.parents:
            if (anc / "SKILL.md").exists():
                return anc
            if anc == ROOT:
                break
        return None

    def _tracked_files(*globs: str) -> list[Path]:
        """The docs that actually ship: git-tracked paths only. Excludes gitignored dirs — a local
        virtualenv (`.harvest-venv/`), build artifacts, `node_modules/` — so the guards can't
        false-fail on vendored files that exist only in one checkout (rglob descends into hidden dirs;
        git-tracked doesn't). Falls back to rglob minus dot-dirs / node_modules if git is unavailable."""
        try:
            out = subprocess.run(["git", "ls-files", "-z", *globs], cwd=ROOT,
                                 capture_output=True, timeout=15)
            if out.returncode == 0:
                return [ROOT / p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]
        except Exception:
            pass
        res: list[Path] = []
        for g in globs:
            for p in ROOT.rglob(g.split("/")[-1]):
                parts = p.relative_to(ROOT).parts
                if any(part.startswith(".") for part in parts) or "node_modules" in parts:
                    continue
                res.append(p)
        return res

    # 15. Doc-path drift: a repo-relative path referenced in a tracked .md — in `backticks` OR a
    # [markdown](link) — must resolve on disk. Generalizes check_references() (skill-local) to the
    # whole tree (the class that left dead un-grouped skills/<name>/ paths after the grouping refactor).
    # Only git-tracked files are scanned, so vendored .md in a local venv can't false-trip it. Resolves
    # relative to repo root, the file's own dir, and its owning skill dir (so skill-local examples/…
    # and relative links both pass); skips runtime stores (*.local.json), known runtime artifacts,
    # glob/placeholder tokens, external URLs, and historical records whose paths are frozen. One
    # unreadable file skips only itself (never disables the whole check).
    try:
        for md in sorted(_tracked_files("*.md")):
            rel = md.relative_to(ROOT).as_posix()
            if "/skill-template/" in rel or "/node_modules/" in rel or rel in DOC_PATH_ALLOW_FILES:
                continue
            try:
                body = md.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"[note] doc-path guard: skipped unreadable {rel} ({e.__class__.__name__})")
                continue
            sd = _skill_dir_of(md)
            bases = [ROOT, md.parent] + ([sd] if sd else [])
            # Strip fenced code blocks before scanning. Triple-backtick fences otherwise (a) desync the
            # inline-`backtick` regex pairing — missing a real dead path inside a fence — and (b) turn
            # illustrative example paths in fenced tutorials into false positives. Path references worth
            # guarding live in prose / inline code; check those, not fenced example bodies.
            scan_body = re.sub(r"(```|~~~).*?\1", "", body, flags=re.DOTALL)
            # backticked paths are repo-relative by convention (require a repo anchor); [markdown](links)
            # are commonly relative and resolve against the file dir (no anchor requirement).
            cands = [(t, True) for t in re.findall(r"`([^`]+)`", scan_body)]
            cands += [(t, False) for t in re.findall(r"\]\(([^)]+)\)", scan_body)]
            for raw, require_anchor in cands:
                raw = raw.strip()
                tok = raw.split()[0] if raw else ""            # drop a `](path "title")` suffix
                if not tok or tok.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if any(c in tok for c in "<>*| {}"):            # globs / brace-expansions / placeholders
                    continue
                target = tok.split("#", 1)[0]                   # drop a trailing #anchor
                if not target.endswith(_REF_EXTS):
                    continue
                if require_anchor and not target.startswith(_DOC_ANCHORS):
                    continue
                if target.endswith(".local.json") or target in DOC_RUNTIME_ARTIFACTS:
                    continue
                if any((b / target).exists() for b in bases):
                    continue
                _emit(f"  x doc-path drift — {rel}: dead {'link' if not require_anchor else 'path'} `{tok}`")
    except Exception as e:
        _crash = _guard_crashed("doc-path guard", e)
        if _crash:
            _emit(_crash)

    # 16. METRICS.md freshness: the committed dashboard must equal a fresh render (minus the generated
    # date line). metrics.py is marked "Do not hand-edit"; this catches "edited skills, forgot to
    # regenerate" (how it sat at 29 skills). Compares content only — the date line is normalized out
    # so a same-day re-render never false-fails.
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        import metrics as _metrics

        def _norm_metrics(s: str) -> str:
            return "\n".join(l for l in s.splitlines() if not l.startswith("_Generated by"))

        live = _norm_metrics(_metrics.render())
        disk = _norm_metrics((ROOT / "docs" / "METRICS.md").read_text(encoding="utf-8"))
        if live != disk:
            _emit("  x docs/METRICS.md is stale vs live evidence — "
                  "run: python3 tools/metrics.py && commit docs/METRICS.md")
    except Exception as e:
        _crash = _guard_crashed("metrics-freshness guard", e)
        if _crash:
            _emit(_crash)

    # 17. Component-doc coverage: every engine under shared/ and every bucket under canonical-sources/
    # carries >=1 top-level .md doc (README, MAINTAINER, or a *-model.md / *-policy.md). Extends the
    # skills-only MAINTAINER-presence check to non-skill components (Diataxis: every component documented).
    try:
        for base_name in COVERAGE_ROOTS:
            base = ROOT / base_name
            if not base.exists():
                continue
            for d in sorted(p for p in base.iterdir() if p.is_dir()):
                if d.name in COVERAGE_SKIP or d.name.startswith((".", "__")):
                    continue
                if not any(d.glob("*.md")):
                    _emit(f"  x component has no doc (add a README/MAINTAINER or *-model.md): "
                          f"{d.relative_to(ROOT).as_posix()}/")
    except Exception as e:
        _crash = _guard_crashed("component-doc-coverage guard", e)
        if _crash:
            _emit(_crash)

    # 18. Doc freshness (SWE-at-Google Ch.10): every README/MAINTAINER carries a `last_reviewed` stamp.
    # A missing stamp, or a stamp older than DOC_FRESHNESS_MAX_AGE_DAYS, hard-fails (on enforce). A
    # sibling source changed *after* the stamp is an advisory reminder only (always a [note]) — a
    # re-review nudge, not a correctness failure.
    try:
        today = date.today()
        # AUDIT G-2: this advisory fired on 84 of 95 maintainer-class docs on EVERY run — 85 notes
        # per CI log, 84 of them this one. A signal that never stops is not a signal, and it buried
        # the SKIPPED/CRASHED lines the fail-closed conversion now prints. Collect and summarise;
        # TOS_SYNC_VERBOSE=1 restores the per-file list for whoever is actually doing a doc pass.
        _sibling_stale: list[tuple] = []
        # ...and two signals were conflated into one. "Someone edited a file NEXT to this doc" and
        # "someone edited THIS DOC after the date it claims to have been reviewed" are different
        # findings, and only the first is a nudge. The second is the stamp contradicting its own
        # file. Reported separately so the loud one is legible: all 43 atom MAINTAINERs are in the
        # second class (edited 2026-07-15, stamped 2026-06-27), not the first.
        _self_stale: list[tuple] = []

        # Synced references are byte-identical to canon by construction and are guarded harder by
        # check 2 — a re-sync is not evidence that the doc beside them needs re-reading. Excluding
        # them is what turns this advisory back into a signal.
        _synced = sorted(synced_basenames())

        def _git_date(p: Path, exclude_synced: bool = False):
            return git_commit_date(p, _synced if exclude_synced else ())

        docs = maintainer_class_docs(_tracked_files)
        for doc in docs:
            drel = doc.relative_to(ROOT).as_posix()
            if "/skill-template/" in drel or "/node_modules/" in drel:
                continue
            try:
                dtext = doc.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"[note] doc-freshness guard: skipped unreadable {drel} ({e.__class__.__name__})")
                continue
            m = re.search(r"last_reviewed:\s*(\d{4}-\d{2}-\d{2})", dtext)
            if not m:
                _emit(f"  x doc missing `last_reviewed` stamp: {drel}")
                continue
            try:
                stamp = date.fromisoformat(m.group(1))
            except ValueError:
                # regex-matching but not a real calendar date (e.g. 2026-13-45) — flag this doc, don't
                # let one bad stamp raise and disable the freshness check for every other doc.
                _emit(f"  x doc has an invalid `last_reviewed` date: {drel} ({m.group(1)})")
                continue
            if (today - stamp).days > DOC_FRESHNESS_MAX_AGE_DAYS:
                _emit(f"  x doc stale: {drel} last_reviewed {stamp} (> {DOC_FRESHNESS_MAX_AGE_DAYS}d)")
                continue
            own = _git_date(doc)                               # advisory only — never a failure
            if own and own > stamp:
                # The doc's own content moved after the date it claims. The sibling nudge below
                # would be noise on top of this, so it is skipped: report the stronger finding once.
                _self_stale.append((stamp, drel, own))
                continue
            newest = _git_date(doc.parent, exclude_synced=True)  # advisory only — never a failure
            if newest and newest > stamp:
                _sibling_stale.append((stamp, drel, newest))
        if _self_stale:
            _self_stale.sort()
            oldest = "; ".join(f"{d} (stamped {s}, edited {n})" for s, d, n in _self_stale[:5])
            print(f"[note] doc-freshness: {len(_self_stale)} doc(s) were EDITED after the "
                  f"last_reviewed date they declare — the stamp contradicts its own file, not a "
                  f"sibling. Oldest 5: {oldest}"
                  + ("" if os.environ.get("TOS_SYNC_VERBOSE") else
                     " — set TOS_SYNC_VERBOSE=1 for the full list"))
            if os.environ.get("TOS_SYNC_VERBOSE"):
                for s, d, n in _self_stale:
                    print(f"[note]   SELF {d}: edited {n}, last_reviewed {s}")
        if _sibling_stale:
            _sibling_stale.sort()
            oldest = "; ".join(f"{d} (stamped {s})" for s, d, _ in _sibling_stale[:5])
            print(f"[note] doc-freshness: {len(_sibling_stale)} doc(s) have a sibling change newer "
                  f"than their last_reviewed stamp. Oldest 5: {oldest}"
                  + ("" if os.environ.get("TOS_SYNC_VERBOSE") else
                     " — set TOS_SYNC_VERBOSE=1 for the full list"))
            if os.environ.get("TOS_SYNC_VERBOSE"):
                for s, d, n in _sibling_stale:
                    print(f"[note]   {d}: sibling changed {n}, last_reviewed {s}")
    except Exception as e:
        _crash = _guard_crashed("doc-freshness guard", e)
        if _crash:
            _emit(_crash)

    # 19. mac-lint (cross-platform safety): no child process spawned by the bare name "python3"/"python"
    # (use sys.executable — a macOS venv can otherwise launch the wrong interpreter), and no text
    # open()/read_text()/write_text() without encoding= (locale-dependent decode). CI runs on Linux
    # where these pass, so without this guard a Mac-only regression ships unnoticed. Same degrade-to-note
    # idiom as 12-14 if the tool can't be imported.
    try:
        from mac_audit import scan as _mac_scan
        for f in _mac_scan():
            _emit(f"  x mac-lint {f['file']}:{f['line']} [{f['check']}] {f['issue']}")
    except Exception as e:
        _crash = _guard_crashed("mac-lint guard", e)
        if _crash:
            _emit(_crash)

    # 20. Doc-source provenance (declare-or-fail): an external URL cited in a maintainer-class doc must
    # be registered in a canonical-sources/registries/*.json source registry (freshness-tracked by
    # tools/source_currency.py) or tools/url-provenance.json. Doc-side analog of check 13: a maintainer
    # note that cites a source thereby *triggers* its registration, so no cited authority can rot
    # untracked. Prefix-match against the registered URL so #anchor/query variants of a declared page
    # pass. Fenced code blocks are stripped (like check 15); a tiny allowlist covers incidental
    # non-authority links.
    try:
        def _norm_url(u: str) -> str:
            # RFC 3986: the scheme and host are case-insensitive (lowercase them for comparison);
            # the path is case-sensitive and left untouched. Trailing slash is equivalence-stripped.
            m = re.match(r"(?i)^(https?)://([^/]*)(.*)$", u)
            if not m:
                return u.rstrip("/")
            return f"{m.group(1).lower()}://{m.group(2).lower()}{m.group(3)}".rstrip("/")

        registered: set[str] = set()
        for reg_p in sorted((ROOT / "canonical-sources" / "registries").glob("*.json")):
            try:
                rj = json.loads(read(reg_p))
            except Exception:
                # its sources silently dropping out would redden every doc that cites them with a
                # message that never names the broken file — say which registry failed to load.
                print(f"[note] doc-source guard: unreadable registry {reg_p.name} — its sources are "
                      f"not registered this run")
                continue
            for s in rj.get("sources", []) or []:
                if isinstance(s, dict) and s.get("url"):
                    registered.add(_norm_url(str(s["url"])))
        upp = ROOT / "tools" / "url-provenance.json"
        if upp.exists():
            for u in json.loads(read(upp)).get("urls", []):
                if isinstance(u, dict) and u.get("url"):
                    registered.add(_norm_url(str(u["url"])))

        def _declared(cited: str) -> bool:
            # EXACT-PAGE match: a citation is declared only if it IS a registered page (after
            # normalization) or adds only a #fragment/?query to one (same page per RFC 3986
            # §3.4/§3.5). A plain prefix test let three bypass shapes through (deep paths under a
            # registered root, sibling-shadowing like `…/developer-id-evil` passing off
            # `…/developer-id/`, numeric suffixes like 102527999 passing off 102527) — every
            # distinct cited page must be individually registered, which is the freshness goal.
            c = _norm_url(cited)
            if c in registered:
                return True
            return any(c.startswith(r + "#") or c.startswith(r + "?") for r in registered)

        DOC_SOURCE_ALLOW = ("https://github.com/",)   # incidental repo/issue links, not cited authorities
        doc_set = set(maintainer_class_docs(_tracked_files))   # same definition as check 18
        for md in sorted(p for p in doc_set if p.exists()):
            rel = md.relative_to(ROOT).as_posix()
            if "/skill-template/" in rel:
                continue
            try:
                body = md.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"[note] doc-source guard: skipped unreadable {rel} ({e.__class__.__name__})")
                continue
            body = re.sub(r"(```|~~~).*?\1", "", body, flags=re.DOTALL)
            for url in re.findall(r"https?://[^\s)>\]\"'`]+", body, flags=re.IGNORECASE):
                # A template placeholder is not a cited authority. `https://<your-host>/mcp` in a
                # deploy recipe names no source to register — the same reason check 8's reference
                # scan skips tokens containing "<>*| ". Surfaced when this check was widened to
                # READMEs: deploy/mcp/README.md tripped it five times on its own instructions.
                if "<" in url or ">" in url:
                    continue
                url = url.rstrip(".,;:!?")
                if any(url.lower().startswith(a) for a in DOC_SOURCE_ALLOW):
                    continue
                if _declared(url):
                    continue
                _emit(f"  x doc-source undeclared — {rel}: {url} — register it in a "
                      f"canonical-sources/registries/*.json source registry (with state.last_checked) "
                      f"or tools/url-provenance.json")
    except Exception as e:
        _crash = _guard_crashed("doc-source guard", e)
        if _crash:
            _emit(_crash)

    # 21. Plugin-metadata freshness: the committed .claude-plugin/ manifests + the skills/README
    # generated catalog must equal a fresh render from live facts (export_plugin_manifest.py —
    # counts computed, never typed; the marketplace listing said "15 skills" for seven weeks while
    # 62 existed because nothing generated or compared it). UNLIKE check 16 this is FAIL-CLOSED:
    # the generator is stdlib/offline/in-repo, so an ImportError here means the repo is broken,
    # which is exactly what this gate exists to say — a degrade-to-note would silently disarm it.
    try:
        import export_plugin_manifest as _epm
        for _issue in _epm.check():
            _emit(_issue)
    except Exception as e:
        _emit(f"  x plugin-metadata freshness gate could not run "
              f"({e.__class__.__name__}: {e}) — the generator itself is broken; fix "
              f"tools/export_plugin_manifest.py (its --self-test should reproduce this)")

    # 22. MCP tool-surface freshness: the committed Actions OpenAPI schema + tool-surface
    # snapshot must equal a fresh render from tools/mcp_tooldefs.py — any tool-surface change is
    # a conscious, reviewed diff on both platforms (Claude MCP + ChatGPT Actions) at once.
    # FAIL-CLOSED like check 21: a broken generator is a failure, not a skipped note.
    try:
        import export_actions_schema as _eas
        for _issue in _eas.check():
            _emit(_issue)
    except Exception as e:
        _emit(f"  x MCP tool-surface freshness gate could not run "
              f"({e.__class__.__name__}: {e}) — fix tools/export_actions_schema.py "
              f"(its --self-test should reproduce this)")

    # 23. Cross-domain schema parity: the schema the `mcp` SDK derives for Claude must match the
    # registry schema ChatGPT gets. Check 22 above cannot see this — it compares a registry render
    # to committed registry artifacts, so registry-vs-SDK divergence is structurally invisible to
    # it, which is how all 8 tools shipped a free-text `subject` on claude.ai and a constrained one
    # on ChatGPT. Comparison is SEMANTIC (the SDK spells optionals `anyOf:[X,null]`); see
    # mcp_http_server.schema_parity().
    # DEGRADATION IS DELIBERATELY UNLIKE 21/22: ImportError -> SKIP, anything else -> FAIL. Those
    # gates are fail-closed because their generators are stdlib/offline/in-repo, so an ImportError
    # means the repo is broken; here it means the OPTIONAL `mcp_server` capability (off by default)
    # simply is not installed — a documented, expected state on a plain clone. The skip cannot
    # become permanent: parity is also asserted inside `mcp_http_server.py --self-test`, which CI
    # runs after installing tools/requirements-mcp.txt.
    try:
        import mcp_http_server as _mhs
        for _issue in _mhs.schema_parity():
            _emit(_issue)
    except ImportError as e:
        print(f"[note] MCP schema-parity gate skipped — the `mcp` SDK is not installed here "
              f"({e.__class__.__name__}: {e}). CI asserts it in mcp_http_server --self-test; to "
              f"run it locally: python3 tools/deps_preflight.py --install mcp_server")
    except Exception as e:
        _emit(f"  x MCP schema-parity gate could not run ({e.__class__.__name__}: {e}) — this is "
              f"NOT the missing-SDK case; fix tools/mcp_http_server.py "
              f"(its --self-test should reproduce this)")

    # 24. A hand-curated `updated` field must not contradict its own file. Same shape as check 18's
    # stamp comparison, and tolerant in exactly one direction: a date NEWER than the last commit is
    # fine (you stamp today and commit today), a date OLDER means the content moved and the date did
    # not. This catches the real failure mode — someone edits the file and forgets — and needs no new
    # state. It does NOT prove anyone re-thought the content; that is the limit every freshness stamp
    # has. git unavailable (a `git archive` export) yields no comparison and says so rather than
    # inventing one, exactly as check 18 already degrades.
    try:
        for _rel in DATED_MANIFESTS:
            _p = ROOT / _rel
            if not _p.exists():
                _emit(f"  x dated manifest missing: {_rel} — it is a tracked file; restore it from git")
                continue
            try:
                _declared = json.loads(_p.read_text(encoding="utf-8")).get("updated")
            except Exception as e:
                _emit(f"  x dated manifest unreadable: {_rel} ({e.__class__.__name__}: {e})")
                continue
            if not _declared:
                _emit(f"  x {_rel} has no `updated` field — it is in DATED_MANIFESTS because that "
                      f"date is load-bearing; add it, or remove the file from the tuple")
                continue
            try:
                _d = date.fromisoformat(str(_declared))
            except ValueError:
                _emit(f"  x {_rel} `updated` is not an ISO date: {_declared!r}")
                continue
            _g = git_commit_date(_p)
            if _g is None:
                print(f"[note] dated-manifest guard: git cannot date {_rel} (export or no git) — "
                      f"declared {_d} not compared")
            elif _g > _d:
                _emit(f"  x {_rel} declares `updated: {_d}` but its last commit is {_g} — the "
                      f"content moved and the date did not. Set it to the date of the change.")
    except Exception as e:
        _crash = _guard_crashed("dated-manifest guard", e)
        if _crash:
            _emit(_crash)

    print("TOS ecosystem - drift guard\n")
    if failures:
        print("DRIFT / INVARIANT FAILURES:\n")
        print("\n".join(failures))
        print(
            f"\n{len(failures)} check(s) failed. Edit the canonical file in shared/ or protocol-layer/ "
            "and re-sync; do not hand-edit synced copies."
        )
        return 1

    print(
        f"OK - {len(skill_dirs)} skill(s) checked; {len(REPO_INVARIANTS)} repository invariants "
        f"present; {len(canonical)} synced reference(s) in sync; frontmatter + resource integrity OK; "
        f"MAINTAINER.md present in all skills."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
