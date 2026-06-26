#!/usr/bin/env python3
"""Local-First standards cache (L1) — deterministic, offline, low-token retrieval.

Builds a local SQLite full-text index over the enumerated Florida standards
(``shared/standards/resources/florida/data/*.json`` — 6,583 codes) so a lookup
returns a handful of ranked snippets + provenance instead of making the model read
~1.9 MB of JSON. This is the default offline tier: pure stdlib (``sqlite3`` + FTS5),
fully offline, zero token cost at query time.

The index is a **regenerable, gitignored build artifact** (``index.local.db``) — it
is never committed; rebuild it from the canonical JSON with ``--build``. Results are
**advisory** and carry provenance (subject + source file); always verify on CPALMS
(https://www.cpalms.org/search/Standard). Nothing here fabricates standards.

If FTS5 is unavailable in the host's SQLite build, the engine falls back to a plain
LIKE scan and reports the reduced capability honestly (it never pretends FTS5 ran).

CLI:
  python3 shared/cache/cache.py --build                          # (re)build the local index
  python3 shared/cache/cache.py --stats                          # row counts + freshness
  python3 shared/cache/cache.py --query "fractions" --subject math --grade 3 --limit 5
  python3 shared/cache/cache.py --query "main idea" --json       # machine-readable snippets
  python3 shared/cache/cache.py --verify                         # source files vs build baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = ROOT / "shared" / "standards" / "resources" / "florida" / "data"
DB = HERE / "index.local.db"

SUBJECTS = ["math", "ela", "science", "computer_science", "eld", "social_studies"]
CPALMS = "https://www.cpalms.org/search/Standard"

# FTS5 columns: statement + code are tokenized (searched); the rest are stored
# UNINDEXED so they can still be filtered/returned without bloating the index.
_SEARCH_COLS = "code, statement"
_STORE_COLS = "subject UNINDEXED, grade UNINDEXED, strand UNINDEXED, type UNINDEXED, source_file UNINDEXED"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fts5_ok(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE _fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def _source_files() -> list[Path]:
    if not DATA.exists():
        return []
    return [f for f in sorted(DATA.glob("*.json")) if f.name != "index.json"]


def _iter_standards():
    """Yield (record, source_file_name) for every enumerated standard."""
    for f in _source_files():
        doc = json.loads(f.read_text(encoding="utf-8"))
        subject = doc.get("subject")
        for s in doc.get("standards", []):
            yield s, subject, f.name


# --------------------------------------------------------------------------- build
def build() -> int:
    if not DATA.exists():
        print(f"No standards data at {DATA.relative_to(ROOT)} — "
              "run: python3 tools/parse_fl_standards.py", file=sys.stderr)
        return 1

    DB.unlink(missing_ok=True)
    conn = sqlite3.connect(DB)
    fts = _fts5_ok(conn)
    try:
        if fts:
            conn.execute(
                f"CREATE VIRTUAL TABLE standards USING fts5({_SEARCH_COLS}, {_STORE_COLS}, "
                "tokenize='unicode61')"
            )
        else:
            conn.execute(
                "CREATE TABLE standards (code TEXT, statement TEXT, subject TEXT, "
                "grade TEXT, strand TEXT, type TEXT, source_file TEXT)"
            )
        conn.execute("CREATE TABLE cache_meta (key TEXT PRIMARY KEY, value TEXT)")

        rows, baselines = 0, {}
        for s, subject, fname in _iter_standards():
            conn.execute(
                "INSERT INTO standards (code, statement, subject, grade, strand, type, source_file) "
                "VALUES (?,?,?,?,?,?,?)",
                (s.get("code", ""), s.get("statement", ""), subject or "",
                 s.get("grade", ""), s.get("strand", ""), s.get("type", ""), fname),
            )
            rows += 1
        if not fts:
            conn.execute("CREATE INDEX idx_subject ON standards(subject)")
            conn.execute("CREATE INDEX idx_code ON standards(code)")

        for f in _source_files():
            baselines[f.name] = {"sha256": _sha256(f), "bytes": f.stat().st_size}

        meta = {
            "built_at": _now(),
            "rows": rows,
            "fts5": fts,
            "engine": "fts5" if fts else "like_fallback",
            "source_dir": str(DATA.relative_to(ROOT)),
            "baselines": baselines,
        }
        for k, v in meta.items():
            conn.execute("INSERT INTO cache_meta (key, value) VALUES (?,?)",
                         (k, json.dumps(v) if not isinstance(v, str) else v))
        conn.commit()
    finally:
        conn.close()

    note = "" if fts else "  (FTS5 unavailable — built LIKE fallback; queries are slower, no ranking)"
    print(f"Built {DB.relative_to(ROOT)} — {rows} standards indexed [{meta['engine']}]{note}")
    return 0


# --------------------------------------------------------------------------- query
def _fts_query(text: str) -> str:
    """Build a safe FTS5 MATCH string: bare alnum tokens, implicit AND."""
    tokens = re.findall(r"[A-Za-z0-9.]+", text)
    return " ".join(f'"{t}"' for t in tokens)


def _meta(conn: sqlite3.Connection, key: str):
    row = conn.execute("SELECT value FROM cache_meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return row[0]


def query(text: str | None, subject: str | None, grade: str | None,
          type_: str | None, code: str | None, limit: int) -> list[dict]:
    if not DB.exists():
        raise FileNotFoundError("index not built — run: python3 shared/cache/cache.py --build")
    conn = sqlite3.connect(DB)
    try:
        engine = _meta(conn, "engine") or "like_fallback"
        where, params = [], []
        if subject:
            where.append("subject = ?"); params.append(subject)
        if grade:
            where.append("grade = ?"); params.append(grade)
        if type_:
            where.append("type = ?"); params.append(type_)
        if code:
            where.append("code LIKE ?"); params.append(code + "%")

        if text and engine == "fts5":
            match = _fts_query(text)
            base = ("SELECT code, statement, subject, grade, strand, type, source_file "
                    "FROM standards WHERE standards MATCH ?")
            params = [match] + params
            if where:
                base += " AND " + " AND ".join(where)
            base += " ORDER BY bm25(standards) LIMIT ?"
        else:
            if text:  # LIKE fallback (no FTS5) or text alongside no MATCH
                where.append("statement LIKE ?"); params.append(f"%{text}%")
            base = ("SELECT code, statement, subject, grade, strand, type, source_file "
                    "FROM standards")
            if where:
                base += " WHERE " + " AND ".join(where)
            base += " LIMIT ?"
        params.append(limit)
        cols = ["code", "statement", "subject", "grade", "strand", "type", "source_file"]
        return [dict(zip(cols, r)) for r in conn.execute(base, params).fetchall()]
    finally:
        conn.close()


# --------------------------------------------------------------------------- stats / verify
def stats() -> int:
    if not DB.exists():
        print("index not built — run: python3 shared/cache/cache.py --build", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB)
    try:
        total = conn.execute("SELECT count(*) FROM standards").fetchone()[0]
        by_sub = conn.execute(
            "SELECT subject, count(*) FROM standards GROUP BY subject ORDER BY 2 DESC"
        ).fetchall()
        print(json.dumps({
            "db": str(DB.relative_to(ROOT)),
            "built_at": _meta(conn, "built_at"),
            "engine": _meta(conn, "engine"),
            "total": total,
            "by_subject": {s: n for s, n in by_sub},
        }, indent=2))
    finally:
        conn.close()
    return 0


def verify() -> int:
    """Compare current source files against the baseline recorded at build time.

    Reports added / removed / changed / current so a later sync (L3) can rebuild
    only what moved. Never re-baselines on its own.
    """
    if not DB.exists():
        print("index not built — run: python3 shared/cache/cache.py --build", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB)
    try:
        baselines = _meta(conn, "baselines") or {}
    finally:
        conn.close()
    current = {f.name: _sha256(f) for f in _source_files()}
    report = {"changed": [], "removed": [], "added": [], "current": []}
    for name, base in baselines.items():
        if name not in current:
            report["removed"].append(name)
        elif current[name] != base.get("sha256"):
            report["changed"].append(name)
        else:
            report["current"].append(name)
    for name in current:
        if name not in baselines:
            report["added"].append(name)
    drift = bool(report["changed"] or report["removed"] or report["added"])
    print(json.dumps({"stale": drift, **report}, indent=2))
    return 1 if drift else 0


def _print_human(rows: list[dict]) -> None:
    print(f"{len(rows)} match(es):")
    for r in rows:
        stmt = (r["statement"] or "").strip()
        if len(stmt) > 200:
            stmt = stmt[:197] + "..."
        print(f"  [{r['code']}] ({r['subject']}/{r['grade']}/{r['type']})  {stmt}")
        print(f"      ↳ source: {r['source_file']}")
    print(f"\nAdvisory — verify on CPALMS: {CPALMS}")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Local-First standards cache (L1)")
    ap.add_argument("--build", action="store_true", help="(re)build the local index")
    ap.add_argument("--stats", action="store_true", help="show index stats + freshness")
    ap.add_argument("--verify", action="store_true", help="check source files vs build baseline")
    ap.add_argument("--query", metavar="TEXT", help="full-text query over standard statements + codes")
    ap.add_argument("--subject", choices=SUBJECTS)
    ap.add_argument("--grade")
    ap.add_argument("--type", choices=["benchmark", "access_point", "practice"])
    ap.add_argument("--code", help="exact or prefix match on the code")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of human text")
    a = ap.parse_args(argv)

    if a.build:
        return build()
    if a.stats:
        return stats()
    if a.verify:
        return verify()
    if a.query is not None or a.code or a.subject or a.grade or a.type:
        try:
            rows = query(a.query, a.subject, a.grade, a.type, a.code, a.limit)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 1
        if a.json:
            print(json.dumps({"query": a.query, "count": len(rows), "results": rows,
                              "advisory": f"verify on CPALMS: {CPALMS}"}, indent=2))
        else:
            _print_human(rows)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
