#!/usr/bin/env python3
"""Feed self-update runner (L7) — the CLI over shared/feeds. Polite, offline-graceful, low-token.

Visits each *due* feed in shared/feeds/feeds.json with a conditional GET (HTTP 304 ⇒ skip), files only
genuinely-new items into the gitignored local store, and prints a "what's new" digest the model can read
for almost nothing. The trigger cadence is driven by the teacher's L0 `feed_update_mode` preference
(default derived from their offline_tier; separately overridable) — this runner just reports the mode and
honors --update when invoked, so a `manual`, `on_session_start` hook, or `scheduled` job all call the
same command.

Usage:
  python3 tools/feeds_update.py --status                 # which feeds are due + the active update mode
  python3 tools/feeds_update.py --update [--offline]     # fetch due feeds, store new items (advisory)
  python3 tools/feeds_update.py --digest [--since ISO] [--category news]   # what's new, JSON/human
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared" / "feeds"))
import feeds as engine  # noqa: E402

PROFILE = ROOT / "shared" / "context" / "profiles" / "teacher.local.json"


def feed_update_mode() -> str:
    """Read the L0 preference; fall back to 'manual' when no profile/preference exists."""
    if not PROFILE.exists():
        return "manual"
    try:
        prof = json.loads(PROFILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "manual"
    return (prof.get("local_first") or {}).get("feed_update_mode", "manual")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Feed self-update runner (L7)")
    ap.add_argument("--status", action="store_true", help="show due feeds + the active update mode")
    ap.add_argument("--update", action="store_true", help="fetch due feeds and store new items")
    ap.add_argument("--digest", action="store_true", help="print what's new from the local store")
    ap.add_argument("--offline", action="store_true", help="age-only triage; no network fetch")
    ap.add_argument("--since", help="digest: only items first seen at/after this ISO timestamp")
    ap.add_argument("--category", help="digest: filter by category")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args(argv)

    catalog = engine.load_catalog()

    if a.status:
        due = engine.due_feeds(catalog)
        print(json.dumps({
            "update_mode": feed_update_mode(),
            "catalog_version": catalog.get("version"),
            "feeds_total": len(catalog.get("feeds", [])),
            "due": [{"id": f["id"], "tier": f.get("tier"), "authority": f.get("authority"),
                     "cadence_days": f.get("cadence_days"), "verified": f.get("verified", False)}
                    for f in due],
            "stored_items": engine.new_count(),
            "human_review_required": True,
        }, indent=2))
        return 0

    if a.update:
        print(json.dumps(engine.update(catalog, offline=a.offline, timeout=a.timeout),
                         indent=2, ensure_ascii=False))
        return 0

    if a.digest:
        print(json.dumps(engine.digest(since=a.since, category=a.category, limit=a.limit),
                         indent=2, ensure_ascii=False))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
