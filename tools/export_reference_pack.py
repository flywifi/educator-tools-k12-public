#!/usr/bin/env python3
"""export_reference_pack.py — build the ChatGPT/claude.ai Reference Pack.

Assembles a CURATED set of canonical reference files into
implementation/gpt/web/reference-pack/ so a chat-platform Project can answer
standards/course/district/school-type questions from the verified Florida
snapshot instead of model memory. Platform-neutral plain JSON + one MANIFEST.md
of receipts (where every file came from and how to double-check it).

Curation rules (the pack is deliberately small):
  * teacher-relevant reference data only — no maintainer registries, no crawl
    caches, no regenerable build artifacts (offline.db);
  * every file MUST carry provenance resolvable from repo data at build time —
    the build FAILS on any uncited file (no fabricated citations);
  * file count stays <= 15 so the pack + TOS-skills.md + a teacher profile fit
    comfortably inside a ~20-file ChatGPT Project.

Usage:
  python3 tools/export_reference_pack.py            # build the pack + MANIFEST.md
  python3 tools/export_reference_pack.py --check    # drift guard: sha256 vs sources,
                                                    # provenance present, <= 15 files

Stdlib only. Generated output — never edit reference-pack/ by hand.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_DIR = ROOT / "implementation" / "gpt" / "web" / "reference-pack"
STANDARDS_DATA = ROOT / "shared" / "standards" / "resources" / "florida" / "data"
STANDARDS_SOURCES = ROOT / "shared" / "standards" / "resources" / "florida" / "sources.json"
REFS = ROOT / "canonical-sources" / "references"
MAX_FILES = 15

# The six standards subjects shipped (index.json is superseded by MANIFEST.md).
STANDARDS_SUBJECTS = ["ela", "math", "science", "social_studies", "computer_science", "eld"]

# The six small pedagogy references consolidated into ONE pack file (saves Project slots).
FRAMEWORKS = {
    "blooms_taxonomy": REFS / "blooms-taxonomy.json",
    "webbs_dok": REFS / "webbs-dok.json",
    "cast_udl_3_0": REFS / "cast-udl-3.0.json",
    "fl_feaps": REFS / "fl-feaps.json",
    "coxhead_awl": REFS / "coxhead-awl.json",
    "fl_instructional_toolkits": REFS / "fl-instructional-toolkits.json",
}

EXCLUSIONS = [
    ("canonical-sources/references/toolkit-content/ (2.2M, 14 files)",
     "standard→CPALMS deep-link content — bulky; use the full-copy tier (clone the repo)"),
    ("canonical-sources/schools/ (664K, 12 files)",
     "school directory/lookup data — the profile interview captures YOUR school directly; full-copy tier"),
    ("canonical-sources/registries/",
     "maintainer ingestion/currency tracking, not teacher reference data"),
    ("canonical-sources/overlays/, canonical-sources/districts/ internals",
     "maintainer context stubs; the district directory teachers need is IN the pack (fl-districts.json)"),
    ("canonical-sources/references/private-school-associations.json",
     "niche; full-copy tier"),
    ("canonical-sources/index/offline.db",
     "regenerable local build artifact (Claude-side full deployment only)"),
    ("shared/standards/resources/florida/data/index.json",
     "internal manifest — superseded by this MANIFEST.md"),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _fail(msg: str) -> "None":
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _standards_provenance() -> dict:
    """Resolve standards provenance from florida/sources.json — never hardcoded."""
    src = _load(STANDARDS_SOURCES)
    auth = src.get("authorities", {})
    prov = {
        "snapshot": src.get("snapshot"),
        "generated": src.get("generated"),
        "authority": auth.get("standards_repository"),
        "verify_at": auth.get("standards_search"),
        "crawl_seeds": src.get("crawl_seeds", [])[:4],
    }
    if not (prov["snapshot"] and prov["authority"] and prov["verify_at"]):
        _fail("standards provenance unresolvable from florida/sources.json")
    return prov


def _pack_spec() -> list[dict]:
    """The full pack: dest name, source path(s), teacher-language purpose, provenance.
    Provenance is RESOLVED FROM REPO DATA here; a row that can't cite its source fails."""
    sp = _standards_provenance()
    spec: list[dict] = []

    for subj in STANDARDS_SUBJECTS:
        src = STANDARDS_DATA / f"{subj}.json"
        d = _load(src)
        label = subj.replace("_", " ")
        note = " (best-effort parse from a legacy .doc — always verify)" if subj == "social_studies" else ""
        spec.append({
            "dest": f"fl-standards-{subj.replace('_', '-')}.json",
            "src": src, "rows": d.get("count"),
            "what": f"Florida {label} standards — code + full statement{note}",
            "authority": sp["authority"],
            "snapshot": f"{sp['snapshot']} (generated {sp['generated']})",
            "verify": f"search the code at {sp['verify_at']}",
        })

    cc = _load(REFS / "fl-course-codes.json")
    if not cc.get("source"):
        _fail("fl-course-codes.json carries no source field")
    spec.append({
        "dest": "fl-course-codes.json", "src": REFS / "fl-course-codes.json",
        "rows": cc.get("count"),
        "what": "Florida course-code directory — match the numbers on schedules/transcripts to real course titles",
        "authority": cc.get("source"),
        "snapshot": f"captured {cc.get('captured')}",
        "verify": "search the course number at cpalms.org/public/search/Course",
    })

    fd = _load(ROOT / "canonical-sources" / "florida-districts.json")
    if not fd.get("sources"):
        _fail("florida-districts.json carries no sources list")
    spec.append({
        "dest": "fl-districts.json", "src": ROOT / "canonical-sources" / "florida-districts.json",
        "rows": fd.get("count"),
        "what": "All 67 Florida county school districts (the LEAs) — names, numbers, governance",
        "authority": fd["sources"][0],
        "snapshot": "see file _comment",
        "verify": "FLDOE district data pages (URLs in the file's sources list)",
    })

    st = _load(ROOT / "canonical-sources" / "school-types.json")
    auths = sorted({a for t in st.get("types", {}).values() for a in t.get("key_authorities", [])})
    if not auths:
        _fail("school-types.json carries no key_authorities")
    spec.append({
        "dest": "fl-school-types.json", "src": ROOT / "canonical-sources" / "school-types.json",
        "rows": len(st.get("types", {})),
        "what": "Which rules apply to YOUR kind of school (public / magnet / charter / virtual / "
                "home-ed / private) — standards applicability, assessment, governance",
        "authority": "; ".join(auths[:3]) + (" …" if len(auths) > 3 else ""),
        "snapshot": "stubs verified against the cited FLDOE/F.S. authorities",
        "verify": "the key_authorities URLs inside the file",
    })

    fw_auths = []
    for key, p in FRAMEWORKS.items():
        d = _load(p)
        # citation = explicit source field, else the file's own _comment + captured date
        s = d.get("source") or (d.get("_comment", "").split(".")[0] +
                                (f" (captured {d['captured']})" if d.get("captured") else ""))
        if not s.strip():
            _fail(f"{p.name} carries no source citation")
        fw_auths.append(f"{key}: {s}")
    spec.append({
        "dest": "teaching-frameworks.json", "src": list(FRAMEWORKS.values()),
        "rows": len(FRAMEWORKS),
        "what": "The pedagogy vocabulary TOS artifacts use — Bloom's, Webb's DOK, UDL 3.0, "
                "FL FEAPs, the Academic Word List, and the FLDOE toolkit catalog — one file",
        "authority": "each framework keeps its original citation inside the file",
        "snapshot": "per-framework version fields preserved verbatim",
        "verify": "; ".join(fw_auths[:2]) + " … (full citations inside the file)",
    })
    return spec


def _build_frameworks() -> dict:
    out = {"_comment": "GENERATED consolidation of six small canonical reference files (source "
                       "metadata preserved verbatim under each key). Built by "
                       "tools/export_reference_pack.py — never edit by hand.",
           "human_review_required": True}
    for key, p in FRAMEWORKS.items():
        out[key] = _load(p)
    return out


def _manifest(spec: list[dict]) -> str:
    lines = [
        "# Reference Pack — MANIFEST (the receipts)",
        "",
        "*Generated by `tools/export_reference_pack.py` — never edit this folder by hand.*",
        "",
        "Every file below is copied from this repository's canonical data, and every row",
        "says where that data originally came from and **how to double-check it yourself**.",
        "Verified data ships for **Florida only** today. Everything TOS produces from these",
        "files is a **DRAFT — a human must verify anything used in a formal document on the",
        "cited authority** (`human_review_required`).",
        "",
        "| File | What it is | Rows | Original authority | Data as of | How to double-check |",
        "|---|---|---|---|---|---|",
    ]
    for e in spec:
        lines.append(f"| `{e['dest']}` | {e['what']} | {e['rows']} | {e['authority']} "
                     f"| {e['snapshot']} | {e['verify']} |")
    lines += [
        "",
        "## What's NOT in the pack (and why)",
        "",
        "The pack is curated on purpose — these stay in the repository (get them by cloning",
        "the repo — the \"full copy\" tier):",
        "",
    ]
    for what, why in EXCLUSIONS:
        lines.append(f"- **{what}** — {why}")
    lines += [
        "",
        "## Freshness",
        "",
        "Each row's snapshot/captured date above is the honesty line: if a date looks stale,",
        "re-verify on the cited authority before relying on it. The repository's maintainer",
        "pipeline (crawl seeds in `shared/standards/resources/florida/sources.json` and the",
        "source-currency registries) is what refreshes the underlying data.",
        "",
    ]
    return "\n".join(lines)


def build() -> int:
    spec = _pack_spec()
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for e in spec:
        dest = PACK_DIR / e["dest"]
        if isinstance(e["src"], list):  # generated consolidation
            dest.write_text(json.dumps(_build_frameworks(), indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        else:
            shutil.copyfile(e["src"], dest)
        written.append(dest.name)
    (PACK_DIR / "MANIFEST.md").write_text(_manifest(spec), encoding="utf-8")
    written.append("MANIFEST.md")
    # prune anything stale that a previous build left behind
    for p in PACK_DIR.iterdir():
        if p.name not in written:
            p.unlink()
            print(f"  pruned stale {p.name}")
    n = len(written)
    total = sum((PACK_DIR / w).stat().st_size for w in written)
    print(f"Reference pack: {n} files, {total/1e6:.1f} MB -> {PACK_DIR.relative_to(ROOT)}/")
    print(f"Project math: {n} pack + TOS-skills.md + your profile = {n + 2} of ~20 slots")
    if n > MAX_FILES:
        _fail(f"pack exceeds {MAX_FILES} files ({n}) — curate, don't dump")
    return 0


def check() -> int:
    spec = _pack_spec()
    problems = []
    names = {e["dest"] for e in spec} | {"MANIFEST.md"}
    if not PACK_DIR.exists():
        _fail("pack not built — run: python3 tools/export_reference_pack.py")
    for e in spec:
        dest = PACK_DIR / e["dest"]
        if not dest.exists():
            problems.append(f"missing {e['dest']}")
            continue
        if isinstance(e["src"], list):
            rebuilt = json.dumps(_build_frameworks(), indent=2, ensure_ascii=False) + "\n"
            if hashlib.sha256(rebuilt.encode()).hexdigest() != _sha(dest):
                problems.append(f"drift: {e['dest']} != rebuild from sources")
        elif _sha(e["src"]) != _sha(dest):
            problems.append(f"drift: {e['dest']} != {e['src'].relative_to(ROOT)}")
        for field in ("what", "authority", "snapshot", "verify"):
            if not e.get(field):
                problems.append(f"uncited: {e['dest']} missing {field}")
    extra = [p.name for p in PACK_DIR.iterdir() if p.name not in names]
    if extra:
        problems.append(f"unexpected files in pack: {extra}")
    n = len(list(PACK_DIR.iterdir()))
    if n > MAX_FILES:
        problems.append(f"pack has {n} files (max {MAX_FILES})")
    if problems:
        print("PACK DRIFT/CITATION REPORT:")
        for p in problems:
            print(f"  FAIL  {p}")
        return 1
    print(f"OK — {n} files, sha256 matches sources, every row cited, <= {MAX_FILES} files.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build/verify the ChatGPT Reference Pack.")
    ap.add_argument("--check", action="store_true", help="verify only; no writes")
    a = ap.parse_args(argv)
    return check() if a.check else build()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
