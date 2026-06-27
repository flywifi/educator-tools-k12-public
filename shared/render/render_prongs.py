#!/usr/bin/env python3
"""Resilient multi-prong fetch for JS-required / hard-to-scrape PUBLIC pages.

When the polite stdlib crawler (tools/standards_refresh.py) flags a page `js_required`
(e.g. the CPALMS standards search, a Single-Page App), this engine tries a chain of
*redundancy prongs* so the content can still be recovered — offline-first, first-success-wins
(or run them all with `all_prongs=True` for comparison/redundancy):

  1. http_static      — stdlib/`requests` fetch (the existing polite path). Free, no deps.
  2. local_render     — LOCAL Playwright Chromium (pre-installed at /opt/pw-browsers) runs the
                        page's OWN JavaScript and returns the rendered HTML. Gated on `playwright`.
  3. offline_docintel — persist the best HTML we have and run it through the docintel pipeline
                        (shared/docintel) for structured, fully offline extraction. Also the path
                        for a downloaded full-page/full-site HTML and any linked documents.
  4. screenshot_ocr   — Playwright full-page screenshot -> docintel OCR (tesseract). A fully
                        offline parse of the rendered *pixels* — last resort for canvas/image-only
                        content. Gated on `local_render` (capture) + `ocr` (recover text).
  5. cloud_render     — firecrawl (capability cloud_web_crawl), ONLY if FIRECRAWL_* is configured.
                        OFF by default; the offline prongs are always preferred.

ETHICS — this is RENDER, not EVASION. Every prong uses the SAME single honest, identifying
User-Agent, respects robots.txt, and (for the browser prongs) simply runs the site's own
JavaScript the way a browser is meant to. There is deliberately NO User-Agent rotation, NO
browser impersonation, and NO CAPTCHA / rate-limit bypass: if a CAPTCHA wall is detected the
chain STOPS and reports it honestly rather than attempting to defeat it. (See the design table in
skills/standards-updater/references/updater-method.md.)

Capability-gated + honest gaps: a prong whose deps are absent is skipped and recorded as a
`capability_gap`, never faked. Output always carries `human_review_required: true`. Stdlib-only at
import time; Playwright and docintel are imported lazily and guarded.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
SHARED = ROOT / "shared"

# One honest, identifying UA shared with tools/standards_refresh.py. We identify, we do not evade.
HONEST_UA = ("TOS-standards-updater/1.1 (+polite educational-standards update checker; "
             "respects robots.txt)")

JS_INDICATORS = ("enable javascript", "javascript is required", "please enable javascript", "<noscript")
CAPTCHA_INDICATORS = ("recaptcha", "hcaptcha", "verify you are human", "prove you are human")

# Where the pre-installed Chromium lives in this environment (no `playwright install` needed).
PW_BROWSERS_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")

DEFAULT_ORDER = ["http_static", "local_render", "offline_docintel", "screenshot_ocr", "cloud_render"]


# --------------------------------------------------------------------------- capability probes
def _have_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _have_bin(name: str) -> bool:
    from shutil import which
    return which(name) is not None


def capability_report() -> dict:
    """What each prong needs, and whether it is available right now (honest preflight)."""
    have_pw = _have_module("playwright")
    have_ocr = _have_module("pytesseract") and _have_module("PIL") and _have_bin("tesseract")
    have_docintel = (SHARED / "docintel" / "__init__.py").exists()
    have_cloud = _have_module("firecrawl") and bool(
        os.environ.get("FIRECRAWL_API_KEY") or os.environ.get("FIRECRAWL_BASE_URL"))
    return {
        "http_static": {"available": True, "needs": "stdlib (requests optional)"},
        "local_render": {"available": have_pw, "needs": "playwright (capability: local_render); "
                         f"Chromium pre-installed at {PW_BROWSERS_PATH}"},
        "offline_docintel": {"available": have_docintel, "needs": "shared/docintel pipeline"},
        "screenshot_ocr": {"available": have_pw and have_ocr,
                           "needs": "playwright (capture) + pytesseract/Pillow/tesseract (capability: ocr)"},
        "cloud_render": {"available": have_cloud,
                         "needs": "firecrawl + FIRECRAWL_API_KEY/BASE_URL (capability: cloud_web_crawl); OFF by default"},
    }


# --------------------------------------------------------------------------- politeness helpers
def robots_allowed(url: str, ua: str = HONEST_UA) -> bool:
    """True if robots.txt permits us (unreachable robots => treated as allowed)."""
    pr = urllib.parse.urlparse(url)
    base = f"{pr.scheme}://{pr.netloc}"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(base + "/robots.txt")
    try:
        rp.read()
    except Exception:
        return True
    try:
        return rp.can_fetch(ua, url)
    except Exception:
        return True


def detect(html: str) -> dict:
    low = html.lower()
    return {"js_required": any(t in low for t in JS_INDICATORS) or len(html.strip()) < 500,
            "captcha": any(t in low for t in CAPTCHA_INDICATORS)}


# --------------------------------------------------------------------------- prong 1: http_static
def prong_http_static(url: str, ua: str, timeout: float) -> dict:
    headers = {"User-Agent": ua,
               "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.5"}
    if _have_module("requests"):
        import requests  # noqa
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            return {"ok": r.status_code == 200, "status": r.status_code,
                    "html": r.text if r.content else "", "bytes": r.content,
                    "content_type": r.headers.get("Content-Type", "")}
        except Exception as e:
            return {"ok": False, "status": 0, "html": "", "bytes": b"", "error": str(e)}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            body = resp.read()
            return {"ok": resp.status == 200, "status": resp.status,
                    "html": body.decode("utf-8", "replace"), "bytes": body,
                    "content_type": resp.headers.get("Content-Type", "")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "html": "", "bytes": b"", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "status": 0, "html": "", "bytes": b"", "error": str(e)}


# --------------------------------------------------------------------------- prong 2/4: local_render
def _chromium_executable() -> Optional[str]:
    """Find the pre-installed Chromium so we never trigger a `playwright install` download."""
    base = Path(PW_BROWSERS_PATH)
    if not base.exists():
        return None
    for pat in ("chromium-*/chrome-linux/chrome", "chromium_headless_shell-*/chrome-linux/headless_shell",
                "chromium*/**/chrome", "chromium*/**/headless_shell"):
        hits = sorted(base.glob(pat))
        if hits:
            return str(hits[0])
    return None


def prong_local_render(url: str, ua: str, timeout: float, want_screenshot: bool = False) -> dict:
    """Render the page's own JS in the LOCAL pre-installed Chromium. Returns rendered HTML
    (+ optional full-page screenshot bytes). Honest UA; robots already checked by the caller."""
    if not _have_module("playwright"):
        return {"ok": False, "capability_gap": "local_render",
                "note": "playwright not installed; install tools/requirements-render.txt (Chromium is "
                        "already at /opt/pw-browsers — do NOT run `playwright install`)."}
    try:
        from playwright.sync_api import sync_playwright  # noqa
    except Exception as e:
        return {"ok": False, "capability_gap": "local_render", "note": f"playwright import failed: {e}"}

    launch_kwargs = {"args": ["--no-sandbox"]}
    exe = _chromium_executable()
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(**launch_kwargs)
            except Exception:
                if not exe:
                    raise
                browser = p.chromium.launch(executable_path=exe, **launch_kwargs)
            # Honest, identifying UA — the same one the polite crawler uses. No impersonation.
            page = browser.new_page(user_agent=ua, locale="en-US")
            try:
                page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            except Exception:
                # networkidle can time out on chatty pages; fall back to DOMContentLoaded content.
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                except Exception:
                    pass
            html = page.content()
            shot = page.screenshot(full_page=True) if want_screenshot else None
            browser.close()
        return {"ok": bool(html), "html": html, "screenshot": shot,
                "executable": exe or "playwright-default"}
    except Exception as e:
        return {"ok": False, "capability_gap": "local_render", "note": f"render failed: {e}"}


# --------------------------------------------------------------------------- prong 3/4b: docintel
def _docintel_extract(data: bytes, filename: str, media_type: Optional[str] = None) -> dict:
    """Run the docintel pipeline offline; return extracted text + confidence + governance summary.
    Reuses the SAME ingestion engine as tools/docintel_run.py — PDFs, HTML, .docx, images+OCR."""
    if not (SHARED / "docintel" / "__init__.py").exists():
        return {"ok": False, "capability_gap": "offline_docintel", "note": "shared/docintel not found"}
    if str(SHARED) not in sys.path:
        sys.path.insert(0, str(SHARED))
    try:
        import docintel  # noqa
    except Exception as e:
        return {"ok": False, "capability_gap": "offline_docintel", "note": f"docintel import failed: {e}"}
    try:
        pipeline = docintel.Pipeline(registry=docintel.default_registry())
        doc = pipeline.run(data, filename, media_type)
        artifact = docintel.build_knowledge_artifact(doc)
        report = docintel.validate(doc, artifact)
        text = "\n".join(
            getattr(b, "text", "") for p in getattr(doc, "pages", []) for b in getattr(p, "blocks", [])
            if getattr(b, "text", "")
        ).strip()
        rec = doc.diagnostics.get("recovery", {}) if hasattr(doc, "diagnostics") else {}
        return {"ok": bool(text), "text": text,
                "confidence": float(getattr(getattr(doc, "confidence", None), "value", 0.0) or 0.0),
                "parser": rec.get("parser"), "capability_gaps": rec.get("capability_gaps", []),
                "governance_ok": report.get("summary", {}).get("governance_ok"),
                "human_review_required": artifact.get("metadata", {}).get("human_review_required", True)}
    except Exception as e:
        return {"ok": False, "capability_gap": "offline_docintel", "note": f"docintel run failed: {e}"}


# --------------------------------------------------------------------------- prong 5: cloud_render
def prong_cloud_render(url: str) -> dict:
    """firecrawl managed JS render — ONLY if configured. Off by default; offline prongs preferred."""
    if not _have_module("firecrawl"):
        return {"ok": False, "capability_gap": "cloud_web_crawl", "note": "firecrawl not installed"}
    if not (os.environ.get("FIRECRAWL_API_KEY") or os.environ.get("FIRECRAWL_BASE_URL")):
        return {"ok": False, "capability_gap": "cloud_web_crawl",
                "note": "FIRECRAWL_API_KEY / FIRECRAWL_BASE_URL not set; cloud prong stays OFF"}
    try:
        from firecrawl import FirecrawlApp  # noqa
        app = FirecrawlApp(api_key=os.environ.get("FIRECRAWL_API_KEY"),
                           api_url=os.environ.get("FIRECRAWL_BASE_URL") or None)
        res = app.scrape_url(url, params={"formats": ["html", "markdown"]})
        html = (res or {}).get("html") or ""
        md = (res or {}).get("markdown") or ""
        return {"ok": bool(html or md), "html": html, "text": md}
    except Exception as e:
        return {"ok": False, "capability_gap": "cloud_web_crawl", "note": f"firecrawl failed: {e}"}


# --------------------------------------------------------------------------- orchestrator
def resilient_fetch(url: str, *, prongs: Optional[list[str]] = None, all_prongs: bool = False,
                    out_dir: Optional[str] = None, timeout: float = 30.0, ua: str = HONEST_UA,
                    respect_robots: bool = True, enable_cloud: bool = False) -> dict:
    """Try the redundancy prong chain until one recovers content (or run them all).

    Returns a structured, auditable report. `human_review_required` is always true. A detected
    CAPTCHA wall STOPS the chain (we never bypass). Robots.txt disallow STOPS the chain (we respect)."""
    prongs = prongs or DEFAULT_ORDER
    report = {
        "tool": "render_prongs.resilient_fetch",
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "prong_order": prongs,
        "prongs_attempted": [],
        "prong_succeeded": "none",
        "html": "", "text": "", "screenshot_path": None, "artifact": None,
        "confidence": 0.0,
        "capability_gaps": [],
        "captcha_detected": False,
        "human_review_required": True,
        "notes": [],
    }
    out = Path(out_dir) if out_dir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)

    if respect_robots and not robots_allowed(url, ua):
        report["notes"].append("skipped per robots.txt (respected, not bypassed)")
        return report

    best_html, best_bytes, screenshot_bytes = "", b"", None

    def record(name, ok, note="", gap=None):
        entry = {"prong": name, "ok": ok}
        if note:
            entry["note"] = note
        if gap:
            entry["capability_gap"] = gap
            if gap not in report["capability_gaps"]:
                report["capability_gaps"].append(gap)
        report["prongs_attempted"].append(entry)

    # ---- prong 1: http_static
    if "http_static" in prongs:
        r = prong_http_static(url, ua, timeout)
        flags = detect(r.get("html", "")) if r.get("html") else {"js_required": True, "captcha": False}
        if r.get("html"):
            best_html, best_bytes = r["html"], r.get("bytes", b"")
        if flags.get("captcha"):
            report["captcha_detected"] = True
            record("http_static", False, "CAPTCHA wall detected — STOPPING (we never bypass CAPTCHAs)")
            report["notes"].append("CAPTCHA detected; reported honestly, not bypassed")
            return report
        good = r.get("ok") and not flags.get("js_required")
        record("http_static", bool(good),
               "ok" if good else f"js_required/empty (status {r.get('status')})")
        if good and not all_prongs:
            report["prong_succeeded"] = "http_static"
            report["html"] = best_html
            if out:
                (out / "page.html").write_text(best_html, encoding="utf-8")
            # still offer a docintel structuring pass for downstream text
            di = _docintel_extract(best_bytes or best_html.encode("utf-8"), "page.html", "text/html")
            if di.get("ok"):
                report["text"] = di["text"]
                report["confidence"] = di.get("confidence", 0.0)
            return report

    # ---- prong 2: local_render (escalation for js_required)
    if "local_render" in prongs:
        want_shot = "screenshot_ocr" in prongs
        r = prong_local_render(url, ua, timeout, want_screenshot=want_shot)
        if r.get("ok"):
            html = r.get("html", "")
            flags = detect(html)
            if flags.get("captcha"):
                report["captcha_detected"] = True
                record("local_render", False, "CAPTCHA wall after render — STOPPING (never bypass)")
                report["notes"].append("CAPTCHA detected post-render; reported honestly, not bypassed")
                return report
            best_html, best_bytes = html, html.encode("utf-8")
            if r.get("screenshot"):
                screenshot_bytes = r["screenshot"]
                if out:
                    (out / "page.png").write_bytes(screenshot_bytes)
                    report["screenshot_path"] = str(out / "page.png")
            rendered_ok = bool(html) and not flags.get("js_required")
            record("local_render", rendered_ok, "rendered" if rendered_ok else "rendered but still thin")
            if out and html:
                (out / "rendered.html").write_text(html, encoding="utf-8")
            if rendered_ok and not all_prongs:
                report["prong_succeeded"] = "local_render"
                report["html"] = html
                di = _docintel_extract(best_bytes, "rendered.html", "text/html")
                if di.get("ok"):
                    report["text"] = di["text"]
                    report["confidence"] = di.get("confidence", 0.0)
                return report
        else:
            record("local_render", False, r.get("note", "render unavailable"), r.get("capability_gap"))

    # ---- prong 3: offline_docintel (structure the best HTML we have, fully offline)
    if "offline_docintel" in prongs and best_html:
        di = _docintel_extract(best_bytes or best_html.encode("utf-8"), "page.html", "text/html")
        if di.get("ok"):
            report["text"] = di["text"]
            report["confidence"] = di.get("confidence", 0.0)
            report["artifact"] = {k: di[k] for k in ("parser", "governance_ok", "capability_gaps")
                                  if k in di}
            record("offline_docintel", True, f"extracted {len(di['text'])} chars offline")
            if out:
                (out / "extracted.txt").write_text(di["text"], encoding="utf-8")
            report["html"] = best_html
            if not all_prongs:
                report["prong_succeeded"] = "offline_docintel"
                return report
        else:
            record("offline_docintel", False, di.get("note", "no text recovered"),
                   di.get("capability_gap"))

    # ---- prong 4: screenshot_ocr (offline parse of the rendered pixels)
    if "screenshot_ocr" in prongs:
        if screenshot_bytes is None and _have_module("playwright"):
            # capture a screenshot now if we have not already
            r = prong_local_render(url, ua, timeout, want_screenshot=True)
            screenshot_bytes = r.get("screenshot")
            if screenshot_bytes and out:
                (out / "page.png").write_bytes(screenshot_bytes)
                report["screenshot_path"] = str(out / "page.png")
        if screenshot_bytes:
            di = _docintel_extract(screenshot_bytes, "page.png", "image/png")
            if di.get("ok"):
                report["text"] = di["text"]
                report["confidence"] = di.get("confidence", 0.0)
                record("screenshot_ocr", True, f"OCR recovered {len(di['text'])} chars offline")
                if out:
                    (out / "ocr.txt").write_text(di["text"], encoding="utf-8")
                if not all_prongs:
                    report["prong_succeeded"] = "screenshot_ocr"
                    return report
            else:
                record("screenshot_ocr", False, di.get("note", "OCR recovered no text"),
                       di.get("capability_gap") or "ocr")
        else:
            record("screenshot_ocr", False, "no screenshot (local_render unavailable)", "local_render")

    # ---- prong 5: cloud_render (only if explicitly enabled AND configured)
    if "cloud_render" in prongs and enable_cloud:
        r = prong_cloud_render(url)
        if r.get("ok"):
            report["html"] = r.get("html", report["html"])
            if r.get("text"):
                report["text"] = r["text"]
            record("cloud_render", True, "firecrawl managed render")
            if not all_prongs:
                report["prong_succeeded"] = "cloud_render"
                return report
        else:
            record("cloud_render", False, r.get("note", "cloud render unavailable"),
                   r.get("capability_gap"))
    elif "cloud_render" in prongs:
        record("cloud_render", False, "cloud prong OFF (offline-first; pass enable_cloud=True to allow)")

    # ---- resolve outcome when running first-success and nothing fully succeeded
    if report["prong_succeeded"] == "none":
        if report["text"]:
            report["prong_succeeded"] = "offline_docintel"
        elif report["html"]:
            report["prong_succeeded"] = "partial_html"
            report["notes"].append("recovered raw HTML but no clean text — human review needed")
        else:
            report["notes"].append("all prongs exhausted; content not recovered (honest gap, not faked)")
    return report
