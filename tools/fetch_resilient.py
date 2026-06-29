#!/usr/bin/env python3
"""fetch_resilient.py — maintainer-grade resilient fetch for PUBLIC data, with the multi-prong
fallback chain TOS keeps gated from its conservative public crawler.

WHY: the public TOS crawler is deliberately minimal (one honest UA, robots-respecting, no browser
render) so it never looks aggressive. As the system maintainer pulling PUBLIC government/education
data (FL standards, school lists, district pages) for a non-commercial teacher tool, you should have
the fuller toolkit. Many sites (e.g. fldoe.org) return 403 to a bare urllib request simply because it
doesn't look like a browser; a complete, honest browser-header set — or a real archived snapshot —
gets the same PUBLIC page a human browser would.

ETHICS (what this does and does NOT do):
  - DOES: send a complete, realistic browser header set; reuse a requests.Session; optionally drive a
    REAL headless browser (Playwright); fall back to the Wayback Machine (public archive of the page).
  - DOES NOT: solve CAPTCHAs, spoof TLS fingerprints, rotate proxies, or defeat authentication / paywalls.
  - Robots.txt is respected by default. --ignore-robots is a maintainer override you are responsible for
    (use only for public data you are authorized to access). Polite delays throughout.

PRONGS (first success wins; --all tries every one):
  1. browser_headers   stdlib urllib + full browser headers + gzip/deflate decode   (no deps)
  2. requests_session  requests.Session w/ browser headers (better TLS/redirects)   (needs requests)
  3. playwright        real headless Chromium — runs JS, defeats most bot walls      (needs playwright)
  4. wayback           closest Internet Archive snapshot of the URL (archive.org)     (no deps)

USAGE
  python tools/fetch_resilient.py <url>                 # try prongs in order, print result
  python tools/fetch_resilient.py <url> --all           # run every prong (compare)
  python tools/fetch_resilient.py <url> --out page.html # save recovered content
  python tools/fetch_resilient.py <url> --ignore-robots # maintainer override (public data only)

Importable: resilient_get(url) -> dict {ok,status,prong,final_url,content,note}.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from pathlib import Path

BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,image/apng,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",   # NOT br — stdlib can't decode brotli
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}


def _robots_ok(url: str, ignore: bool) -> bool:
    if ignore:
        return True
    try:
        m = urllib.parse.urlparse(url)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{m.scheme}://{m.netloc}/robots.txt")
        rp.read()
        return rp.can_fetch(BROWSER_HEADERS["User-Agent"], url)
    except Exception:
        return True  # no robots / unreadable -> allowed


def _decompress(resp, raw: bytes) -> bytes:
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


# --- prong 1: stdlib urllib + full browser headers ---------------------------
def prong_browser_headers(url: str, timeout: float = 25.0) -> dict:
    try:
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = _decompress(resp, resp.read(15_000_000))
            return {"ok": 200 <= resp.status < 300, "status": resp.status,
                    "final_url": resp.geturl(), "content": raw,
                    "note": "full browser headers"}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "final_url": url, "content": b"", "note": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "status": None, "final_url": url, "content": b"", "note": f"{e.__class__.__name__}"}


# --- prong 2: requests.Session -----------------------------------------------
def prong_requests_session(url: str, timeout: float = 25.0) -> dict:
    try:
        import requests
    except Exception:
        return {"ok": False, "status": None, "final_url": url, "content": b"",
                "note": "requests not installed (skip)"}
    try:
        s = requests.Session()
        s.headers.update(BROWSER_HEADERS)
        r = s.get(url, timeout=timeout)
        return {"ok": r.ok, "status": r.status_code, "final_url": r.url,
                "content": r.content, "note": "requests.Session"}
    except Exception as e:
        return {"ok": False, "status": None, "final_url": url, "content": b"", "note": f"{e.__class__.__name__}"}


# --- prong 3: real headless browser (Playwright) -----------------------------
def prong_playwright(url: str, timeout: float = 45.0) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {"ok": False, "status": None, "final_url": url, "content": b"",
                "note": "playwright not installed — enable: pip install playwright && playwright install chromium"}
    try:
        with sync_playwright() as p:
            kw = {}
            # honor a pre-installed Chromium if present (e.g. /opt/pw-browsers)
            for cand in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome",):
                if Path(cand).exists():
                    kw["executable_path"] = cand
            browser = p.chromium.launch(headless=True, **kw)
            page = browser.new_page(user_agent=BROWSER_HEADERS["User-Agent"])
            resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            page.wait_for_timeout(2500)
            html = page.content()
            status = resp.status if resp else None
            final = page.url
            browser.close()
            return {"ok": bool(status and 200 <= status < 400), "status": status,
                    "final_url": final, "content": html.encode("utf-8"), "note": "headless Chromium (JS rendered)"}
    except Exception as e:
        return {"ok": False, "status": None, "final_url": url, "content": b"", "note": f"playwright: {e.__class__.__name__}"}


# --- prong 4: Wayback Machine (public archive — gets pages that block direct) -
def prong_wayback(url: str, timeout: float = 25.0) -> dict:
    try:
        api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
        req = urllib.request.Request(api, headers={"User-Agent": BROWSER_HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            meta = json.loads(resp.read().decode("utf-8", "replace"))
        snap = meta.get("archived_snapshots", {}).get("closest", {})
        if not snap.get("available"):
            return {"ok": False, "status": None, "final_url": url, "content": b"",
                    "note": "no Wayback snapshot found"}
        snap_url = snap["url"]
        req2 = urllib.request.Request(snap_url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req2, timeout=timeout) as resp2:
            raw = _decompress(resp2, resp2.read(15_000_000))
        return {"ok": True, "status": int(snap.get("status", 200)), "final_url": snap_url,
                "content": raw, "note": f"Wayback snapshot {snap.get('timestamp','')}"}
    except Exception as e:
        return {"ok": False, "status": None, "final_url": url, "content": b"", "note": f"wayback: {e.__class__.__name__}"}


PRONGS = [("browser_headers", prong_browser_headers), ("requests_session", prong_requests_session),
          ("playwright", prong_playwright), ("wayback", prong_wayback)]


def resilient_get(url: str, ignore_robots: bool = False, run_all: bool = False, delay: float = 1.0) -> dict:
    """Try each prong until one succeeds (or all, with run_all). Returns the best result + a trail."""
    if not _robots_ok(url, ignore_robots):
        return {"ok": False, "status": None, "prong": None, "final_url": url, "content": b"",
                "note": "blocked by robots.txt (use --ignore-robots for authorized public data)", "trail": []}
    trail, best = [], None
    for name, fn in PRONGS:
        if delay:
            time.sleep(delay)
        r = fn(url)
        r["prong"] = name
        trail.append({"prong": name, "ok": r["ok"], "status": r["status"], "note": r["note"]})
        if r["ok"] and best is None:
            best = r
            if not run_all:
                break
    out = best or {"ok": False, "status": None, "prong": None, "final_url": url, "content": b"",
                   "note": "all prongs failed"}
    out["trail"] = trail
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--all", action="store_true", help="run every prong, not first-success")
    ap.add_argument("--out", help="save recovered content to this file")
    ap.add_argument("--ignore-robots", action="store_true", help="maintainer override (public data only)")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args(argv)
    if not args.url:
        ap.print_help()
        return 0
    r = resilient_get(args.url, ignore_robots=args.ignore_robots, run_all=args.all, delay=args.delay)
    print(f"URL: {args.url}")
    for t in r["trail"]:
        print(f"  [{'OK ' if t['ok'] else 'no '}] {t['prong']:16} {t['status']}  {t['note']}")
    print(f"\nRESULT: {'RECOVERED via ' + r['prong'] if r['ok'] else 'FAILED (all prongs)'}")
    if r["ok"]:
        print(f"  final_url: {r['final_url']}  bytes: {len(r['content'])}")
        if args.out:
            Path(args.out).write_bytes(r["content"])
            print(f"  saved -> {args.out}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
