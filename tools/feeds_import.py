#!/usr/bin/env python3
"""Import a published feed snapshot into the LOCAL feed store — READER side (fully offline).

The egress-blocked half of the OpenCLAW/crawlkit hand-off: read shared/feeds/snapshot/ (manifest.json
+ feed_items.jsonl), verify the pack's sha256 fingerprint, and import rows into
shared/feeds/feed_items.local.db with INSERT OR IGNORE (dedupe by content hash — idempotent). The
imported manifest sha256 is recorded so an unchanged snapshot is a no-op (incremental); `--force`
re-imports. No network is ever used. Nothing is fabricated; a corrupt/tampered pack (sha mismatch) is
refused, not imported.

Usage:
  python3 tools/feeds_import.py            # import (skips if the snapshot is unchanged)
  python3 tools/feeds_import.py --status   # snapshot vs last import
  python3 tools/feeds_import.py --force     # re-import even if unchanged
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared" / "feeds"))
import feeds as engine  # noqa: E402

SNAP = ROOT / "shared" / "feeds" / "snapshot"
ITEMS_JSONL = SNAP / "feed_items.jsonl"
MANIFEST = SNAP / "manifest.json"
COLS = ["content_sha256", "feed_id", "guid", "title", "link", "summary",
        "published", "category", "tier", "first_seen"]


def _ensure_meta(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS import_meta (key TEXT PRIMARY KEY, value TEXT)")


def _last_imported(conn) -> str | None:
    _ensure_meta(conn)
    row = conn.execute("SELECT value FROM import_meta WHERE key='last_manifest_sha256'").fetchone()
    return row[0] if row else None


def _load_manifest() -> dict | None:
    if not MANIFEST.exists():
        return None
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def status() -> int:
    m = _load_manifest()
    conn = engine._connect()
    try:
        last = _last_imported(conn)
        rows = conn.execute("SELECT count(*) FROM feed_items").fetchone()[0]
    finally:
        conn.close()
    snap_sha = (m or {}).get("tables", {}).get("feed_items", {}).get("sha256") if m else None
    print(json.dumps({"snapshot_present": bool(m),
                      "snapshot_sha256": snap_sha, "last_imported_sha256": last,
                      "up_to_date": bool(snap_sha and snap_sha == last),
                      "local_rows": rows, "pack": str(SNAP.relative_to(ROOT))}, indent=2))
    return 0


def run_import(force: bool) -> int:
    m = _load_manifest()
    if not m or not ITEMS_JSONL.exists():
        print(json.dumps({"status": "no_snapshot",
                          "detail": f"no pack at {SNAP.relative_to(ROOT)} — run tools/feeds_publish.py "
                                    "on an open-net machine and commit it"}, indent=2))
        return 1
    declared = m.get("tables", {}).get("feed_items", {}).get("sha256")
    data = ITEMS_JSONL.read_text(encoding="utf-8")
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if declared != actual:                       # integrity gate — never import a tampered/corrupt pack
        print(json.dumps({"status": "integrity_error",
                          "detail": "feed_items.jsonl sha256 does not match manifest"}, indent=2))
        return 2
    conn = engine._connect()
    try:
        if not force and _last_imported(conn) == declared:
            print(json.dumps({"status": "up_to_date", "imported": 0,
                              "detail": "snapshot unchanged since last import"}, indent=2))
            return 0
        new = 0
        for line in data.splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            cur = conn.execute(
                f"INSERT OR IGNORE INTO feed_items ({', '.join(COLS)}) "
                f"VALUES ({', '.join('?' for _ in COLS)})",
                tuple(r.get(c) for c in COLS))
            new += cur.rowcount
        _ensure_meta(conn)
        conn.execute("INSERT OR REPLACE INTO import_meta (key, value) VALUES ('last_manifest_sha256', ?)",
                     (declared,))
        conn.commit()
        total = conn.execute("SELECT count(*) FROM feed_items").fetchone()[0]
    finally:
        conn.close()
    print(json.dumps({"status": "imported", "new_rows": new, "local_rows_total": total,
                      "manifest_sha256": declared, "human_review_required": True}, indent=2))
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Import a published feed snapshot (reader side, offline)")
    ap.add_argument("--status", action="store_true", help="snapshot vs last import")
    ap.add_argument("--force", action="store_true", help="re-import even if unchanged")
    a = ap.parse_args(argv)
    if a.status:
        return status()
    return run_import(a.force)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
