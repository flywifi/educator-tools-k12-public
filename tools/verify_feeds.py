#!/usr/bin/env python3
"""Portable feed verifier + discoverer — RUN WHERE THE INTERNET IS OPEN.

The TOS build container's egress is locked down, so feed URLs can't be fetched/verified here.
This stdlib-only script does it anywhere the network is open: on a laptop, or pasted into a chatbot
that has a CODE INTERPRETER (which fetches raw XML reliably, unlike a browser tool). For each candidate
it: fetches the URL (following redirects); if that's an HTML page it autodiscovers the RSS/Atom
`<link rel="alternate">`; fetches + parses the feed; and emits a **catalog-ready** entry
(`verified: true`, with a proof item and the etag/last-modified/sha256 baseline) for
`shared/feeds/feeds.json`, plus an `unverified` list with the reason. No third-party deps; nothing
fabricated — a feed that doesn't parse to real items is reported unverified.

Usage:
  python3 tools/verify_feeds.py shared/feeds/feed_candidates.json > verified.json
  python3 tools/verify_feeds.py --url https://www.ed.gov/feed --id ed-gov-news --tier news_teacher_student
Then paste the JSON back to the TOS assistant (or: it drops the "verified" entries into feeds.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (compatible; TOS-feed-verifier/0.1; +k12-education)"
LABEL_KEYS = ("id", "label", "category", "authority", "tier", "purpose",
              "grade_band", "subject", "scope", "cadence_days")
_RSS_LINK = re.compile(
    rb'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+>', re.I)
_HREF = re.compile(rb'href=["\']([^"\']+)["\']', re.I)


def fetch(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, text/xml, text/html;q=0.8, */*;q=0.5"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 - operator-supplied catalog URLs
        return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}, r.geturl()


def autodiscover(html: bytes, base: str) -> list[str]:
    out = []
    for tag in _RSS_LINK.findall(html):
        m = _HREF.search(tag)
        if m:
            out.append(urllib.parse.urljoin(base, m.group(1).decode("utf-8", "replace")))
    return out


def parse_items(raw: bytes):
    try:
        root = ET.fromstring(raw)  # nosec B314 - operator-supplied feed
    except ET.ParseError:
        return None, []
    items = []
    for node in root.iter():
        if node.tag.split("}")[-1] not in ("item", "entry"):
            continue
        rec = {"title": "", "link": "", "date": ""}
        for ch in node:
            ct = ch.tag.split("}")[-1]
            if ct == "title":
                rec["title"] = (ch.text or "").strip()
            elif ct == "link":
                rec["link"] = (ch.get("href") or ch.text or "").strip()
            elif ct in ("pubDate", "published", "updated"):
                rec["date"] = (ch.text or "").strip()
        items.append(rec)
    return root.tag.split("}")[-1], items


def verify_one(cand: dict, timeout: int) -> tuple[dict | None, dict | None]:
    url = cand["url"]
    try:
        status, body, headers, final = fetch(url, timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as e:
        return None, {"id": cand.get("id"), "url": url,
                      "finding": f"fetch failed: {e.__class__.__name__}: {e}"}
    root, items = parse_items(body)
    # If we landed on an HTML page, try to autodiscover the real feed link.
    if root not in ("rss", "feed") and (b"<html" in body[:2000].lower()
                                        or "html" in headers.get("content-type", "")):
        feeds = autodiscover(body, final)
        if not feeds:
            return None, {"id": cand.get("id"), "url": url,
                          "finding": "page has no rss/atom <link rel=alternate>; "
                                     "provide the feed URL directly or check for an iCal/.ics export"}
        url = feeds[0]
        try:
            status, body, headers, final = fetch(url, timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as e:
            return None, {"id": cand.get("id"), "url": url,
                          "finding": f"discovered feed fetch failed: {e.__class__.__name__}: {e}"}
        root, items = parse_items(body)
    if root not in ("rss", "feed") or not items:
        return None, {"id": cand.get("id"), "url": url,
                      "finding": f"not a valid feed (root={root!r}, items={len(items)})"}
    entry = {k: cand.get(k) for k in LABEL_KEYS}
    entry.update({
        "url": final, "type": "feed", "parser": "atom" if root == "feed" else "rss", "verified": True,
        "discover_from": cand.get("discover_from", cand["url"]),
        "proof_latest_item": items[0],
        "state": {"etag": headers.get("etag"), "last_modified": headers.get("last-modified"),
                  "content_sha256": hashlib.sha256(body).hexdigest(),
                  "last_checked": None, "last_status": status}})
    return entry, None


def run(cands: list[dict], timeout: int) -> dict:
    verified, unverified = [], []
    for c in cands:
        ok, bad = verify_one(c, timeout)
        (verified if ok else unverified).append(ok or bad)
    return {"verified": verified, "unverified": unverified,
            "note": "paste this to the TOS assistant; 'verified' entries drop into shared/feeds/feeds.json"}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Portable feed verifier/discoverer (run where net is open)")
    ap.add_argument("candidates", nargs="?", help="path to a candidates JSON (list, or {feeds:[...]})")
    ap.add_argument("--url", help="verify a single feed/page URL")
    ap.add_argument("--id", default="feed")
    ap.add_argument("--tier", default="news_teacher_student")
    ap.add_argument("--authority", default="secondary")
    ap.add_argument("--timeout", type=int, default=20)
    a = ap.parse_args(argv)

    if a.url:
        cands = [{"id": a.id, "url": a.url, "tier": a.tier, "authority": a.authority}]
    elif a.candidates:
        data = json.loads(open(a.candidates, encoding="utf-8").read())
        cands = data.get("feeds", data) if isinstance(data, dict) else data
    else:
        ap.print_help()
        return 2
    print(json.dumps(run(cands, a.timeout), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
