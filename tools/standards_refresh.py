#!/usr/bin/env python3
"""Standards refresh — politely crawl canonical sources for newer stored resources.

Reads a resource manifest (default: shared/standards/resources/florida/sources.json),
crawls its `crawl_seeds` (official sources — CPALMS, FLDOE, WIDA), discovers document
links (pdf/doc/docx/xlsx), and reports what is NEW or CHANGED vs. the stored sha256s.
Optionally downloads the updates and writes a timestamped JSON report.

Design (ethical, public-data crawler — NOT an evasion tool):
  - Respects robots.txt (skips disallowed paths) — compliance, not bypass.
  - One honest, identifying User-Agent (no browser-impersonation/rotation).
  - Polite randomized delays; backs OFF on 429/robots/JS/CAPTCHA rather than bypassing.
  - Detects JS-required pages (CPALMS search is a JS app) and reports them for a
    browser-rendered fetch instead of pretending to scrape them.
Patterns adapted from a robots-respecting "detect → polite-crawl → report" scraper design.

Stdlib only (urllib + robotparser + html.parser); uses `requests`/`bs4` automatically if
installed (see tools/requirements-scraper.txt). Network required for --crawl/--download.

Usage:
  python3 tools/standards_refresh.py --check                       # offline: validate + plan
  python3 tools/standards_refresh.py --crawl                       # report new/changed (+ JSON report)
  python3 tools/standards_refresh.py --crawl --download out/       # also download updates
Options: --manifest PATH --max-pages N(200) --max-depth N(2) --min-delay S(1.5) --max-delay S(3.0)
         --timeout S(30) --user-agent UA --report PATH --no-robots(not recommended)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

try:                       # optional, better fetch/parse if available
    import requests       # noqa
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "shared" / "standards" / "resources" / "florida" / "sources.json"
DOC_EXTS = (".pdf", ".doc", ".docx", ".xlsx", ".rtf")
DEFAULT_UA = "TOS-standards-updater/1.1 (+polite educational-standards update checker; respects robots.txt)"
JS_INDICATORS = ("enable javascript", "javascript is required", "please enable javascript", "<noscript")
CAPTCHA_INDICATORS = ("recaptcha", "hcaptcha", "verify you are human", "prove you are human")


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)


def reg_domain(netloc: str) -> str:
    return ".".join(netloc.lower().split(":")[0].split(".")[-2:])


class Fetcher:
    """Honest, robots-respecting, polite fetcher. Backs off; never evades."""

    def __init__(self, ua, timeout, respect_robots=True):
        self.ua = ua
        self.timeout = timeout
        self.respect_robots = respect_robots
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def allowed(self, url) -> bool:
        if not self.respect_robots:
            return True
        pr = urllib.parse.urlparse(url)
        base = f"{pr.scheme}://{pr.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(base + "/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = None        # no robots reachable -> treat as allowed
            self._robots[base] = rp
        rp = self._robots[base]
        return True if rp is None else rp.can_fetch(self.ua, url)

    def get(self, url) -> tuple[int, bytes, str]:
        """Return (status, body, content_type). status 0 on transport error."""
        headers = {"User-Agent": self.ua,
                   "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                   "Accept-Language": "en-US,en;q=0.5"}
        if _HAS_REQUESTS:
            try:
                r = requests.get(url, headers=headers, timeout=self.timeout)
                return r.status_code, r.content, r.headers.get("Content-Type", "")
            except Exception:
                return 0, b"", ""
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read(), resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            return e.code, b"", ""
        except Exception:
            return 0, b"", ""


def detect(html: str) -> dict:
    low = html.lower()
    return {"js_required": any(t in low for t in JS_INDICATORS) or len(html.strip()) < 500,
            "captcha": any(t in low for t in CAPTCHA_INDICATORS)}


def crawl(seeds, fetcher, max_pages, max_depth, min_delay, max_delay):
    seen, docs = set(), {}
    report = {"visited": 0, "skipped_robots": [], "js_required": [], "captcha": [],
              "rate_limited": [], "errors": []}
    allowed_doms = {reg_domain(urllib.parse.urlparse(s).netloc) for s in seeds}
    queue = [(s, 0) for s in seeds]
    while queue and report["visited"] < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if not fetcher.allowed(url):
            report["skipped_robots"].append(url)
            continue
        status, body, ctype = fetcher.get(url)
        if status == 429:
            report["rate_limited"].append(url)
            time.sleep(max_delay * 2)            # back off, do not evade
            continue
        if status == 0 or status >= 400 or not body:
            report["errors"].append(f"{url} (status {status})")
            continue
        report["visited"] += 1
        time.sleep(random.uniform(min_delay, max_delay))   # polite jitter
        if "html" not in ctype.lower():
            continue
        text = body.decode("utf-8", "ignore")
        flags = detect(text)
        if flags["captcha"]:
            report["captcha"].append(url)
        if flags["js_required"]:
            report["js_required"].append(url)   # needs a browser-rendered fetch; reported, not faked
        p = LinkParser()
        try:
            p.feed(text)
        except Exception:
            continue
        for href in p.links:
            absu = urllib.parse.urljoin(url, href).split("#")[0]
            pr = urllib.parse.urlparse(absu)
            if pr.scheme not in ("http", "https") or reg_domain(pr.netloc) not in allowed_doms:
                continue
            if pr.path.lower().endswith(DOC_EXTS):
                docs.setdefault(absu, urllib.parse.unquote(pr.path.lower().rsplit("/", 1)[-1]))
            elif depth < max_depth and absu not in seen:
                queue.append((absu, depth + 1))
    return docs, report


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--crawl", action="store_true")
    ap.add_argument("--download", metavar="DIR")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--min-delay", type=float, default=1.5)
    ap.add_argument("--max-delay", type=float, default=3.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--user-agent", default=DEFAULT_UA)
    ap.add_argument("--report", metavar="PATH")
    ap.add_argument("--no-robots", action="store_true", help="(not recommended) ignore robots.txt")
    ap.add_argument("--update-hashes", action="store_true", help="save watch-page baseline hashes to the manifest")
    a = ap.parse_args(argv)

    man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    seeds = man.get("crawl_seeds", [])
    known = {f["filename"].lower(): f for f in man.get("files", [])}
    print(f"manifest: {a.manifest}\nschool year: {man.get('current_school_year','?')}  "
          f"stored: {len(known)}  seeds: {len(seeds)}  fetch: {'requests' if _HAS_REQUESTS else 'urllib'}")

    cov = man.get("coverage", {})
    watch = man.get("watch_pages", [])
    if cov:
        print(f"coverage: {', '.join(cov)}")
    if a.check or not (a.crawl or a.download):
        print(f"\n[check] {len(seeds)} crawl seed(s) + {len(watch)} watch page(s) (content-change monitoring):")
        for s in seeds:
            print("  - seed:", s)
        for w in watch:
            print(f"  - watch[{w.get('category')}]: {w['url']}")
        print("\n[check] OK — manifest parses. Run --crawl (needs network) to check for updates.")
        return 0

    fetcher = Fetcher(a.user_agent, a.timeout, respect_robots=not a.no_robots)
    print(f"\n[crawl] polite crawl (UA='{a.user_agent[:40]}…', robots={'off' if a.no_robots else 'on'}, "
          f"delay {a.min_delay}-{a.max_delay}s)…")
    docs, rep = crawl(seeds, fetcher, a.max_pages, a.max_depth, a.min_delay, a.max_delay)

    new, changed = [], []
    for url, fname in sorted(docs.items()):
        if fname not in known:
            new.append({"file": fname, "url": url})
        elif a.download:
            st, body, _ = fetcher.get(url)
            if body and hashlib.sha256(body).hexdigest() != known[fname]["sha256"]:
                changed.append({"file": fname, "url": url, "_body": body})

    # watch pages: detect CONTENT changes (legislation / rules / guidance / graduation / curriculum)
    page_changes = []
    for w in watch:
        if not fetcher.allowed(w["url"]):
            page_changes.append({**w, "status": "skipped_robots"}); continue
        st, body, _ = fetcher.get(w["url"])
        time.sleep(random.uniform(a.min_delay, a.max_delay))
        if st == 0 or st >= 400 or not body:
            page_changes.append({**w, "status": f"error_{st}"}); continue
        h = hashlib.sha256(re.sub(r"\s+", " ", body.decode("utf-8", "ignore")).encode()).hexdigest()
        prev = w.get("sha256")
        page_changes.append({"url": w["url"], "label": w.get("label"), "category": w.get("category"),
                             "status": "baseline_recorded" if not prev else ("changed" if h != prev else "unchanged")})
        if a.update_hashes:
            w["sha256"] = h

    report = {"timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"), "manifest": a.manifest,
              "school_year": man.get("current_school_year"), "coverage": list(cov),
              "pages_visited": rep["visited"], "docs_found": len(docs),
              "new": new, "changed": [{k: v for k, v in c.items() if k != "_body"} for c in changed],
              "page_changes": page_changes,
              "skipped_robots": rep["skipped_robots"], "js_required": rep["js_required"],
              "captcha": rep["captcha"], "rate_limited": rep["rate_limited"], "errors": rep["errors"]}

    print(f"[crawl] visited {rep['visited']} page(s); {len(docs)} doc link(s); "
          f"NEW {len(new)}, CHANGED {len(changed)}.")
    for n in new[:50]:
        print(f"  + {n['file']}  <-  {n['url']}")
    chg = [p for p in page_changes if p["status"] == "changed"]
    base = [p for p in page_changes if p["status"] == "baseline_recorded"]
    for p in chg:
        print(f"  ! CHANGED [{p.get('category')}]: {p.get('label')}  ({p['url']})")
    if base:
        print(f"  [watch] {len(base)} baseline hash(es) recorded — run with --update-hashes to save them.")
    if rep["js_required"]:
        print(f"  [note] {len(rep['js_required'])} page(s) need a browser render (JS) — e.g. CPALMS "
              f"search; use a Selenium/Playwright fetch for those, or the static downloads page.")
    if rep["skipped_robots"] or any(p["status"] == "skipped_robots" for p in page_changes):
        print("  [note] some URL(s) skipped per robots.txt (respected).")

    if a.download:
        out = Path(a.download); out.mkdir(parents=True, exist_ok=True)
        for c in changed:
            (out / c["file"]).write_bytes(c["_body"]); print(f"  ~ {c['file']} (downloaded)")
        for n in new:
            st, body, _ = fetcher.get(n["url"])
            if body:
                (out / n["file"]).write_bytes(body)
        print(f"  downloaded updates to {out}/ — review, then update sources.json + re-verify on CPALMS.")

    if a.update_hashes:
        Path(a.manifest).write_text(json.dumps(man, indent=2), encoding="utf-8")
        print(f"  saved watch-page baseline hashes to {a.manifest}")

    if a.report:
        Path(a.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  report -> {a.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
