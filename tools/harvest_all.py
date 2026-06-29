#!/usr/bin/env python3
"""harvest_all.py — all-in local harvesting pipeline (scan -> fetch -> parse -> validate -> catalog -> handoff).

The next iteration of run_ingest: one command that takes a folder of saved sources (and/or a list of
URLs) and drives the WHOLE pipeline on your own machine, unrestricted, token-free. It composes the
existing tools rather than duplicating them:

  SCAN      classify every file in the inbox by content signature (html/xls/xlsx/pdf/docx/...).
  FETCH     (optional, UNRESTRICTED) acquire URLs via the resilient chain — full browser headers ->
            requests -> headless browser -> Wayback — with --ignore-robots for authorized public data.
            Re-acquires any 'captured_unparsed' URL already in the base catalog, or a --urls file.
  PARSE     route each file to a parser: NCES PSS / AISF (private schools), CPALMS course xlsx
            (courses), PDF + DOCX toolkits (standards + CPALMS links + full text). Unknown -> base only.
  VALIDATE  dedup private schools across sources; CROSS-CHECK extracted standard codes against the
            offline index (coverage %); run the drift guard.
  CATALOG   write canonical datasets, record EVERY file at base level (with URL) in
            ingested-sources.json, rebuild the unified offline index.
  HANDOFF   write HARVEST_HANDOFF.md (what changed + human_review_required items) and, with --push,
            git add/commit/push the data.

Deps: pure stdlib core. Optional: requests (fetch), openpyxl (xlsx), pymupdf/fitz (pdf). DOCX is stdlib.
Each absent dep is an honest capability gap, never faked. Nothing is fabricated — only parsed/fetched.

USAGE
  python3 tools/harvest_all.py --inbox source_inbox                      # scan+parse+validate+catalog
  python3 tools/harvest_all.py --inbox source_inbox --fetch --ignore-robots
  python3 tools/harvest_all.py --inbox source_inbox --urls urls.txt --fetch --push
  python3 tools/harvest_all.py --inbox source_inbox --dry-run
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

# reuse the existing ingester's parsers / dedup / base-catalog (single source of truth)
import ingest_sources as ING  # noqa: E402

TOOLKIT_DIR = ROOT / "canonical-sources" / "references" / "toolkit-content"
STD_RE = re.compile(r"\b(?:LAFS|MAFS|SC|SS|HE|PE|VA|MU|TH|DA|ELA|MA|ELD)\.[K0-9]{1,2}"
                    r"\.[A-Za-z0-9]+(?:\.[A-Za-z0-9]+){1,3}\b")
BENCH_RE = re.compile(r"\b(?:MA|ELA)\.[K0-9]{1,2}\.[A-Z]+\.[0-9]+\.[0-9]+$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# --------------------------------------------------------------------------- PARSE: pdf / docx toolkits
def parse_pdf_toolkit(path: Path, tid: str):
    try:
        import fitz
    except Exception:
        return None  # capability gap — handled by caller
    doc = fitz.open(path)
    pages, links, stds = [], set(), set()
    for i, pg in enumerate(doc):
        txt = pg.get_text()
        pl = sorted({l.get("uri") for l in pg.get_links() if l.get("uri")})
        ps = sorted(set(STD_RE.findall(txt)))
        links |= set(pl); stds |= set(ps)
        pages.append({"page": i + 1, "text": txt, "links": pl, "standards": ps})
    doc.close()
    return {"id": tid, "source_file": path.name, "pages": len(pages),
            "standards_covered": sorted(stds), "all_links": sorted(links), "content": pages,
            "captured": _now()[:10], "provenance": "harvest_all pdf extract (pymupdf)"}


def parse_docx_toolkit(path: Path, tid: str):
    z = zipfile.ZipFile(path)
    try:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    except KeyError:
        return None
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", xml)))
    links = []
    try:
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8", "replace")
        links = sorted(set(re.findall(r'Target="(https?://[^"]+)"', rels)))
    except KeyError:
        pass
    stds = sorted(set(STD_RE.findall(text)))
    return {"id": tid, "source_file": path.name, "pages": 1,
            "standards_covered": stds, "all_links": links,
            "content": [{"page": 1, "text": text, "links": links, "standards": stds}],
            "captured": _now()[:10], "provenance": "harvest_all docx extract (stdlib)"}


# --------------------------------------------------------------------------- pipeline
def scan(inbox: Path) -> list[dict]:
    out = []
    for f in sorted(inbox.rglob("*")):  # recursive: picks up acquired subfolders (rendered/wayback/files/)
        if not f.is_file() or f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif") or f.name == "manifest.json":
            continue
        suf = f.suffix.lower()
        if suf in (".pdf",):
            kind = "pdf_toolkit"
        elif suf == ".docx":
            kind = "docx_toolkit"
        elif suf == ".zip":
            kind = "zip"
        else:
            text = f.read_text(encoding="utf-8", errors="replace")
            kind = ING.detect(f, text)
        out.append({"file": f, "kind": kind})
    return out


def fetch_phase(urls: list[str], inbox: Path, ignore_robots: bool, report: list[str], depth: int) -> None:
    """Combined redundant acquisition per URL (token-free): browser-headers + headless render +
    screenshot/OCR + mirror linked files/pages + Wayback backstop. Keeps every artifact for parsing."""
    try:
        from acquire import acquire
    except Exception as e:
        report.append(f"  [fetch] acquirer unavailable: {e.__class__.__name__}")
        return
    for u in urls:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", u)[:70]
        m = acquire(u, inbox / slug, ignore_robots=ignore_robots, depth=depth)
        arts = m.get("artifacts", {})
        got = "+".join(k for k, v in arts.items() if v) or "none"
        report.append(f"  [fetch] {'OK' if m.get('ok_any') else 'FAIL'}: {u}  [{got}]")


def validate_standards(all_codes: set[str], report: list[str]) -> dict:
    """Cross-check extracted benchmark codes against the offline index — coverage %, like the
    100% B.E.S.T. Math verification. Honest: reports gaps, never asserts coverage it can't show."""
    bench = {c for c in all_codes if BENCH_RE.match(c)}
    if not bench:
        return {"checked": 0}
    rc, out = _run([sys.executable, str(HERE / "offline_index.py"), "--standards", "MA", "--limit", "9000", "--json"])
    try:
        idx = {r["code"] for r in json.loads(out).get("results", [])}
    except Exception:
        idx = set()
    present = bench & idx
    pct = 100 * len(present) // max(len(bench), 1)
    gaps = sorted(bench - idx)[:10]
    report.append(f"  [validate] standards cross-check: {len(present)}/{len(bench)} benchmark codes in index ({pct}%)"
                  + (f"; gaps e.g. {gaps}" if gaps else "; no gaps"))
    return {"checked": len(bench), "present": len(present), "pct": pct, "gaps": gaps}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inbox", required=True)
    ap.add_argument("--urls", help="file of URLs to resilient-fetch into the inbox (one per line)")
    ap.add_argument("--fetch", action="store_true", help="run the unrestricted fetch phase")
    ap.add_argument("--ignore-robots", action="store_true", help="maintainer override for public data")
    ap.add_argument("--depth", type=int, default=1, help="mirror depth for same-domain pages (default 1)")
    ap.add_argument("--push", action="store_true", help="git add+commit+push the catalogued data")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    inbox = Path(a.inbox)
    inbox.mkdir(parents=True, exist_ok=True)
    report = [f"# harvest_all — {_now()}"]

    # ---- FETCH (optional, unrestricted) ----
    if a.fetch:
        report.append("\n## FETCH")
        urls = []
        if a.urls and Path(a.urls).exists():
            urls += [l.strip() for l in Path(a.urls).read_text().splitlines() if l.strip() and not l.startswith("#")]
        cat = ING.INGESTED
        if cat.exists():  # re-acquire previously captured-but-unparsed URLs
            for s in json.loads(cat.read_text()).get("sources", []):
                if s.get("status") == "captured_unparsed" and s.get("source_url"):
                    urls.append(s["source_url"])
        urls = sorted(set(urls))
        report.append(f"  {len(urls)} URL(s) to acquire (browser+render+screenshot/OCR+mirror+wayback)")
        if not a.dry_run:
            fetch_phase(urls, inbox, a.ignore_robots, report, a.depth)

    # ---- SCAN ----
    report.append("\n## SCAN")
    items = scan(inbox)
    for it in items:
        report.append(f"  {it['kind']:18} {it['file'].name[:54]}")

    # ---- PARSE ----
    report.append("\n## PARSE")
    priv_in, course_in, base, all_codes = [], [], [], set()
    TOOLKIT_DIR.mkdir(parents=True, exist_ok=True)
    for it in items:
        f, kind = it["file"], it["kind"]
        text = "" if f.suffix.lower() in (".xlsx", ".pdf", ".zip", ".docx") else f.read_text(encoding="utf-8", errors="replace")
        recs = 0; status = "captured_unparsed"; tk = None
        if kind == "nces_pss":
            r = ING.parse_nces_pss(text, f.name); priv_in += r; recs = len(r); status = "parsed"
        elif kind == "aisf_directory":
            r = ING.parse_aisf(text, f.name); priv_in += r; recs = len(r); status = "parsed"
        elif kind == "xlsx_course_export":
            r = ING.parse_course_xlsx(f, f.name); course_in += r; recs = len(r); status = "parsed"
        elif kind == "pdf_toolkit":
            tk = parse_pdf_toolkit(f, f.stem)
            status = "parsed" if tk else "capability_gap_pymupdf"
        elif kind == "docx_toolkit":
            tk = parse_docx_toolkit(f, f.stem)
            status = "parsed" if tk else "captured_unparsed"
        if tk:
            recs = len(tk["standards_covered"]); all_codes |= set(tk["standards_covered"])
            if not a.dry_run:
                (TOOLKIT_DIR / f"{f.stem}.json").write_text(json.dumps(tk, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report.append(f"  {kind:18} {recs:5} -> {f.name[:46]} [{status}]")
        base.append({"file": f.name, "source_url": ING._saved_url(text) if text else None,
                     "title": ING._title(text) if text else None, "detected_type": kind,
                     "status": status, "rows": recs, "captured": _now()[:10]})

    # ---- VALIDATE ----
    report.append("\n## VALIDATE")
    consolidated = ING.PRIV_DIR / "private-schools-consolidated.json"
    existing = json.loads(consolidated.read_text())["members"] if consolidated.exists() else []
    merged, added, dedup = ING.merge_private(existing, priv_in)
    report.append(f"  [validate] private schools: +{added} new, {dedup} deduped -> {len(merged)} total")
    val = validate_standards(all_codes, report)

    if a.dry_run:
        report.append("\n[dry-run] no writes, no index rebuild, no commit.")
        print("\n".join(report)); return 0

    # ---- CATALOG ----
    report.append("\n## CATALOG")
    ING.PRIV_DIR.mkdir(parents=True, exist_ok=True)
    consolidated.write_text(json.dumps({
        "_comment": "Consolidated + deduped private schools (harvest_all).", "domain": "private-schools-consolidated",
        "captured": _now()[:10], "count": len(merged), "human_review_required": True, "members": merged,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_cat = ING.catalog_base(base)
    report.append(f"  base catalog: {len(base)} files ({n_cat} new) in {ING.INGESTED.relative_to(ROOT)}")
    rc, out = _run([sys.executable, str(HERE / "offline_index.py"), "--build"])
    report.append("  " + (out.strip().splitlines()[-1] if out.strip() else f"index build rc={rc}"))
    rc, out = _run([sys.executable, str(HERE / "sync_check.py")])
    report.append(f"  drift guard: {'PASS' if rc == 0 else 'FAIL'} ({out.strip().splitlines()[-1][:70]})")

    # ---- HANDOFF ----
    report.append("\n## HANDOFF")
    needs_review = [b for b in base if b["status"].startswith(("captured_unparsed", "capability_gap"))]
    report.append(f"  human_review_required: {len(needs_review)} unparsed/gap source(s) cataloged by URL for later")
    (ROOT / "HARVEST_HANDOFF.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    print(f"\nHandoff report: HARVEST_HANDOFF.md")

    if a.push:
        _run(["git", "add", "canonical-sources/schools/private", "canonical-sources/references",
              "canonical-sources/registries/ingested-sources.json"])
        rc, out = _run(["git", "commit", "-m", f"data: harvest_all ingest {_now()[:10]}"])
        if "nothing to commit" not in out.lower():
            br = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])[1].strip()
            _run(["git", "push", "-u", "origin", br])
            print(f"  pushed to {br}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
