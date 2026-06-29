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
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fetch_resilient as FR  # reuse BROWSER_HEADERS, prong_browser_headers, prong_wayback, _robots_ok, _decompress  # noqa

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


# ---- prong 4: mirror (download linked files + same-domain pages) --------------
def mirror(seed_html: str, base_url: str, outdir: Path, depth: int, max_files: int,
           max_pages: int, ignore_robots: bool, delay: float = 1.0) -> dict:
    files_dir = outdir / "files"; files_dir.mkdir(exist_ok=True)
    got_files, got_pages, seen = [], [], {base_url}
    queue = [(base_url, seed_html, 0)]
    while queue:
        cur_url, cur_html, d = queue.pop(0)
        for link in _links(cur_html, cur_url):
            low = link.lower().split("?")[0]
            if low.endswith(FILE_EXT) and link not in seen and len(got_files) < max_files:
                seen.add(link)
                if not ignore_robots and not FR._robots_ok(link, False):
                    continue
                try:
                    time.sleep(delay)
                    req = urllib.request.Request(link, headers=FR.BROWSER_HEADERS)
                    with urllib.request.urlopen(req, timeout=25) as r:
                        data = r.read(30_000_000)
                    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", urllib.parse.urlparse(link).path.split("/")[-1] or "file")[:80]
                    (files_dir / name).write_bytes(data)
                    got_files.append(link)
                except Exception:
                    pass
            elif d < depth and _same_domain(link, base_url) and link not in seen and len(got_pages) < max_pages:
                seen.add(link)
                try:
                    time.sleep(delay)
                    req = urllib.request.Request(link, headers=FR.BROWSER_HEADERS)
                    with urllib.request.urlopen(req, timeout=20) as r:
                        sub = FR._decompress(r, r.read(10_000_000)).decode("utf-8", "replace")
                    pname = re.sub(r"[^a-zA-Z0-9]+", "_", link)[:70] + ".html"
                    (outdir / pname).write_text(sub, encoding="utf-8")
                    got_pages.append(link); queue.append((link, sub, d + 1))
                except Exception:
                    pass
    return {"files": got_files, "pages": got_pages}


def acquire(url: str, outdir: Path, ignore_robots: bool = False, depth: int = 1,
            max_files: int = 40, max_pages: int = 10, do_ocr: bool = True) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"url": url, "artifacts": {}, "ok_any": False}
    if not ignore_robots and not FR._robots_ok(url, False):
        manifest["note"] = "blocked by robots.txt (use --ignore-robots for authorized public data)"
        (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    seed_html = ""
    # 1. browser-headers GET
    r1 = FR.prong_browser_headers(url)
    if r1.get("ok") and r1.get("content"):
        seed_html = r1["content"].decode("utf-8", "replace")
        (outdir / "raw.html").write_text(seed_html, encoding="utf-8")
        manifest["artifacts"]["raw_html"] = True; manifest["ok_any"] = True
    # 2/3. render + screenshot (better DOM; use it as seed if static was thin/blocked)
    rs = render_and_shot(url, outdir)
    manifest["artifacts"].update({"rendered_html": rs["render"], "screenshot": rs["screenshot"]})
    if rs["render"]:
        manifest["ok_any"] = True
        rendered = (outdir / "rendered.html").read_text(encoding="utf-8", errors="replace")
        if len(rendered) > len(seed_html):
            seed_html = rendered
    if do_ocr and rs["screenshot"]:
        manifest["artifacts"]["ocr_text"] = ocr_screenshot(outdir)
    # 5. wayback backstop (always — different host; rescues 403/404)
    rw = FR.prong_wayback(url)
    if rw.get("ok") and rw.get("content"):
        (outdir / "wayback.html").write_text(rw["content"].decode("utf-8", "replace"), encoding="utf-8")
        manifest["artifacts"]["wayback_html"] = True; manifest["ok_any"] = True
        if not seed_html:
            seed_html = rw["content"].decode("utf-8", "replace")
    # 4. mirror linked files + same-domain pages from whatever HTML we got
    if seed_html:
        m = mirror(seed_html, url, outdir, depth, max_files, max_pages, ignore_robots)
        manifest["artifacts"]["mirrored_files"] = len(m["files"])
        manifest["artifacts"]["mirrored_pages"] = len(m["pages"])
        if m["files"] or m["pages"]:
            manifest["ok_any"] = True

    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
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
    a = ap.parse_args(argv)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", a.url)[:70]
    out = Path(a.out) / slug
    m = acquire(a.url, out, a.ignore_robots, a.depth, a.max_files, a.max_pages, not a.no_ocr)
    print(json.dumps(m, indent=2))
    print(f"\n{'RECOVERED' if m['ok_any'] else 'FAILED (all methods)'} -> {out}")
    return 0 if m["ok_any"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
