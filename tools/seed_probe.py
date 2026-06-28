#!/usr/bin/env python3
"""seed_probe.py — offline-runnable seed/feed prober. Run on YOUR machine (open network); it
actually fetches every feed + source-currency seed in the repo, reports what is live / dead /
redirected, auto-discovers real RSS/Atom feed URLs for the unverified ones, and packages a report
for Claude to act on. PURE STDLIB — no pip, no venv, no dependency hell. Never fabricates: it only
reports HTTP results it really got.

WHAT IT TOUCHES
  - shared/feeds/feeds.json                      (the RSS/page feed catalog)
  - canonical-sources/registries/*.json          (source-currency seeds with a "sources" list)

WHAT IT DOES
  review   list every seed/feed with its URL + current verified/status            (default, offline)
  probe    GET each URL (browser UA, polite), record status/redirect/content-type, detect real feeds,
           and AUTO-DISCOVER <link rel=alternate ...rss/atom> feed URLs on page-type entries  (network)
  report   write seed_report_<ts>.json + .md  (+ zip)  -> upload to Claude
  apply    OPTIONAL: write back confirmations — set verified=true for entries whose URL returned a
           real feed; record discovered feed candidates; stamp last_checked/last_status/sha256.
           Conservative: never overwrites a URL, never sets verified on a guess.

USAGE
  python tools/seed_probe.py                     # review only (offline, no network)
  python tools/seed_probe.py --probe             # fetch everything + write the report (network)
  python tools/seed_probe.py --probe --apply     # also write confirmed verifications + candidates back
  python tools/seed_probe.py --probe --only feeds # probe only feeds (or: --only registries)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.request
import zlib
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def find_root(start: Path) -> Path:
    for base in (Path(start).resolve().parent, Path.cwd()):
        p = base
        for _ in range(6):
            if (p / "tools" / "sync_check.py").exists():
                return p
            if p.parent == p:
                break
            p = p.parent
    return Path(start).resolve().parent.parent


ROOT = find_root(__file__)
FEEDS = ROOT / "shared" / "feeds" / "feeds.json"
REGISTRIES = ROOT / "canonical-sources" / "registries"


class _FeedLinkFinder(HTMLParser):
    """Collect <link rel="alternate" type="application/(rss|atom)+xml" href="..."> from HTML."""
    def __init__(self):
        super().__init__()
        self.feeds: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        typ = a.get("type", "").lower()
        rel = a.get("rel", "").lower()
        if a.get("href") and ("rss" in typ or "atom" in typ or ("alternate" in rel and "xml" in typ)):
            self.feeds.append(a["href"])


def _abs(base: str, href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    m = re.match(r"(https?://[^/]+)", base)
    root = m.group(1) if m else base
    return root + (href if href.startswith("/") else "/" + href)


def _decode_body(resp, raw: bytes) -> bytes:
    """Transparently decompress gzip/deflate so compressed pages aren't read as garbage."""
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in enc:
            return gzip.decompress(raw)
        if "deflate" in enc:
            try:
                return zlib.decompress(raw)
            except zlib.error:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        return raw
    return raw


def probe(url: str, timeout: float = 25.0, retries: int = 2, delay: float = 1.0) -> dict:
    """Actually fetch a URL on YOUR machine (no TOS/sandbox egress limits). Returns only real,
    observed facts — never guesses. Follows redirects, decompresses gzip/deflate, retries transient
    failures, and reads the full body (large cap) so nothing is truncated."""
    out = {"url": url, "ok": False, "status": None, "final_url": url,
           "content_type": None, "bytes": 0, "is_feed": False,
           "discovered_feeds": [], "supersession": [], "error": None, "sha256": None}
    last_err = None
    for attempt in range(retries + 1):
        if delay:
            time.sleep(delay)
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip, deflate"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read(15_000_000)  # 15MB — effectively no truncation for these pages
                data = _decode_body(resp, raw)
                out["status"] = resp.status
                out["final_url"] = resp.geturl()
                out["content_type"] = resp.headers.get("Content-Type", "")
                out["bytes"] = len(data)
                out["ok"] = 200 <= resp.status < 300
                out["sha256"] = hashlib.sha256(data).hexdigest()
            text = data.decode("utf-8", errors="replace")
            head = text[:8000].lower()
            out["is_feed"] = ("<rss" in head or "<feed" in head or "<rdf" in head
                              or "application/rss" in (out["content_type"] or "")
                              or "application/atom" in (out["content_type"] or ""))
            if not out["is_feed"] and "<html" in head:  # autodiscover real feeds on a page
                f = _FeedLinkFinder()
                try:
                    f.feed(text)
                except Exception:
                    pass
                out["discovered_feeds"] = sorted({_abs(out["final_url"], h) for h in f.feeds})[:20]
            for kw in ("rescinded", "repealed", "archived", "superseded", "discontinued",
                       "program eliminated", "page not found", "retired"):
                if kw in text.lower():
                    out["supersession"].append(kw)
            return out  # success
        except urllib.error.HTTPError as e:
            out["status"] = e.code
            out["error"] = f"HTTP {e.code}"
            if e.code in (404, 410, 401, 403):
                return out  # definitive — don't retry
            last_err = out["error"]
        except Exception as e:
            last_err = f"{e.__class__.__name__}: {str(e)[:120]}"
            out["error"] = last_err
        # transient — back off and retry
        time.sleep(1.5 * (attempt + 1))
    out["error"] = last_err
    return out


def load_seeds(only: str | None) -> list[dict]:
    """Collect every probeable seed: feeds + source-currency registry sources."""
    seeds = []
    if only in (None, "feeds") and FEEDS.exists():
        d = json.loads(FEEDS.read_text(encoding="utf-8"))
        for f in d.get("feeds", []):
            seeds.append({"kind": "feed", "file": "shared/feeds/feeds.json", "id": f.get("id"),
                          "url": f.get("url"), "type": f.get("type"), "verified": f.get("verified"),
                          "url_status": f.get("url_status")})
    if only in (None, "registries") and REGISTRIES.exists():
        for rf in sorted(REGISTRIES.glob("*.json")):
            try:
                d = json.loads(rf.read_text(encoding="utf-8"))
            except Exception:
                continue
            for s in d.get("sources", []):
                seeds.append({"kind": "registry", "file": f"canonical-sources/registries/{rf.name}",
                              "id": s.get("id"), "url": s.get("url"), "type": s.get("type"),
                              "authority": s.get("authority")})
    return [s for s in seeds if s.get("url")]


def classify(p: dict) -> str:
    if p["error"] or (p["status"] and p["status"] >= 400):
        return "DEAD"
    if p["final_url"].rstrip("/") != p["url"].rstrip("/"):
        return "REDIRECT"
    if p["is_feed"]:
        return "LIVE_FEED"
    if p["discovered_feeds"]:
        return "PAGE+FEED_FOUND"
    if p["ok"]:
        return "LIVE_PAGE"
    return "UNKNOWN"


def apply_back(results: list[dict]) -> list[str]:
    """Conservative write-back: confirm verified for entries whose own URL is a real feed; attach
    discovered-feed candidates; stamp last_checked/last_status. Never overwrites a URL or guesses."""
    notes = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if FEEDS.exists():
        d = json.loads(FEEDS.read_text(encoding="utf-8"))
        by_id = {r["seed"]["id"]: r for r in results if r["seed"]["kind"] == "feed"}
        for f in d.get("feeds", []):
            r = by_id.get(f.get("id"))
            if not r:
                continue
            p, cls = r["probe"], r["class"]
            f.setdefault("state", {})
            f["state"].update({"last_checked": now, "last_status": p["status"],
                               "content_sha256": p["sha256"]})
            if cls == "LIVE_FEED":
                f["verified"] = True
                f["url_status"] = "confirmed_live_feed"
                notes.append(f"verified {f['id']} (live feed)")
            elif cls == "DEAD":
                f["url_status"] = "dead_link"
                notes.append(f"flagged {f['id']} DEAD ({p.get('error') or p['status']})")
            if p["discovered_feeds"]:
                f["discovered_feed_candidates"] = p["discovered_feeds"]
                notes.append(f"{f['id']}: found {len(p['discovered_feeds'])} candidate feed(s)")
        FEEDS.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true", help="fetch every seed (needs network)")
    ap.add_argument("--apply", action="store_true", help="write confirmations/candidates back (with --probe)")
    ap.add_argument("--only", choices=["feeds", "registries"], help="limit to one kind")
    ap.add_argument("--delay", type=float, default=1.0, help="polite delay between fetches (s); 0 = fastest")
    args = ap.parse_args(argv)

    seeds = load_seeds(args.only)
    print(f"seed_probe — repo {ROOT}")
    print(f"{len(seeds)} seed(s): "
          f"{sum(s['kind']=='feed' for s in seeds)} feeds, {sum(s['kind']=='registry' for s in seeds)} registry sources\n")

    if not args.probe:
        for s in seeds:
            print(f"  [{s['kind']:8}] {s['id']:30} verified={s.get('verified')}  {s['url']}")
        print("\nRun with --probe to fetch them all and produce a report for Claude.")
        return 0

    results = []
    counts: dict[str, int] = {}
    for s in seeds:
        p = probe(s["url"], delay=args.delay)
        cls = classify(p)
        counts[cls] = counts.get(cls, 0) + 1
        results.append({"seed": s, "probe": p, "class": cls})
        extra = ""
        if p["discovered_feeds"]:
            extra = "  -> FEED: " + p["discovered_feeds"][0]
        if p["error"]:
            extra = "  " + p["error"]
        print(f"  {cls:16} {s['id']:30} {p['status'] or '---'}{extra}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    rj = ROOT / f"seed_report_{stamp}.json"
    rm = ROOT / f"seed_report_{stamp}.md"
    rj.write_text(json.dumps({"generated": stamp, "summary": counts, "results": results},
                             indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# Seed probe report {stamp}", "", "## Summary", ""]
    md += [f"- {k}: {v}" for k, v in sorted(counts.items())]
    md += ["", "## Details", "", "| class | id | status | url / discovered feed |", "|---|---|---|---|"]
    for r in results:
        s, p = r["seed"], r["probe"]
        disc = p["discovered_feeds"][0] if p["discovered_feeds"] else (p["final_url"] if p["final_url"] != s["url"] else s["url"])
        md.append(f"| {r['class']} | {s['id']} | {p['status'] or p.get('error','')} | {disc} |")
    rm.write_text("\n".join(md) + "\n", encoding="utf-8")

    zip_path = ROOT / f"seed_report_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(rj, rj.name)
        z.write(rm, rm.name)

    print("\nsummary:", counts)
    if args.apply:
        for n in apply_back(results):
            print("  applied:", n)
    print(f"\nReport: {rm.name} / {rj.name}")
    print(f"Upload to Claude:  {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
