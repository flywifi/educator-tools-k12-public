#!/usr/bin/env python3
"""Publish the local feed store as a portable, git-shareable snapshot — WRITER side (open net).

The OpenCLAW/crawlkit hand-off model: export the SQLite feed store to JSONL + a fingerprinted
manifest under shared/feeds/snapshot/, commit that pack to git, and an egress-blocked TOS instance
imports it with tools/feeds_import.py — no live network on the reader. Run this where the internet is
open, after `tools/feeds_update.py --update` has harvested fresh items. stdlib-only; deterministic
output (sorted rows) so re-publishing an unchanged store yields an identical pack (no git churn).

Usage:
  python3 tools/feeds_publish.py             # export shared/feeds/snapshot/ (then: git add + commit it)
  python3 tools/feeds_publish.py --stats     # what would be exported
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared" / "feeds"))
import feeds as engine  # noqa: E402

SNAP = ROOT / "shared" / "feeds" / "snapshot"
ITEMS_JSONL = SNAP / "feed_items.jsonl"
MANIFEST = SNAP / "manifest.json"
COLS = ["content_sha256", "feed_id", "guid", "title", "link", "summary",
        "published", "category", "tier", "first_seen"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rows() -> list[dict]:
    if not engine.DB.exists():
        return []
    conn = engine._connect()
    try:
        cur = conn.execute(f"SELECT {', '.join(COLS)} FROM feed_items "
                           "ORDER BY first_seen, content_sha256")
        return [dict(zip(COLS, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def export() -> int:
    rows = _rows()
    SNAP.mkdir(parents=True, exist_ok=True)
    # Deterministic JSONL: sorted keys + stable row order ⇒ identical bytes for an identical store.
    data = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    ITEMS_JSONL.write_text(data, encoding="utf-8")
    sha = hashlib.sha256(data.encode("utf-8")).hexdigest()
    manifest = {
        "name": "feed-items-snapshot", "version": "0.1.0", "generated": _now(),
        "tables": {"feed_items": {"file": "feed_items.jsonl", "rows": len(rows), "sha256": sha}},
        "writer": "tools/feeds_publish.py", "import_with": "tools/feeds_import.py",
        "note": "git-shareable pack (OpenCLAW/crawlkit model); reader imports offline, dedupes by content hash",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "exported", "rows": len(rows),
                      "pack": str(SNAP.relative_to(ROOT)), "sha256": sha,
                      "next": "git add shared/feeds/snapshot && git commit -m 'feeds: publish snapshot'"},
                     indent=2))
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Publish the local feed store as a git-shareable snapshot (L7/L8)")
    ap.add_argument("--stats", action="store_true", help="show what would be exported")
    a = ap.parse_args(argv)
    if a.stats:
        rows = _rows()
        print(json.dumps({"db": str(engine.DB.relative_to(ROOT)), "rows": len(rows),
                          "pack_target": str(SNAP.relative_to(ROOT))}, indent=2))
        return 0
    return export()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
