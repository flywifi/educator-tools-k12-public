#!/usr/bin/env python3
"""Unified offline index — deterministic, zero-token lookups over all canonical FL reference data.

WHY (token reduction): the reference corpora are huge — FL standards (~1.9 MB), the course-code
directory (~1 MB), school directories, toolkit content. Putting any of it in an LLM prompt costs
thousands–hundreds-of-thousands of tokens PER CALL (and risks hallucination if the model recalls
from memory instead). This builds a local SQLite FTS5 index so a skill answers "what's the course
code for Precalculus Honors?" or "which standards does this toolkit cover?" with a tool call that
returns a handful of exact rows — the model never ingests the corpus. Pure stdlib, fully offline.

INDEXED (all from committed canonical-sources / shared data — nothing fabricated):
  standards          shared/standards/resources/florida/data/*.json        (FL B.E.S.T./NGSSS codes)
  courses            canonical-sources/references/fl-course-codes.json      (4,607 FL course codes)
  schools            canonical-sources/schools/*/schools.json               (Central FL schools)
  toolkit_resources  canonical-sources/references/toolkit-content/*.json    (standard -> CPALMS links)
  data_sources       canonical-sources/registries/fldoe-data-sources.json   (authoritative endpoints)

The DB (canonical-sources/index/offline.db) is a REGENERABLE, gitignored build artifact — never
committed; rebuild from the canonical JSON with --build. Results are advisory + carry provenance.

CLI:
  python3 tools/offline_index.py --build
  python3 tools/offline_index.py --stats                       # row counts + token-savings table
  python3 tools/offline_index.py --course "Precalculus"
  python3 tools/offline_index.py --school "Boone" --district 48
  python3 tools/offline_index.py --standards "fractions" --grade 3
  python3 tools/offline_index.py --resource SC.5.P.10.1        # toolkit links for a standard
  python3 tools/offline_index.py --source assessment
  python3 tools/offline_index.py --course "Algebra" --json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "canonical-sources" / "index" / "offline.db"
STD_DATA = ROOT / "shared" / "standards" / "resources" / "florida" / "data"
COURSES = ROOT / "canonical-sources" / "references" / "fl-course-codes.json"
SCHOOLS = ROOT / "canonical-sources" / "schools"
TOOLKITS = ROOT / "canonical-sources" / "references" / "toolkit-content"
DSOURCES = ROOT / "canonical-sources" / "registries" / "fldoe-data-sources.json"

CHARS_PER_TOKEN = 4  # standard rough estimate for English/JSON


def _fts5_ok(conn) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _p USING fts5(x)")
        conn.execute("DROP TABLE _p")
        return True
    except sqlite3.OperationalError:
        return False


# --------------------------------------------------------------------------- build
def build() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.unlink(missing_ok=True)
    conn = sqlite3.connect(DB)
    fts = _fts5_ok(conn)
    V = "VIRTUAL TABLE" if fts else "TABLE"
    using = "USING fts5" if fts else ""
    counts = {}
    try:
        # ---- standards ----
        conn.execute(f"CREATE {V} standards {using}(code, statement, subject UNINDEXED, "
                     f"grade UNINDEXED, type UNINDEXED, source_file UNINDEXED)" if fts else
                     "CREATE TABLE standards (code TEXT, statement TEXT, subject TEXT, grade TEXT, type TEXT, source_file TEXT)")
        n = 0
        for f in sorted(STD_DATA.glob("*.json")) if STD_DATA.exists() else []:
            if f.name == "index.json":
                continue
            doc = json.loads(f.read_text(encoding="utf-8"))
            subj = doc.get("subject")
            for s in doc.get("standards", []):
                conn.execute("INSERT INTO standards VALUES (?,?,?,?,?,?)",
                             (s.get("code", ""), s.get("statement", ""), subj or "",
                              s.get("grade", ""), s.get("type", ""), f.name))
                n += 1
        counts["standards"] = n

        # ---- courses ----
        conn.execute(f"CREATE {V} courses {using}(course_number, title, path UNINDEXED, link UNINDEXED)" if fts else
                     "CREATE TABLE courses (course_number TEXT, title TEXT, path TEXT, link TEXT)")
        n = 0
        if COURSES.exists():
            for c in json.loads(COURSES.read_text(encoding="utf-8")).get("courses", []):
                conn.execute("INSERT INTO courses VALUES (?,?,?,?)",
                             (c.get("course_number", ""), c.get("title", ""), c.get("path", ""), c.get("link", "")))
                n += 1
        counts["courses"] = n

        # ---- schools ----
        conn.execute(f"CREATE {V} schools {using}(msid UNINDEXED, school_name, district UNINDEXED, "
                     f"type UNINDEXED, levels UNINDEXED, grades UNINDEXED, locale, programs)" if fts else
                     "CREATE TABLE schools (msid TEXT, school_name TEXT, district TEXT, type TEXT, levels TEXT, grades TEXT, locale TEXT, programs TEXT)")
        n = 0
        for sf in sorted(SCHOOLS.glob("*/schools.json")) if SCHOOLS.exists() else []:
            doc = json.loads(sf.read_text(encoding="utf-8"))
            dnum = str(doc.get("district_number", ""))
            for s in doc.get("schools", []):
                progs = ", ".join(
                    (p.get("program_name", "") if isinstance(p, dict) else str(p))
                    for p in s.get("programs", []))
                conn.execute("INSERT INTO schools VALUES (?,?,?,?,?,?,?,?)",
                             (s.get("msid", ""), s.get("school_name", ""), dnum, s.get("type", ""),
                              ",".join(s.get("levels", [])), s.get("grades", ""), s.get("locale", "") or "", progs))
                n += 1
        counts["schools"] = n

        # ---- toolkit_resources (standard -> CPALMS resource links, page-level proximity) ----
        conn.execute(f"CREATE {V} toolkit_resources {using}(standard, toolkit UNINDEXED, subject UNINDEXED, "
                     f"page UNINDEXED, links UNINDEXED)" if fts else
                     "CREATE TABLE toolkit_resources (standard TEXT, toolkit TEXT, subject TEXT, page TEXT, links TEXT)")
        n = 0
        cat = TOOLKITS.parent / "fl-instructional-toolkits.json"
        subj_by_id = {}
        if cat.exists():
            subj_by_id = {r["id"]: r.get("subject") for r in json.loads(cat.read_text()).get("resources", [])}
        for tf in sorted(TOOLKITS.glob("*.json")) if TOOLKITS.exists() else []:
            doc = json.loads(tf.read_text(encoding="utf-8"))
            tid = doc.get("id", tf.stem)
            for pg in doc.get("content", []):
                links = pg.get("links", [])
                for code in pg.get("standards", []):
                    conn.execute("INSERT INTO toolkit_resources VALUES (?,?,?,?,?)",
                                 (code, tid, subj_by_id.get(tid, "") or "", str(pg.get("page", "")),
                                  " | ".join(links[:8])))
                    n += 1
        counts["toolkit_resources"] = n

        # ---- data_sources ----
        conn.execute(f"CREATE {V} data_sources {using}(id, url UNINDEXED, label, category, status UNINDEXED)" if fts else
                     "CREATE TABLE data_sources (id TEXT, url TEXT, label TEXT, category TEXT, status TEXT)")
        n = 0
        if DSOURCES.exists():
            for s in json.loads(DSOURCES.read_text(encoding="utf-8")).get("sources", []):
                conn.execute("INSERT INTO data_sources VALUES (?,?,?,?,?)",
                             (s.get("id", ""), s.get("url", ""), s.get("label") or "",
                              s.get("category", ""), s.get("status", "")))
                n += 1
        counts["data_sources"] = n

        conn.execute("CREATE TABLE idx_meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO idx_meta VALUES ('built_at', ?)",
                     (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),))
        conn.execute("INSERT INTO idx_meta VALUES ('engine', ?)", ("fts5" if fts else "like_fallback",))
        conn.execute("INSERT INTO idx_meta VALUES ('counts', ?)", (json.dumps(counts),))
        conn.commit()
    finally:
        conn.close()
    total = sum(counts.values())
    print(f"Built {DB.relative_to(ROOT)} [{('fts5' if fts else 'like_fallback')}] — {total} rows: {counts}")
    return 0


# --------------------------------------------------------------------------- query
def _q(table, search_cols, text, filters, limit):
    if not DB.exists():
        raise FileNotFoundError("index not built — run: python3 tools/offline_index.py --build")
    conn = sqlite3.connect(DB)
    try:
        engine = conn.execute("SELECT value FROM idx_meta WHERE key='engine'").fetchone()
        engine = engine[0] if engine else "like_fallback"
        # get column names
        cur = conn.execute(f"SELECT * FROM {table} LIMIT 0")
        colnames = [d[0] for d in cur.description]
        where, params = [], []
        for col, val in (filters or {}):
            where.append(f"{col} = ?"); params.append(val)
        if text and engine == "fts5":
            import re as _re
            # PREFIX match (token*) so "fraction" also matches "fractions"/"fractional" — FTS5
            # unicode61 does not stem, and exact-token match silently misses inflected forms.
            match = " ".join(f'"{t}"*' for t in _re.findall(r"[A-Za-z0-9.]+", text))
            sql = f"SELECT * FROM {table} WHERE {table} MATCH ?"
            params = [match] + params
            if where:
                sql += " AND " + " AND ".join(where)
            sql += f" ORDER BY bm25({table}) LIMIT ?"
        else:
            if text:
                ors = " OR ".join(f"{c} LIKE ?" for c in search_cols)
                where.insert(0, f"({ors})")
                params = [f"%{text}%"] * len(search_cols) + params
            sql = f"SELECT * FROM {table}"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " LIMIT ?"
        params.append(limit)
        return [dict(zip(colnames, r)) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


# --------------------------------------------------------------------------- stats + token quantification
def _bytes_to_tokens(b: int) -> int:
    return round(b / CHARS_PER_TOKEN)


def stats() -> int:
    if not DB.exists():
        print("index not built — run --build", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB)
    counts = json.loads(conn.execute("SELECT value FROM idx_meta WHERE key='counts'").fetchone()[0])
    conn.close()
    # corpus sizes (what the model would otherwise have to ingest)
    def dsize(*paths):
        t = 0
        for p in paths:
            if p.is_dir():
                t += sum(f.stat().st_size for f in p.glob("**/*.json"))
            elif p.exists():
                t += p.stat().st_size
        return t
    corpora = {
        "standards": dsize(STD_DATA),
        "courses": dsize(COURSES),
        "schools": dsize(*[p for p in SCHOOLS.glob("*/schools.json")]),
        "toolkit_resources": dsize(TOOLKITS),
        "data_sources": dsize(DSOURCES),
    }
    print(json.dumps({"db": str(DB.relative_to(ROOT)), "rows": counts}, indent=2))
    print("\nTOKEN-SAVINGS (corpus you DON'T load vs a typical lookup):")
    print(f"  {'dataset':18} {'rows':>6} {'corpus_KB':>10} {'corpus_tokens':>14} {'typical_lookup_tokens':>22} {'reduction':>10}")
    tot_corpus = 0
    for k in counts:
        b = corpora.get(k, 0); tot_corpus += b
        ctok = _bytes_to_tokens(b)
        lookup = 250  # a typical 5-row result ~ 250 tokens
        red = (1 - lookup / ctok) * 100 if ctok else 0
        print(f"  {k:18} {counts[k]:>6} {b/1024:>10.1f} {ctok:>14,} {lookup:>22,} {red:>9.1f}%")
    print(f"  {'-'*18}")
    print(f"  whole corpus tokens ≈ {_bytes_to_tokens(tot_corpus):,}  ·  a lookup returns ≈250 → "
          f"~{(1-250/_bytes_to_tokens(tot_corpus))*100:.2f}% reduction per reference need")
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Unified offline index — zero-token reference lookups")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--course"); ap.add_argument("--school"); ap.add_argument("--standards")
    ap.add_argument("--resource", help="toolkit resource links for a standard code")
    ap.add_argument("--source", help="search the data-source endpoint index")
    ap.add_argument("--district"); ap.add_argument("--grade"); ap.add_argument("--subject")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.build:
        return build()
    if a.stats:
        return stats()
    rows, label = None, ""
    try:
        if a.course is not None:
            rows = _q("courses", ["course_number", "title"], a.course, [], a.limit); label = "courses"
        elif a.school is not None:
            filt = [("district", a.district)] if a.district else []
            rows = _q("schools", ["school_name", "locale", "programs"], a.school, filt, a.limit); label = "schools"
        elif a.standards is not None:
            filt = [(c, v) for c, v in [("subject", a.subject), ("grade", a.grade)] if v]
            rows = _q("standards", ["code", "statement"], a.standards, filt, a.limit); label = "standards"
        elif a.resource is not None:
            rows = _q("toolkit_resources", ["standard"], a.resource, [], a.limit); label = "toolkit_resources"
        elif a.source is not None:
            rows = _q("data_sources", ["id", "label", "category"], a.source, [], a.limit); label = "data_sources"
        else:
            ap.print_help(); return 0
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 1
    if a.json:
        print(json.dumps({"index": label, "count": len(rows), "results": rows,
                          "advisory": "verify standards/courses on CPALMS"}, indent=2))
    else:
        print(f"{len(rows)} {label} match(es):")
        for r in rows:
            print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v)[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
