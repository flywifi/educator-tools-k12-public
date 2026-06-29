#!/usr/bin/env python3
"""Optional local semantic index (L2) over the L1 standards cache — opt-in, capability-gated.

Adds offline VECTOR recall (paraphrase matches that keyword search misses) on top of the L1 SQLite
cache, using `sqlite-vec` for storage and a LOCAL embedding backend. It is **off by default** and only
activates when BOTH are true:

  1. the optional deps are installed (`sqlite-vec` + an embedder — see tools/requirements-semantic.txt), and
  2. the teacher has granted consent (`local_first.consents.local_semantic` in the gitignored profile).

When either is missing the engine does **not** guess: `search()` falls back to L1 keyword search and
returns an honest `gap` explaining why the vector path was skipped. No data leaves the machine — vectors
are derived from the PUBLIC standards text only; no student data is ever embedded.

CLI:
  python3 shared/cache/semantic.py --status                       # what's available + consent state
  python3 shared/cache/semantic.py --build                        # build the vector index (needs deps+consent)
  python3 shared/cache/semantic.py --search "adding parts of a whole" --k 5 --subject math
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PROFILE = ROOT / "shared" / "context" / "profiles" / "teacher.local.json"
CONSENT_KEY = "local_semantic"
EMBED_DIM = 384  # all-MiniLM-L6-v2; the vec table is created to match the active embedder

# Import the sibling L1 cache (keyword search + the canonical standards iterator) without assuming
# shared/ is on sys.path.
sys.path.insert(0, str(HERE))
import cache as l1  # noqa: E402


def _has(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


# --------------------------------------------------------------- capability + consent detection
def embedder_backend() -> str | None:
    """First available LOCAL embedding backend, or None. Order: sentence-transformers, llm CLI."""
    if _has("sentence_transformers"):
        return "sentence_transformers"
    if _has("llm"):
        return "llm"
    return None


def read_consent() -> bool:
    """True only if the teacher explicitly granted local_semantic consent (reversible, L0)."""
    if not PROFILE.exists():
        return False
    try:
        prof = json.loads(PROFILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return bool((prof.get("local_first", {}).get("consents", {})
                 .get(CONSENT_KEY, {}) or {}).get("granted"))


def capability_status() -> dict:
    vec = _has("sqlite_vec")
    emb = embedder_backend()
    consent = read_consent()
    ready = bool(vec and emb and consent)
    if ready:
        reason = "ready"
    elif not consent:
        reason = "consent not granted — opt in via the teacher-profile wizard (--consent local_semantic)"
    elif not vec:
        reason = "sqlite-vec not installed — pip install -r tools/requirements-semantic.txt"
    else:
        reason = "no local embedding backend — install sentence-transformers (or the llm CLI)"
    return {"capability": "local_semantic", "ready": ready, "reason": reason,
            "sqlite_vec": vec, "embedder": emb, "consent": consent,
            "vector_db": str((HERE / "semantic.local.db").relative_to(ROOT))}


# --------------------------------------------------------------- embeddings (active only when present)
def _embed(texts: list[str], backend: str) -> list[list[float]]:
    if backend == "sentence_transformers":
        from sentence_transformers import SentenceTransformer  # type: ignore
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return [list(map(float, v)) for v in model.encode(texts, normalize_embeddings=True)]
    if backend == "llm":
        import llm  # type: ignore
        model = llm.get_embedding_model("sentence-transformers/all-MiniLM-L6-v2")
        return [list(map(float, model.embed(t))) for t in texts]
    raise RuntimeError(f"unknown embedding backend: {backend}")


VEC_DB = HERE / "semantic.local.db"


def build() -> int:
    st = capability_status()
    if not st["ready"]:
        print(json.dumps({"status": "skipped", **st}, indent=2))
        return 1
    import sqlite_vec  # type: ignore

    rows = [(s.get("code", ""), s.get("statement", ""), subject or "",
             s.get("grade", ""), s.get("type", ""))
            for s, subject, _ in l1._iter_standards()]
    backend = st["embedder"]
    vectors = _embed([f"{code}: {stmt}" for code, stmt, *_ in rows], backend)

    VEC_DB.unlink(missing_ok=True)
    conn = sqlite3.connect(VEC_DB)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    dim = int(len(vectors[0]) if vectors else EMBED_DIM)  # integer vector-column dimension
    conn.execute(f"CREATE VIRTUAL TABLE vec_standards USING vec0(embedding float[{dim}])")  # nosemgrep  (dim is an int; DDL dimensions cannot be bound params)
    conn.execute("CREATE TABLE meta_standards (rowid INTEGER PRIMARY KEY, code TEXT, statement TEXT, "
                 "subject TEXT, grade TEXT, type TEXT)")
    for i, ((code, stmt, subj, grade, typ), vec) in enumerate(zip(rows, vectors), start=1):
        conn.execute("INSERT INTO vec_standards (rowid, embedding) VALUES (?, ?)",
                     (i, sqlite_vec.serialize_float32(vec)))
        conn.execute("INSERT INTO meta_standards VALUES (?,?,?,?,?,?)",
                     (i, code, stmt, subj, grade, typ))
    conn.commit()
    conn.close()
    print(json.dumps({"status": "built", "rows": len(rows), "dim": dim,
                      "backend": backend, "db": str(VEC_DB.relative_to(ROOT))}, indent=2))
    return 0


def vector_query(text: str, k: int, subject: str | None, grade: str | None) -> list[dict]:
    import sqlite_vec  # type: ignore
    st = capability_status()
    qv = _embed([text], st["embedder"])[0]
    conn = sqlite3.connect(VEC_DB)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    params: list = [sqlite_vec.serialize_float32(qv), k]
    # Fully static SQL (adjacent string literals, not runtime concatenation); values are bound via ?.
    rows = conn.execute(
        "SELECT m.code, m.statement, m.subject, m.grade, m.type, v.distance "
        "FROM vec_standards v JOIN meta_standards m ON m.rowid = v.rowid "
        "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance", params).fetchall()
    conn.close()
    out = []
    for code, stmt, subj, grade_, typ, dist in rows:
        if subject and subj != subject:
            continue
        if grade and grade_ != grade:
            continue
        out.append({"code": code, "statement": stmt, "subject": subj, "grade": grade_,
                    "type": typ, "distance": round(float(dist), 4)})
    return out


# --------------------------------------------------------------- unified, consent-aware entry point
def search(text: str, k: int = 10, subject: str | None = None, grade: str | None = None) -> dict:
    """Semantic search when opted-in and available; otherwise transparent L1 keyword fallback.

    Always returns: {engine, results, gap?}. The caller (or the model) sees exactly which path served
    the answer and why — the fallback is never disguised as a vector result.
    """
    st = capability_status()
    if st["ready"] and VEC_DB.exists():
        return {"engine": "vector", "query": text,
                "results": vector_query(text, k, subject, grade)}
    if st["ready"] and not VEC_DB.exists():
        gap = "vector index not built yet — run: python3 shared/cache/semantic.py --build"
    else:
        gap = st["reason"]
    try:
        kw = l1.query(text, subject, grade, None, None, k)
    except FileNotFoundError as e:
        return {"engine": "none", "gap": f"{gap}; and L1 cache unavailable: {e}", "results": []}
    return {"engine": "keyword_fallback", "query": text, "gap": gap, "results": kw}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Optional local semantic index (L2) — opt-in, gated")
    ap.add_argument("--status", action="store_true", help="show availability + consent state")
    ap.add_argument("--build", action="store_true", help="build the vector index (needs deps + consent)")
    ap.add_argument("--search", metavar="TEXT", help="semantic search (falls back to L1 keyword)")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--subject", choices=l1.SUBJECTS)
    ap.add_argument("--grade")
    a = ap.parse_args(argv)

    if a.status:
        print(json.dumps(capability_status(), indent=2))
        return 0
    if a.build:
        return build()
    if a.search is not None:
        print(json.dumps(search(a.search, a.k, a.subject, a.grade), indent=2, ensure_ascii=False))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
