#!/usr/bin/env python3
"""make_feed.py — build RSS-style items from any web page that has no native feed.

For education sites that publish news as HTML pages rather than RSS/Atom, this tool fetches
the page, extracts news items via CSS selectors (or a stdlib fallback), and outputs either
JSON (default) or real RSS XML (with --output-rss). The JSON drops straight into
shared/feeds/feed_candidates.json for human review and catalog entry.

stdlib-only core; beautifulsoup4 (web_fetch capability) upgrades selector accuracy; feedgen
(feed_gen capability) enables real RSS XML output. All absent → honest gap, never faked.
Uses the same source_currency polite fetch as the rest of the TOS feed engine.

Usage:
  python3 tools/make_feed.py --url URL [--id ID] [--title TITLE]
  python3 tools/make_feed.py --url URL --output-rss            # emit RSS XML (needs feedgen)
  python3 tools/make_feed.py --config scrape_config.json       # batch from a config file
  python3 tools/make_feed.py --url URL --selector "article" --title-sel "h2" --link-sel "a"

Config file format (JSON):
  {"url": "...", "id": "...", "title": "...", "scrape_config": {
    "items": "article", "title": "h2", "link": "a", "date": "time", "summary": "p"}}
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import urllib.parse as _up
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
try:
    import source_currency as sc
    _HAVE_SC = True
except ImportError:
    _HAVE_SC = False

_HAVE_BS4 = importlib.util.find_spec("bs4") is not None
_HAVE_FG = importlib.util.find_spec("feedgen") is not None

UA = "Mozilla/5.0 (compatible; TOS-make-feed/0.1; +k12-education)"


def _fetch(url: str, timeout: int = 20) -> tuple[int, bytes, dict]:
    """Polite fetch reusing source_currency when available, else stdlib."""
    if _HAVE_SC:
        status, body, headers = sc._conditional_get(url, None, None, timeout)
        return status, body or b"", headers
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html, */*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310
            return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}
    except Exception as e:
        return 0, b"", {"_error": str(e)}


def _scrape(html_bytes: bytes, base_url: str, cfg: dict) -> list[dict]:
    """Extract news items from HTML. BS4 preferred; stdlib html.parser fallback."""
    items: list[dict] = []
    if _HAVE_BS4:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_bytes, "html.parser")
        container_sel = cfg.get("items", "article, .news-item, .post-item, li.item")
        for c in soup.select(container_sel)[:60]:
            title = ""
            for ts in cfg.get("title", "h2, h3, h4, .title, .headline").split(","):
                el = c.select_one(ts.strip())
                if el:
                    title = el.get_text(separator=" ", strip=True)
                    break
            if not title:
                continue
            link = ""
            for ls in cfg.get("link", "a").split(","):
                el = c.select_one(ls.strip())
                if el and el.get("href"):
                    link = el["href"]
                    break
            if link and not link.startswith("http"):
                link = _up.urljoin(base_url, link)
            date = ""
            for ds in cfg.get("date", "time, .date, .published").split(","):
                el = c.select_one(ds.strip())
                if el:
                    date = el.get("datetime") or el.get_text(strip=True)
                    break
            summary = ""
            for ss in cfg.get("summary", "p, .excerpt").split(","):
                el = c.select_one(ss.strip())
                if el:
                    summary = el.get_text(separator=" ", strip=True)[:500]
                    break
            items.append({"guid": link or title, "title": title, "link": link,
                          "summary": summary, "published": date})
    else:
        # stdlib headline-link extractor
        from html.parser import HTMLParser

        class _HL(HTMLParser):
            def __init__(self):
                super().__init__()
                self.items: list[dict] = []
                self._h = False; self._t = ""; self._href = ""

            def handle_starttag(self, tag, attrs):
                d = dict(attrs)
                if tag in ("h2", "h3", "h4"):
                    self._h = True; self._t = ""; self._href = ""
                if tag == "a":
                    href = d.get("href", "")
                    if href and not href.startswith("#") and "javascript" not in href:
                        self._href = _up.urljoin(base_url, href)

            def handle_data(self, data):
                if self._h:
                    self._t += data

            def handle_endtag(self, tag):
                if tag in ("h2", "h3", "h4") and self._t.strip() and self._href:
                    self.items.append({"guid": self._href, "title": self._t.strip(),
                                       "link": self._href, "summary": "", "published": ""})
                    self._h = False; self._t = ""; self._href = ""

        p = _HL()
        try:
            p.feed(html_bytes.decode("utf-8", "replace"))
        except Exception:
            pass
        items = p.items[:50]
    return items


def _to_rss_xml(feed_id: str, feed_title: str, feed_url: str, items: list[dict]) -> str:
    """Emit real RSS 2.0 XML. Requires feedgen; raises ImportError if absent."""
    from feedgen.feed import FeedGenerator  # type: ignore
    fg = FeedGenerator()
    fg.id(feed_url)
    fg.title(feed_title or feed_id)
    fg.link(href=feed_url, rel="alternate")
    fg.description(f"Scraped feed for {feed_url}")
    fg.language("en")
    for it in items:
        fe = fg.add_entry()
        fe.id(it.get("guid") or it.get("link") or "")
        fe.title(it.get("title") or "(no title)")
        if it.get("link"):
            fe.link(href=it["link"])
        if it.get("summary"):
            fe.description(it["summary"])
        if it.get("published"):
            fe.pubDate(it["published"])
    return fg.rss_str(pretty=True).decode("utf-8")


def run(url: str, feed_id: str, feed_title: str, cfg: dict,
        output_rss: bool, timeout: int) -> int:
    status, body, headers = _fetch(url, timeout)
    if status == 0 or not body:
        err = headers.get("_error", f"HTTP {status}")
        print(json.dumps({"status": "error", "url": url, "detail": err}, indent=2))
        return 1
    items = _scrape(body, url, cfg)
    if output_rss:
        if not _HAVE_FG:
            print(json.dumps({"status": "error",
                              "detail": "feedgen not installed — pip install feedgen",
                              "items_found": len(items)}, indent=2))
            return 2
        print(_to_rss_xml(feed_id, feed_title, url, items))
        return 0
    result = {
        "url": url, "id": feed_id, "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "http_status": status, "items_found": len(items), "items": items,
        "scrape_config_used": cfg,
        "note": ("human_review_required — scraped items, not a real RSS feed. "
                 "Tune scrape_config selectors if count is 0 or items look wrong. "
                 "Add verified items to shared/feeds/feeds.json after review."),
        "capabilities": {"bs4": _HAVE_BS4, "feedgen": _HAVE_FG,
                         "note": "install beautifulsoup4 for selector-based extraction; "
                                 "install feedgen to emit real RSS XML (--output-rss)"},
        "human_review_required": True,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(
        description="Build RSS-style items from any web page (for sites without a native feed)")
    ap.add_argument("--url", help="URL of the news-listing page to scrape")
    ap.add_argument("--id", default="scraped-feed", dest="feed_id", help="feed ID for the output")
    ap.add_argument("--title", default="", dest="feed_title", help="feed title for RSS output")
    ap.add_argument("--config", help="path to a JSON config file with url + scrape_config")
    ap.add_argument("--selector", default="", dest="items_sel",
                    help="CSS selector for news-item containers (overrides config)")
    ap.add_argument("--title-sel", default="", help="CSS selector for item titles")
    ap.add_argument("--link-sel", default="", help="CSS selector for item links")
    ap.add_argument("--date-sel", default="", help="CSS selector for item dates")
    ap.add_argument("--summary-sel", default="", help="CSS selector for item summaries")
    ap.add_argument("--output-rss", action="store_true",
                    help="emit real RSS 2.0 XML instead of JSON (requires feedgen)")
    ap.add_argument("--timeout", type=int, default=20)
    a = ap.parse_args(argv)

    cfg: dict = {}
    url = a.url or ""
    feed_id = a.feed_id
    feed_title = a.feed_title

    if a.config:
        raw = json.loads(Path(a.config).read_text(encoding="utf-8"))
        url = raw.get("url", url)
        feed_id = raw.get("id", feed_id)
        feed_title = raw.get("title", feed_title)
        cfg = raw.get("scrape_config", {})

    # CLI overrides
    if a.items_sel:
        cfg["items"] = a.items_sel
    if a.title_sel:
        cfg["title"] = a.title_sel
    if a.link_sel:
        cfg["link"] = a.link_sel
    if a.date_sel:
        cfg["date"] = a.date_sel
    if a.summary_sel:
        cfg["summary"] = a.summary_sel

    if not url:
        ap.print_help()
        return 2

    return run(url, feed_id, feed_title, cfg, a.output_rss, a.timeout)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
