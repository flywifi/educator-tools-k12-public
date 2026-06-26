#!/usr/bin/env python3
"""Feed self-update engine (L7) — local, low-token "what changed" from a catalog of trusted feeds.

Keeps a small **catalog** of authoritative education feeds (`feeds.json`) and a **local store** of the
items harvested from them (`feed_items.local.db`, gitignored). On an update it visits each *due* feed
with a polite conditional GET (HTTP 304 ⇒ skip — cheap), parses new items, dedupes by content hash, and
files only the genuinely-new ones locally. A teacher then gets a "what's new" digest at **zero model
token cost** — the heavy lifting is plain Python; the model only ever sees the short result.

stdlib-first: parses with `feedparser` when present, else stdlib ElementTree. Network fetch + conditional
GET are reused from `tools/source_currency.py` (`_conditional_get` / `_content_hash`), which already
handles `requests`-or-`urllib`. Offline ⇒ age-only triage, never a guess. Change *interpretation* stays
advisory (a `canonical`/`primary` feed signalling a standards change routes to "verify on the primary
source", never an auto-edit). `human_review_required: true` on every digest. Nothing fabricated.

Engine API (the CLI lives in tools/feeds_update.py):
  load_catalog() · save_catalog() · due_feeds() · parse_feed(raw) · fetch_and_store(feed) ·
  update(catalog) · digest(since) · new_count()
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CATALOG = HERE / "feeds.json"
DB = HERE / "feed_items.local.db"

# Reuse the F2 currency engine's polite fetch (requests-or-urllib, conditional GET) + hashing.
sys.path.insert(0, str(ROOT / "tools"))
import source_currency as sc  # noqa: E402

_HAVE_FP = importlib.util.find_spec("feedparser") is not None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# --------------------------------------------------------------------------- catalog
def load_catalog() -> dict:
    if not CATALOG.exists():
        return {"domain": "education-feeds", "version": "0.0.0", "feeds": []}
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def save_catalog(catalog: dict) -> None:
    catalog["updated"] = _iso()
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


def _layer_enabled(catalog: dict, feed: dict) -> bool:
    """The off-by-default product_updates layer is skipped unless the teacher enabled it."""
    if feed.get("tier") == "product_updates":
        return bool(catalog.get("layers", {}).get("product_updates", {}).get("enabled"))
    return True


def due_feeds(catalog: dict, now: datetime | None = None) -> list[dict]:
    now = now or _now()
    due = []
    for f in catalog.get("feeds", []):
        if not _layer_enabled(catalog, f):
            continue
        last = _parse_dt((f.get("state") or {}).get("last_checked"))
        cadence = int(f.get("cadence_days", 7))
        if last is None or (now - last) > timedelta(days=cadence):
            due.append(f)
    return due


# --------------------------------------------------------------------------- parsing
def _tag(el) -> str:
    return el.tag.split("}")[-1]


def parse_feed(raw: bytes) -> list[dict]:
    """Return [{guid,title,link,summary,published}] from RSS or Atom bytes. feedparser if present."""
    items: list[dict] = []
    if _HAVE_FP:
        import feedparser
        for e in feedparser.parse(raw).entries:
            items.append({
                "guid": getattr(e, "id", "") or getattr(e, "link", ""),
                "title": getattr(e, "title", ""),
                "link": getattr(e, "link", ""),
                "summary": getattr(e, "summary", ""),
                "published": getattr(e, "published", "") or getattr(e, "updated", ""),
            })
        return items
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(raw)  # nosec B314 - catalog URLs are operator-controlled
    except ET.ParseError:
        return items
    for node in root.iter():
        if _tag(node) not in ("item", "entry"):
            continue
        rec = {"guid": "", "title": "", "link": "", "summary": "", "published": ""}
        for ch in node:
            ct = _tag(ch)
            if ct == "title":
                rec["title"] = (ch.text or "").strip()
            elif ct == "link":
                rec["link"] = (ch.get("href") or ch.text or "").strip()
            elif ct in ("summary", "description"):
                rec["summary"] = (ch.text or "").strip()
            elif ct in ("guid", "id"):
                rec["guid"] = (ch.text or "").strip()
            elif ct in ("pubDate", "published", "updated"):
                rec["published"] = (ch.text or "").strip()
        rec["guid"] = rec["guid"] or rec["link"]
        items.append(rec)
    return items


def _item_hash(feed_id: str, item: dict) -> str:
    key = f"{feed_id}|{item.get('guid') or item.get('link')}|{item.get('title')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- local store
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS feed_items ("
        "content_sha256 TEXT PRIMARY KEY, feed_id TEXT, guid TEXT, title TEXT, link TEXT, "
        "summary TEXT, published TEXT, category TEXT, tier TEXT, first_seen TEXT)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_first_seen ON feed_items(first_seen)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_feed ON feed_items(feed_id)")
    return conn


def store_items(feed: dict, items: list[dict]) -> int:
    """Insert only NEW items (dedupe by content hash). Returns the count of genuinely-new rows."""
    conn = _connect()
    new = 0
    seen = _iso()
    try:
        for it in items:
            h = _item_hash(feed["id"], it)
            cur = conn.execute(
                "INSERT OR IGNORE INTO feed_items "
                "(content_sha256, feed_id, guid, title, link, summary, published, category, tier, first_seen) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (h, feed["id"], it.get("guid", ""), it.get("title", ""), it.get("link", ""),
                 it.get("summary", "")[:1000], it.get("published", ""),
                 feed.get("category", ""), feed.get("tier", ""), seen),
            )
            new += cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return new


# --------------------------------------------------------------------------- fetch + update
def fetch_and_store(feed: dict, offline: bool, timeout: int) -> dict:
    """Conditional GET a single feed, parse + store new items, update its state. Honest on every path."""
    st = feed.setdefault("state", {})
    result = {"id": feed["id"], "tier": feed.get("tier"), "authority": feed.get("authority"),
              "state": None, "new_items": 0, "status": None}
    if offline:
        result["state"] = "uncertain"
        result["reason"] = "offline — no fetch; existing local items unchanged"
        return result
    status, body, headers = sc._conditional_get(feed["url"], st.get("etag"),
                                                 st.get("last_modified"), timeout)
    result["status"] = status
    st["last_checked"] = _iso()
    st["last_status"] = status
    if status == 304:
        result["state"] = "current"
        return result
    if status in (404, 410):
        result["state"] = "removed_404"
        result["reason"] = f"HTTP {status} — feed gone; flag for the curator (L8)"
        return result
    if status == 0 or not body:
        result["state"] = "unreachable"
        result["reason"] = "transport error / empty body — could not verify"
        return result
    digest_sha = sc._content_hash(body)
    items = parse_feed(body)
    if not items and digest_sha != st.get("content_sha256"):
        result["state"] = "uncertain"
        result["reason"] = "fetched but no items parsed — possible format change; flag for the curator"
    new = store_items(feed, items)
    st["etag"] = headers.get("etag") or st.get("etag")
    st["last_modified"] = headers.get("last-modified") or st.get("last_modified")
    st["content_sha256"] = digest_sha
    result["new_items"] = new
    result["state"] = "changed" if new else "current"
    return result


def update(catalog: dict, offline: bool = False, timeout: int = 15,
           write_state: bool = True) -> dict:
    due = due_feeds(catalog)
    reports = [fetch_and_store(f, offline, timeout) for f in due]
    if write_state and not offline:
        save_catalog(catalog)
    advisory = [r for r in reports
                if r["state"] in ("removed_404", "uncertain")
                or (r["state"] == "changed" and r.get("authority") == "primary")]
    return {"tool": "feeds-update", "generated_at": _iso(), "offline": offline,
            "due": len(due), "new_total": sum(r["new_items"] for r in reports),
            "reports": reports,
            "advisory": [{"id": r["id"], "state": r["state"],
                          "note": "verify on the primary source / route to the feed-curator (L8)"}
                         for r in advisory],
            "human_review_required": True}


# --------------------------------------------------------------------------- digest / query
def new_count() -> int:
    if not DB.exists():
        return 0
    conn = _connect()
    try:
        return conn.execute("SELECT count(*) FROM feed_items").fetchone()[0]
    finally:
        conn.close()


def digest(since: str | None = None, category: str | None = None, limit: int = 50) -> dict:
    if not DB.exists():
        return {"since": since, "count": 0, "items": [],
                "note": "no local store yet — run feeds_update.py --update"}
    conn = _connect()
    try:
        where, params = [], []
        if since:
            where.append("first_seen >= ?"); params.append(since)
        if category:
            where.append("category = ?"); params.append(category)
        sql = ("SELECT feed_id, title, link, published, category, tier, first_seen FROM feed_items")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY first_seen DESC, feed_id LIMIT ?"
        params.append(limit)
        cols = ["feed_id", "title", "link", "published", "category", "tier", "first_seen"]
        rows = [dict(zip(cols, r)) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()
    return {"since": since, "category": category, "count": len(rows), "items": rows,
            "human_review_required": True}
