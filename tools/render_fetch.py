#!/usr/bin/env python3
"""render_fetch — recover content from a JS-required / hard-to-scrape PUBLIC page via a chain of
redundancy prongs (LOCAL render -> offline docintel parse -> screenshot+OCR -> optional cloud).

This is the LOCAL, offline-first counterpart to the cloud firecrawl prong. It exists so a page the
polite stdlib crawler reports as `js_required` (e.g. the CPALMS standards search SPA) can still be
read — without ever impersonating a browser or bypassing a CAPTCHA/rate-limit. Same honest UA,
robots.txt respected, the site's own JavaScript simply run the way a browser is meant to.

Usage:
  python3 tools/render_fetch.py --check                      # list prongs + availability (offline)
  python3 tools/render_fetch.py <url>                        # run the chain, print the JSON report
  python3 tools/render_fetch.py <url> --out out/            # also save rendered.html/page.png/extracted.txt
  python3 tools/render_fetch.py <url> --all                  # run EVERY available prong (redundancy)
  python3 tools/render_fetch.py <url> --prongs local_render,offline_docintel
  python3 tools/render_fetch.py <url> --enable-cloud         # allow the firecrawl prong (if configured)
  python3 tools/render_fetch.py <url> --no-robots            # NOT recommended; robots respected by default

Prongs: http_static, local_render, offline_docintel, screenshot_ocr, cloud_render.
Each absent dependency is reported as an honest capability gap, never faked. Output always carries
human_review_required: true.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared"))

import render  # noqa: E402  (path set above)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Resilient multi-prong fetch for JS-required public pages.")
    ap.add_argument("url", nargs="?", help="the public page to recover")
    ap.add_argument("--check", action="store_true", help="list prongs + availability and exit")
    ap.add_argument("--out", help="directory to write rendered.html / page.png / extracted.txt")
    ap.add_argument("--prongs", help="comma list/order subset of: "
                    "http_static,local_render,offline_docintel,screenshot_ocr,cloud_render")
    ap.add_argument("--all", action="store_true", dest="all_prongs",
                    help="run every prong (redundancy/comparison) instead of stopping at first success")
    ap.add_argument("--timeout", type=float, default=30.0, help="per-prong timeout seconds (default 30)")
    ap.add_argument("--user-agent", default=render.HONEST_UA, help="honest identifying UA (no rotation)")
    ap.add_argument("--no-robots", action="store_true", help="(discouraged) do not consult robots.txt")
    ap.add_argument("--enable-cloud", action="store_true",
                    help="allow the firecrawl cloud prong if FIRECRAWL_* configured (off by default)")
    a = ap.parse_args(argv)

    if a.check:
        caps = render.capability_report()
        print("render_fetch — prong availability (capability-gated, honest gaps):")
        for name, info in caps.items():
            flag = "available" if info["available"] else "unavailable"
            print(f"  - {name:<18} {flag:<12} needs: {info['needs']}")
        print("\nOrder (first-success-wins unless --all):", ", ".join(render.DEFAULT_ORDER))
        print("Ethics: one honest UA, robots respected, no impersonation/CAPTCHA/rate-limit bypass.")
        return 0

    if not a.url:
        ap.error("provide a URL to fetch, or use --check")

    prongs = [p.strip() for p in a.prongs.split(",")] if a.prongs else None
    rep = render.resilient_fetch(
        a.url, prongs=prongs, all_prongs=a.all_prongs, out_dir=a.out, timeout=a.timeout,
        ua=a.user_agent, respect_robots=not a.no_robots, enable_cloud=a.enable_cloud)

    # Trim large bodies for console readability; full content is on disk when --out is given.
    printable = dict(rep)
    if printable.get("html"):
        printable["html"] = f"<{len(rep['html'])} chars>" + (" (saved)" if a.out else "")
    if printable.get("text") and len(printable["text"]) > 600:
        printable["text"] = printable["text"][:600] + f"... <{len(rep['text'])} chars total>"
    print(json.dumps(printable, indent=2))

    return 0 if rep["prong_succeeded"] not in ("none",) else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
