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

_HAVE_FFP = importlib.util.find_spec("fastfeedparser") is not None
_HAVE_FP = importlib.util.find_spec("feedparser") is not None
_HAVE_BS4 = importlib.util.find_spec("bs4") is not None


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


def _entries_to_items(entries) -> list[dict]:
    """Normalize feedparser-style entries (feedparser AND fastfeedparser share this API)."""
    out = []
    for e in entries:
        out.append({
            "guid": getattr(e, "id", "") or getattr(e, "link", ""),
            "title": getattr(e, "title", ""),
            "link": getattr(e, "link", ""),
            "summary": getattr(e, "summary", "") or getattr(e, "description", ""),
            "published": getattr(e, "published", "") or getattr(e, "updated", ""),
        })
    return out


def parse_feed(raw: bytes) -> list[dict]:
    """Return [{guid,title,link,summary,published}] from RSS or Atom bytes.

    Parser preference (all optional; stdlib always works): fastfeedparser (~25x faster, robust) →
    feedparser (gold standard) → stdlib ElementTree. A booster that errors falls through to the next.
    """
    if _HAVE_FFP:
        try:
            import fastfeedparser
            return _entries_to_items(fastfeedparser.parse(raw).entries)
        except Exception:  # malformed-for-FFP: fall through to the next parser, never fake
            pass
    if _HAVE_FP:
        try:
            import feedparser
            return _entries_to_items(feedparser.parse(raw).entries)
        except Exception:
            pass
    items: list[dict] = []
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


def scrape_page_items(feed: dict, html_bytes: bytes) -> list[dict]:
    """Extract news items from an HTML page (for feeds with type='page' + a scrape_config).

    The scrape_config block in feeds.json drives selector behaviour:
      items  — CSS selector for news-item containers (BS4 preferred)
      title  — CSS selectors to try (comma-separated)
      link   — CSS selector for the anchor (falls back to first <a href>)
      date   — CSS selectors to try (reads datetime attr or text)
      summary — CSS selectors to try

    BS4 (beautifulsoup4) is used when installed; otherwise a stdlib html.parser fallback
    extracts headline-bearing <a> tags. Both paths are advisory — scraped items carry
    human_review_required. Selectors are site-specific; tune via scrape_config in feeds.json.
    """
    import urllib.parse as _up
    cfg = feed.get("scrape_config", {})
    base_url = cfg.get("news_list_url") or feed.get("url", "")
    items: list[dict] = []

    if _HAVE_BS4:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_bytes, "html.parser")
        container_sel = cfg.get("items", "article, .news-item, .post-item, li.item, .fs-entry-digest")
        containers = soup.select(container_sel)[:60]
        for c in containers:
            # title — try selectors left to right until one hits
            title = ""
            for ts in (cfg.get("title", "h2, h3, h4, .title, .headline, .fs-entry-summary-header")).split(","):
                el = c.select_one(ts.strip())
                if el:
                    title = el.get_text(separator=" ", strip=True)
                    break
            if not title:
                continue
            # link
            link = ""
            for ls in (cfg.get("link", "a")).split(","):
                el = c.select_one(ls.strip())
                if el and el.get("href"):
                    link = el["href"]
                    break
            if link and not link.startswith("http"):
                link = _up.urljoin(base_url, link)
            # date
            date = ""
            for ds in (cfg.get("date", "time, .date, .published, .news-date, .fs-entry-summary-date")).split(","):
                el = c.select_one(ds.strip())
                if el:
                    date = el.get("datetime") or el.get_text(strip=True)
                    break
            # summary
            summary = ""
            for ss in (cfg.get("summary", "p, .excerpt, .description, .fs-entry-summary-description")).split(","):
                el = c.select_one(ss.strip())
                if el:
                    summary = el.get_text(separator=" ", strip=True)[:500]
                    break
            items.append({"guid": link or title, "title": title, "link": link,
                          "summary": summary, "published": date})
    else:
        # stdlib fallback — pull headline-bearing <a> tags from the page
        from html.parser import HTMLParser

        class _HeadingLinks(HTMLParser):
            def __init__(self):
                super().__init__()
                self.items: list[dict] = []
                self._h = False
                self._htext = ""
                self._href = ""

            def handle_starttag(self, tag, attrs):
                d = dict(attrs)
                if tag in ("h2", "h3", "h4"):
                    self._h = True; self._htext = ""; self._href = ""
                if tag == "a":
                    href = d.get("href", "")
                    if href and not href.startswith("#") and "javascript" not in href:
                        self._href = _up.urljoin(base_url, href)

            def handle_data(self, data):
                if self._h:
                    self._htext += data

            def handle_endtag(self, tag):
                if tag in ("h2", "h3", "h4") and self._htext.strip() and self._href:
                    self.items.append({"guid": self._href, "title": self._htext.strip(),
                                       "link": self._href, "summary": "", "published": ""})
                    self._h = False; self._htext = ""; self._href = ""

        p = _HeadingLinks()
        try:
            p.feed(html_bytes.decode("utf-8", "replace"))
        except Exception:
            pass
        items = p.items[:50]

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
    feed_type = feed.get("type", "feed")
    if feed_type == "page":
        # Scrape HTML → synthetic RSS items; mark source so curator knows they're scraped
        items = scrape_page_items(feed, body)
        result["source"] = "scraped"
        result["scrape_note"] = ("items extracted by page scraper (not a real RSS feed) — "
                                 "tune scrape_config selectors if count is 0 or items look wrong")
    else:
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
