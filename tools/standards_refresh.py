#!/usr/bin/env python3
"""Standards refresh — crawl canonical sources for newer versions of stored resources.

Reads a resource manifest (default: shared/standards/resources/florida/sources.json), then
recursively crawls its `crawl_seeds` (official sources — CPALMS, FLDOE, WIDA), discovers
document links (pdf/doc/docx/xlsx), and reports what is NEW or CHANGED relative to the stored
snapshot. Optionally downloads the updates.

This keeps the standards corpus current as standards change: the stored files are a dated
snapshot; the canonical sources in the manifest are the live authority.

Stdlib only. Requires outbound network for --crawl/--download (use --check offline).

Usage:
  python3 tools/standards_refresh.py --check                  # offline: validate manifest, show plan
  python3 tools/standards_refresh.py --crawl                  # crawl sources, report new/changed
  python3 tools/standards_refresh.py --crawl --download out/  # also download updates to out/
Options: --manifest PATH  --max-pages N(200)  --max-depth N(2)  --delay S(1.0)  --timeout S(30)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "shared" / "standards" / "resources" / "florida" / "sources.json"
DOC_EXTS = (".pdf", ".doc", ".docx", ".xlsx", ".rtf")
UA = "TOS-standards-refresh/1.0 (+educational standards update checker; contact: repo owner)"


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


def fetch(url: str, timeout: float) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def crawl(seeds, max_pages, max_depth, delay, timeout):
    """BFS over same-registrable-domain pages; return {doc_url: ...} discovered."""
    seen_pages, docs = set(), {}
    allowed = {reg_domain(urllib.parse.urlparse(s).netloc) for s in seeds}
    queue = [(s, 0) for s in seeds]
    pages = 0
    while queue and pages < max_pages:
        url, depth = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        try:
            body, ctype = fetch(url, timeout)
            pages += 1
        except Exception as e:
            print(f"  [skip] {url} ({e})")
            continue
        time.sleep(delay)  # politeness
        if "html" not in ctype.lower():
            continue
        p = LinkParser()
        try:
            p.feed(body.decode("utf-8", "ignore"))
        except Exception:
            continue
        for href in p.links:
            absu = urllib.parse.urljoin(url, href).split("#")[0]
            pr = urllib.parse.urlparse(absu)
            if pr.scheme not in ("http", "https"):
                continue
            if reg_domain(pr.netloc) not in allowed:
                continue
            low = pr.path.lower()
            if low.endswith(DOC_EXTS):
                docs.setdefault(absu, urllib.parse.unquote(low.rsplit("/", 1)[-1]))
            elif depth < max_depth and absu not in seen_pages:
                queue.append((absu, depth + 1))
    return docs, pages


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--check", action="store_true", help="offline: validate + show plan")
    ap.add_argument("--crawl", action="store_true", help="crawl sources for updates")
    ap.add_argument("--download", metavar="DIR", help="download new/changed docs to DIR")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args(argv)

    man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    seeds = man.get("crawl_seeds", [])
    known = {f["filename"].lower(): f for f in man.get("files", [])}

    print(f"manifest: {a.manifest}")
    print(f"snapshot: {man.get('snapshot')}  stored files: {len(known)}  seeds: {len(seeds)}")

    if a.check or not (a.crawl or a.download):
        print("\n[check] crawl seeds (canonical sources):")
        for s in seeds:
            print("  -", s)
        print("\n[check] OK — manifest parses; run with --crawl (needs network) to check for updates.")
        return 0

    print("\n[crawl] discovering documents from canonical sources...")
    docs, pages = crawl(seeds, a.max_pages, a.max_depth, a.delay, a.timeout)
    print(f"[crawl] visited {pages} page(s); found {len(docs)} document link(s).")

    new, changed = [], []
    for url, fname in sorted(docs.items()):
        if fname not in known:
            new.append((fname, url))
        elif a.download:  # only verify content when downloading (costs a GET)
            try:
                body, _ = fetch(url, a.timeout)
                if hashlib.sha256(body).hexdigest() != known[fname]["sha256"]:
                    changed.append((fname, url, body))
            except Exception as e:
                print(f"  [skip verify] {url} ({e})")

    print(f"\nNEW (not in snapshot): {len(new)}")
    for fname, url in new[:50]:
        print(f"  + {fname}  <-  {url}")
    if a.download:
        print(f"\nCHANGED (content differs): {len(changed)}")
        out = Path(a.download); out.mkdir(parents=True, exist_ok=True)
        for fname, url, body in changed:
            (out / fname).write_bytes(body)
            print(f"  ~ {fname}  (downloaded)")
        for fname, url in new:
            try:
                body, _ = fetch(url, a.timeout)
                (out / fname).write_bytes(body)
            except Exception as e:
                print(f"  [skip download] {url} ({e})")
        print(f"\nDownloaded updates to {out}/. Review, then update sources.json + re-verify codes on CPALMS.")
    else:
        print("\nRun with --download DIR to fetch the updates. Then refresh sources.json + the catalog.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
