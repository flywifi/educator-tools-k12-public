#!/usr/bin/env python3
"""acquire.py — all-in redundant acquisition for ONE public URL (token-free, max-success).

Local fetching costs no model tokens, so the efficient strategy is REDUNDANCY, not first-success:
throw every method at a URL, keep whatever lands, and parse it offline. This makes a hard 403/404
very unlikely to block you — if the live site refuses, the archive has it; if it's a JS app, the
real browser renders it; if it's image-only, the screenshot+OCR recovers it; and the page's linked
files get mirrored regardless.

PER URL it gathers (each independent — one failing never stops the others):
  1. browser_headers   full-browser-header GET                 -> raw.html        (beats naive 403)
  2. render            headless Chromium, runs JS              -> rendered.html   (beats JS + bot walls)
  3. screenshot[+OCR]  full-page screenshot (+ tesseract OCR)  -> page.png/ocr.txt(beats image-only)
  4. mirror            download linked FILES (+ same-domain     -> files/*         (gets the actual data)
                       pages to --depth) found in the HTML
  5. wayback           closest Internet Archive snapshot        -> wayback.html    (404/403 backstop)
All artifacts land in an out folder + a manifest.json. Robots respected unless --ignore-robots
(maintainer override for authorized public data). Honest capability gaps when playwright/OCR absent.

USAGE
  python3 tools/acquire.py "https://www.fldoe.org/academics/standards/" --out acq/ --ignore-robots
  python3 tools/acquire.py URL --out acq/ --depth 1 --max-files 40   (mirror 1 level + up to 40 files)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fetch_resilient as FR  # reuse BROWSER_HEADERS, prong_browser_headers, prong_wayback, _robots_ok, _decompress  # noqa
import rate_governor as RG  # per-host pacing + lockout avoidance (Crawl-delay/Retry-After/breaker/budget)  # noqa
import fetch_diag as FD  # detect WHY blocked (vendor/challenge) + structured-source hints (no evasion)  # noqa
import fetch_cache as FC  # conditional/incremental fetch — only re-download what changed  # noqa

CHROME_CANDIDATES = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome"]
FILE_EXT = (".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv", ".zip", ".json", ".xml")


def _links(html_text: str, base: str) -> list[str]:
    out = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html_text, re.I):
        if href.startswith(("javascript:", "#", "mailto:")):
            continue
        out.append(urllib.parse.urljoin(base, href))
    return out


def _same_domain(a: str, b: str) -> bool:
    return urllib.parse.urlparse(a).netloc.split(":")[0].replace("www.", "") == \
           urllib.parse.urlparse(b).netloc.split(":")[0].replace("www.", "")


# ---- prong 2/3: headless render + screenshot (one browser pass) ---------------
def render_and_shot(url: str, outdir: Path, timeout: float = 45.0) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {"render": False, "screenshot": False, "note": "playwright not installed"}
    res = {"render": False, "screenshot": False, "note": ""}
    try:
        with sync_playwright() as p:
            kw = {}
            for c in CHROME_CANDIDATES:
                if Path(c).exists():
                    kw["executable_path"] = c
            b = p.chromium.launch(headless=True, **kw)
            pg = b.new_page(user_agent=FR.BROWSER_HEADERS["User-Agent"])
            pg.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            pg.wait_for_timeout(2500)
            (outdir / "rendered.html").write_text(pg.content(), encoding="utf-8")
            res["render"] = True
            try:
                pg.screenshot(path=str(outdir / "page.png"), full_page=True)
                res["screenshot"] = True
            except Exception as e:
                res["note"] = f"screenshot failed: {e}"
            b.close()
    except Exception as e:
        res["note"] = f"render failed: {e.__class__.__name__}"
    return res


def ocr_screenshot(outdir: Path) -> bool:
    shot = outdir / "page.png"
    if not shot.exists():
        return False
    try:
        import pytesseract
        from PIL import Image
        txt = pytesseract.image_to_string(Image.open(shot))
        (outdir / "ocr.txt").write_text(txt, encoding="utf-8")
        return True
    except Exception:
        return False


def _governed_get(gov: "RG.RateGovernor", url: str, timeout: float, cap: int,
                  cache: "FC.FetchCache" = None):
    """One host-paced GET. Honors the per-host breaker/budget (and robots, unless the governor was
    built with respect_robots=False), spaces requests, and on a 429/503 backs off the server-directed
    amount and retries the SAME url. With a cache, sends a CONDITIONAL GET and skips unchanged content.
    Returns (raw_bytes, headers), (b"", {"unchanged": True}) when nothing changed, or (None, reason)."""
    ok, why = gov.can_request(url)
    if not ok:
        return None, why
    for attempt in range(3):
        gov.wait(url)
        try:
            headers = dict(FR.BROWSER_HEADERS)
            if cache:
                headers.update(cache.validators(url))  # If-None-Match / If-Modified-Since
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(cap)
                hdrs = dict(r.headers)
            gov.note(url, getattr(r, "status", 200), hdrs)
            if cache and not cache.update(url, hdrs, raw):
                return b"", {"unchanged": True}     # server re-sent byte-identical content -> skip write
            return raw, hdrs
        except urllib.error.HTTPError as e:
            if e.code == 304:                        # Not Modified: cheapest "unchanged" signal
                gov.note(url, 304, {})
                if cache:
                    cache.note_unchanged(url)
                return b"", {"unchanged": True}
            hdrs = dict(getattr(e, "headers", {}) or {})
            wait = gov.note(url, e.code, hdrs)
            if wait is not None and attempt < 2:
                time.sleep(wait)
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            gov.note(url, 0, {})
            return None, e.__class__.__name__
    return None, "retries exhausted"


# ---- prong 4: mirror (download linked files + same-domain pages) --------------
def mirror(seed_html: str, base_url: str, outdir: Path, depth: int, max_files: int,
           max_pages: int, ignore_robots: bool, gov: "RG.RateGovernor" = None,
           cache: "FC.FetchCache" = None) -> dict:
    if gov is None:
        gov = RG.RateGovernor(FR.BROWSER_HEADERS["User-Agent"], respect_robots=not ignore_robots)
    files_dir = outdir / "files"; files_dir.mkdir(exist_ok=True)
    got_files, got_pages, unchanged, seen = [], [], 0, {base_url}
    queue = [(base_url, seed_html, 0)]
    while queue:
        cur_url, cur_html, d = queue.pop(0)
        for link in _links(cur_html, cur_url):
            low = link.lower().split("?")[0]
            if low.endswith(FILE_EXT) and link not in seen and len(got_files) < max_files:
                seen.add(link)
                data, info = _governed_get(gov, link, 25, 30_000_000, cache)
                if data is None:
                    continue
                if isinstance(info, dict) and info.get("unchanged"):
                    unchanged += 1; got_files.append(link); continue  # already have it; don't re-write
                name = re.sub(r"[^a-zA-Z0-9._-]+", "_", urllib.parse.urlparse(link).path.split("/")[-1] or "file")[:80]
                (files_dir / name).write_bytes(data)
                got_files.append(link)
            elif d < depth and _same_domain(link, base_url) and link not in seen and len(got_pages) < max_pages:
                seen.add(link)
                raw, info = _governed_get(gov, link, 20, 10_000_000, cache)
                if raw is None:
                    continue
                if isinstance(info, dict) and info.get("unchanged"):
                    unchanged += 1; got_pages.append(link); continue
                enc = (info.get("Content-Encoding") or "").lower() if isinstance(info, dict) else ""
                sub = _decode(raw, enc)
                pname = re.sub(r"[^a-zA-Z0-9]+", "_", link)[:70] + ".html"
                (outdir / pname).write_text(sub, encoding="utf-8")
                got_pages.append(link); queue.append((link, sub, d + 1))
    return {"files": got_files, "pages": got_pages, "unchanged": unchanged}


def _decode(raw: bytes, content_encoding: str) -> str:
    import gzip
    import zlib
    try:
        if "gzip" in content_encoding:
            raw = gzip.decompress(raw)
        elif "deflate" in content_encoding:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:  # noqa: BLE001
        pass
    return raw.decode("utf-8", "replace")


def acquire(url: str, outdir: Path, ignore_robots: bool = False, depth: int = 1,
            max_files: int = 40, max_pages: int = 10, do_ocr: bool = True,
            gov: "RG.RateGovernor" = None, per_host_budget: int = RG.DEFAULT_BUDGET,
            min_interval: float = RG.DEFAULT_MIN_INTERVAL) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"url": url, "artifacts": {}, "ok_any": False}
    # One governor enforces per-host pacing + lockout avoidance across every prong (and, when a single
    # one is shared across a whole harvest run, across every URL). --ignore-robots only drops the
    # robots gate; the breaker/budget/server-backoff still protect against an IP lockout.
    if gov is None:
        gov = RG.RateGovernor(FR.BROWSER_HEADERS["User-Agent"], per_host_budget=per_host_budget,
                              min_interval=min_interval, respect_robots=not ignore_robots)
    ok, why = gov.can_request(url)
    if not ok:
        manifest["note"] = f"skipped: {why}"
        (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        gov.save()
        return manifest

    cache = FC.FetchCache()
    seed_html = ""
    # 1. browser-headers GET (host-paced; feeds the governor so repeated 403/429 trips the breaker)
    gov.wait(url)
    r1 = FR.prong_browser_headers(url)
    gov.note(url, r1.get("status"), None)
    static_body = r1["content"].decode("utf-8", "replace") if r1.get("content") else ""
    if r1.get("ok") and r1.get("content"):
        seed_html = static_body
        (outdir / "raw.html").write_text(seed_html, encoding="utf-8")
        manifest["artifacts"]["raw_html"] = True; manifest["ok_any"] = True
    # DETECT (not evade) why a block happened, from static signatures. A high-confidence vendor
    # challenge / IP block that a plain GET can't pass -> proactively rest the host (the real-browser
    # render below may still legitimately load it; otherwise we lean on Wayback / the official source).
    block = FD.classify_block(r1.get("status"), None, static_body)
    manifest["block"] = block
    if block["blocked"] and not block["retry_worthwhile"] and block["confidence"] != "low":
        gov.cooldown(url, reason=f"{block['vendor'] or block['kind']} block")
    # 2/3. render + screenshot (a real browser hit — pace it too; better DOM beats a thin/blocked static page)
    if gov.can_request(url)[0]:
        gov.wait(url)
        rs = render_and_shot(url, outdir)
    else:
        rs = {"render": False, "screenshot": False, "note": "skipped (breaker/budget)"}
    manifest["artifacts"].update({"rendered_html": rs["render"], "screenshot": rs["screenshot"]})
    if rs["render"]:
        manifest["ok_any"] = True
        rendered = (outdir / "rendered.html").read_text(encoding="utf-8", errors="replace")
        if len(rendered) > len(seed_html):
            seed_html = rendered
    if do_ocr and rs["screenshot"]:
        manifest["artifacts"]["ocr_text"] = ocr_screenshot(outdir)
    # 5. wayback backstop (always — different host, paced under archive.org's own budget; rescues 403/404)
    rw = FR.prong_wayback(url)
    if rw.get("ok") and rw.get("content"):
        (outdir / "wayback.html").write_text(rw["content"].decode("utf-8", "replace"), encoding="utf-8")
        manifest["artifacts"]["wayback_html"] = True; manifest["ok_any"] = True
        if not seed_html:
            seed_html = rw["content"].decode("utf-8", "replace")
    # "Is there an API?" — spot structured sources already on the page so a later pass can prefer them
    # over scraping rendered HTML (more accurate, nothing inferred; and it sidesteps the anti-bot wall).
    manifest["data_sources"] = FD.find_data_sources(seed_html, url)
    # 4. mirror linked files + same-domain pages from whatever HTML we got (same governor + fetch cache)
    if seed_html:
        m = mirror(seed_html, url, outdir, depth, max_files, max_pages, ignore_robots, gov, cache)
        manifest["artifacts"]["mirrored_files"] = len(m["files"])
        manifest["artifacts"]["mirrored_pages"] = len(m["pages"])
        manifest["artifacts"]["unchanged_skipped"] = m["unchanged"]
        if m["files"] or m["pages"]:
            manifest["ok_any"] = True

    manifest["rate"] = gov.summary()
    manifest["incremental"] = cache.summary()
    manifest["diag"] = FD.summarize(block, manifest["data_sources"])
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    gov.save()
    cache.save()
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out", default="acquired")
    ap.add_argument("--ignore-robots", action="store_true")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--max-files", type=int, default=40)
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--per-host-budget", type=int, default=RG.DEFAULT_BUDGET,
                    help="max requests per host this run before self-limiting (lockout guard)")
    ap.add_argument("--min-interval", type=float, default=RG.DEFAULT_MIN_INTERVAL,
                    help="polite floor (seconds) between same-host requests; robots Crawl-delay wins if slower")
    # dependency-preflight flags (consumed by deps_preflight via sys.argv; declared here so argparse
    # accepts them and they survive the re-exec into the isolated venv)
    ap.add_argument("--update-deps", action="store_true", help="force an upgrade pass of all deps now")
    ap.add_argument("--no-update", action="store_true", help="skip the deps upgrade pass (verify presence only)")
    ap.add_argument("--no-venv", action="store_true", help="use the current interpreter (probe-only, no installs)")
    ap.add_argument("--reset-venv", action="store_true", help="delete + rebuild the isolated .harvest-venv")
    ap.add_argument("--no-deps", action="store_true", help="disable the dependency preflight entirely")
    a = ap.parse_args(argv)
    # Dependency preflight FIRST: ensure every OCR + document-parsing + browser tool this run might
    # touch (playwright/chromium, pytesseract+tesseract, pymupdf, pdfplumber, pillow, openpyxl,
    # beautifulsoup4, markitdown, requests) is present and current in the isolated .harvest-venv.
    import deps_preflight  # local; stdlib-only at import time  # noqa: E402
    deps_preflight.preflight()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", a.url)[:70]
    out = Path(a.out) / slug
    m = acquire(a.url, out, a.ignore_robots, a.depth, a.max_files, a.max_pages, not a.no_ocr,
                per_host_budget=a.per_host_budget, min_interval=a.min_interval)
    print(json.dumps(m, indent=2))
    print(f"\n{'RECOVERED' if m['ok_any'] else 'FAILED (all methods)'} -> {out}")
    return 0 if m["ok_any"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
