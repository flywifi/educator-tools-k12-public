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
  python3 tools/feeds_publish.py --self-test # offline proof of the redistribution switch
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
        cur = conn.execute(f"SELECT {', '.join(COLS)} FROM feed_items "  # nosec B608 - COLS is a hardcoded constant column list, never user input
                           "ORDER BY first_seen, content_sha256")
        return [dict(zip(COLS, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def _policy() -> dict:
    """The catalog's redistribution switch and the feeds it covers. A feed marked `redistribute:
    false` (its publisher's terms allow linking, not republishing) is withheld from the snapshot
    only while `redistribution.enforced` is true; with it off, the export says what it WOULD withhold."""
    try:
        catalog = engine.load_catalog()
    except (OSError, ValueError):
        catalog = {}
    marked = sorted(f["id"] for f in catalog.get("feeds", []) if f.get("redistribute") is False)
    enforced = bool((catalog.get("redistribution") or {}).get("enforced", False))
    return {"enforced": enforced, "marked": marked}


def _split(rows: list[dict], policy: dict) -> tuple[list[dict], dict]:
    marked = set(policy["marked"])
    counts: dict = {}
    for r in rows:
        if r["feed_id"] in marked:
            counts[r["feed_id"]] = counts.get(r["feed_id"], 0) + 1
    if not policy["enforced"]:
        return rows, counts
    return [r for r in rows if r["feed_id"] not in marked], counts


def export() -> int:
    policy = _policy()
    rows, marked_rows = _split(_rows(), policy)
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
        "redistribution": {"enforced": policy["enforced"],
                           ("withheld" if policy["enforced"] else "not_withheld"): marked_rows},
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    out = {"status": "exported", "rows": len(rows), "pack": str(SNAP.relative_to(ROOT)), "sha256": sha,
           "next": "git add shared/feeds/snapshot && git commit -m 'feeds: publish snapshot'"}
    if marked_rows and not policy["enforced"]:
        out["warning"] = (f"redistribution is not enforced: rows from {sorted(marked_rows)} (redistribute:false) "
                          "ARE in this pack. Review before committing it; set redistribution.enforced in "
                          "shared/feeds/feeds.json to withhold them.")
    print(json.dumps(out, indent=2))
    return 0


def self_test() -> int:
    """Offline proof of the redistribution switch, both positions, on in-memory rows (no store, no pack)."""
    rows = [{"feed_id": "open-feed"}, {"feed_id": "link-only"}, {"feed_id": "link-only"}]
    checks = []
    off, off_counts = _split(rows, {"enforced": False, "marked": ["link-only"]})
    checks.append(("off: every row exported", len(off) == 3, len(off)))
    checks.append(("off: marked rows still counted", off_counts == {"link-only": 2}, off_counts))
    on, on_counts = _split(rows, {"enforced": True, "marked": ["link-only"]})
    checks.append(("on: marked feed withheld", [r["feed_id"] for r in on] == ["open-feed"], len(on)))
    checks.append(("on: withheld rows counted", on_counts == {"link-only": 2}, on_counts))
    none, _ = _split(rows, {"enforced": True, "marked": []})
    checks.append(("on, nothing marked: every row exported", len(none) == 3, len(none)))
    live = _policy()
    checks.append(("the live catalog's policy reads", isinstance(live["enforced"], bool), live))
    failures = [c[0] for c in checks if not c[1]]
    print(json.dumps({"tool": "feeds-publish-self-test",
                      "checks": [{"check": n, "ok": ok, "observed": o} for n, ok, o in checks],
                      "failures": failures}, indent=2))
    return 1 if failures else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Publish the local feed store as a git-shareable snapshot (L7/L8)")
    ap.add_argument("--stats", action="store_true", help="show what would be exported")
    ap.add_argument("--self-test", action="store_true", help="offline proof of the redistribution switch")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.stats:
        policy = _policy()
        rows, marked_rows = _split(_rows(), policy)
        print(json.dumps({"db": str(engine.DB.relative_to(ROOT)), "rows": len(rows),
                          "pack_target": str(SNAP.relative_to(ROOT)),
                          "redistribution": {"enforced": policy["enforced"], "marked": policy["marked"],
                                             "marked_rows": marked_rows}}, indent=2))
        return 0
    return export()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
