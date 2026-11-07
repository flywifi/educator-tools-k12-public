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
  python3 tools/feeds_update.py --self-test              # offline engine checks (CI runs this)
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


def self_test() -> int:
    """Offline, write-free proof of the engine's promises, reported as OBSERVED values. No network
    (the transport is stubbed), no catalog write (in-memory fixtures), a temp item store."""
    import tempfile
    checks: list[dict] = []

    def ck(name: str, ok: bool, observed) -> None:
        checks.append({"check": name, "ok": bool(ok), "observed": observed})

    # 1. due_feeds: the seed probes stamp bare dates ("2026-06-28"); the runner must not crash on them.
    fixture = {"layers": {"product_updates": {"enabled": False}}, "feeds": [
        {"id": "bare-date", "tier": "canonical", "cadence_days": 7, "state": {"last_checked": "2026-06-28"}},
        {"id": "fresh-iso", "tier": "canonical", "cadence_days": 7, "state": {"last_checked": engine._iso()}},
        {"id": "never", "tier": "news_teacher_student", "cadence_days": 7, "state": {}},
        {"id": "vendor", "tier": "product_updates", "cadence_days": 7, "state": {}}]}
    try:
        due = [f["id"] for f in engine.due_feeds(fixture)]
        ck("a bare-date last_checked does not crash and is due", "bare-date" in due, due)
        ck("a fresh ISO stamp is not due", "fresh-iso" not in due, due)
        ck("a never-checked feed is due", "never" in due, due)
        ck("the off-by-default product_updates layer is skipped", "vendor" not in due, due)
    except TypeError as exc:
        ck("due_feeds survives a bare-date stamp", False, repr(exc))
    # 2. the stdlib parser
    rss = (b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title><item>'
           b'<title>Item One</title><link>https://example.com/1</link><guid>g1</guid>'
           b'<pubDate>Thu, 05 Nov 2026 18:41:56 GMT</pubDate></item></channel></rss>')
    items = engine.parse_feed(rss)
    ck("the stdlib parser yields the item", len(items) == 1 and items[0]["title"] == "Item One",
       [i.get("title") for i in items])
    # 3. first-fetch rule: a promoted feed carries the verifier's ETag; the first fetch must not send it.
    calls: list[dict] = []

    def fake_get(url, etag, last_modified, timeout):
        calls.append({"etag": etag, "last_modified": last_modified})
        return (304, b"", {}) if etag else (200, rss, {"etag": '"e1"'})

    real_get, real_db = engine.sc._conditional_get, engine.DB
    with tempfile.TemporaryDirectory() as td:
        engine.DB = Path(td) / "t.local.db"
        engine.sc._conditional_get = fake_get
        try:
            feed = {"id": "promoted", "url": "https://example.com/rss", "tier": "news_teacher_student",
                    "state": {"etag": '"baseline"', "content_sha256": "x"}}
            r1 = engine.fetch_and_store(feed, offline=False, timeout=1)
            ck("the first fetch ignores the baseline ETag and gets 200",
               calls[0]["etag"] is None and r1["status"] == 200, {**calls[0], "status": r1["status"]})
            ck("the first fetch stores the backlog", r1["new_items"] == 1, r1["new_items"])
            r2 = engine.fetch_and_store(feed, offline=False, timeout=1)
            ck("the next fetch is conditional (304)", calls[1]["etag"] == '"e1"' and r2["status"] == 304,
               {**calls[1], "status": r2["status"]})
        finally:
            engine.sc._conditional_get, engine.DB = real_get, real_db
    failures = [c["check"] for c in checks if not c["ok"]]
    print(json.dumps({"tool": "feeds-update-self-test", "checks": checks, "failures": failures,
                      "human_review_required": True}, indent=2, ensure_ascii=False))
    return 1 if failures else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Feed self-update runner (L7)")
    ap.add_argument("--status", action="store_true", help="show due feeds + the active update mode")
    ap.add_argument("--update", action="store_true", help="fetch due feeds and store new items")
    ap.add_argument("--digest", action="store_true", help="print what's new from the local store")
    ap.add_argument("--offline", action="store_true", help="age-only triage; no network fetch")
    ap.add_argument("--since", help="digest: only items first seen at/after this ISO timestamp")
    ap.add_argument("--category", help="digest: filter by category")
    ap.add_argument("--self-test", action="store_true", help="offline engine checks (no network, no writes)")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()

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
