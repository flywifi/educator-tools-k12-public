#!/usr/bin/env python3
"""Resilient multi-prong fetch for ANY hard-to-scrape PUBLIC page.

Fallback prongs are not limited to JS-required pages. They activate whenever there is *any obstacle*
(HTTP error, empty/garbled body, bot gate, rate-limit, encoding issue) OR when retrieval confidence
falls below a configurable threshold (default 0.95). Multiple prongs run and their results are
*aggregated* into a single high-confidence contract. Discrepancies between prongs are documented in
the minority report and appended to ledger/render-discrepancy-log.json for auditing.

Prong chain (executed in DEFAULT_ORDER; stops at confidence_threshold unless all_prongs=True):

  1. http_static      — stdlib/`requests` fetch. Free, no deps.
  2. local_render     — LOCAL Playwright Chromium (pre-installed at /opt/pw-browsers) runs the
                        page's OWN JavaScript and returns the rendered HTML.
  3. offline_docintel — run the best HTML through the docintel pipeline (shared/docintel) for
                        structured, fully offline extraction of text, tables, and links.
  4. screenshot_ocr   — Playwright full-page screenshot → docintel OCR (tesseract). Fully offline
                        pixel-level parse; last resort for canvas/image-only content.
  5. cloud_render     — firecrawl (capability cloud_web_crawl), only if explicitly enabled.

After aggregation: if the web_archive capability is present, the most recent Wayback Machine
snapshot is compared against the current content to confirm whether the page genuinely changed,
was removed, or whether the current fetch is unreliable.

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
import json
import os
import re
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
LEDGER_DISCREPANCY_LOG = ROOT / "ledger" / "render-discrepancy-log.json"

# One honest, identifying UA shared with tools/standards_refresh.py.
HONEST_UA = ("TOS-standards-updater/1.1 (+polite educational-standards update checker; "
             "respects robots.txt)")

CONFIDENCE_THRESHOLD_DEFAULT = 0.95

JS_INDICATORS = ("enable javascript", "javascript is required", "please enable javascript", "<noscript")
CAPTCHA_INDICATORS = ("recaptcha", "hcaptcha", "verify you are human", "prove you are human",
                      "i am not a robot", "captcha")
OBSTACLE_INDICATORS = ("access denied", "403 forbidden", "404 not found", "page not found",
                       "this page is unavailable", "maintenance mode", "503 service unavailable",
                       "temporarily unavailable", "this page has been removed",
                       "content not found", "you do not have permission")

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
    have_wayback = _have_module("waybackpy")
    return {
        "http_static": {"available": True, "needs": "stdlib (requests optional)"},
        "local_render": {"available": have_pw, "needs": "playwright (capability: local_render); "
                         f"Chromium pre-installed at {PW_BROWSERS_PATH}"},
        "offline_docintel": {"available": have_docintel, "needs": "shared/docintel pipeline"},
        "screenshot_ocr": {"available": have_pw and have_ocr,
                           "needs": "playwright (capture) + pytesseract/Pillow/tesseract (capability: ocr)"},
        "cloud_render": {"available": have_cloud,
                         "needs": "firecrawl + FIRECRAWL_API_KEY/BASE_URL (capability: cloud_web_crawl); OFF by default"},
        "web_archive": {"available": have_wayback or True,
                        "needs": "waybackpy (optional; stdlib urllib fallback always available); requires network to archive.org"},
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


def detect(html: str, status: int = 200) -> dict:
    """Detect obstacle and quality flags in a fetched page response.

    Returns a dict of trigger flags. Any truthy flag except 'captcha' suggests running
    additional prongs to improve confidence. 'captcha' STOPS the chain entirely — we never bypass.
    Triggers are not limited to js_required: any obstacle or low-content response escalates.
    """
    low = html.lower() if html else ""
    body_len = len(html.strip()) if html else 0
    return {
        "js_required": any(t in low for t in JS_INDICATORS) or body_len < 500,
        "captcha": any(t in low for t in CAPTCHA_INDICATORS),
        "obstacle": (any(t in low for t in OBSTACLE_INDICATORS) or
                     status in (400, 401, 403, 503)),
        "rate_limited": status == 429,
        "http_error": status not in (200, 203, 206, 301, 302, 304),
        "low_content": body_len < 2000,
    }


# --------------------------------------------------------------------------- confidence scoring
def _score_confidence(html: str, status: int = 200) -> float:
    """Score quality of fetched content (0.0 = no useful content, 1.0 = high confidence).

    Used to decide whether to escalate to additional prongs — regardless of whether js_required
    was detected. Any score below confidence_threshold triggers the fallback chain.
    """
    if status == 429:
        return 0.0
    if status not in (200, 203, 206):
        return 0.1
    if not html:
        return 0.0

    score = 0.5
    body = html.strip()
    body_len = len(body)

    if body_len < 200:
        return 0.0
    if body_len < 1000:
        score -= 0.3
    elif body_len < 5000:
        score -= 0.1
    elif body_len > 20000:
        score += 0.1

    low = body.lower()

    if any(t in low for t in JS_INDICATORS):
        score -= 0.3
    if any(t in low for t in OBSTACLE_INDICATORS):
        score -= 0.3

    # Text-to-tag ratio: lots of tags with little visible text → low quality
    text_only = re.sub(r"<[^>]+>", " ", body)
    ratio = len(text_only.strip()) / body_len if body_len else 0
    if ratio < 0.10:
        score -= 0.2
    elif ratio > 0.40:
        score += 0.1

    # Structural markers indicate real content
    if any(t in low for t in ("<h1", "<h2", "<article", "<main", "<section")):
        score += 0.1

    # Encoding errors
    if body.count("�") > 5:
        score -= 0.1

    return max(0.0, min(1.0, round(score, 3)))


# --------------------------------------------------------------------------- text helpers
def _extract_text_fast(html: str) -> str:
    """Quick plaintext extraction for comparison purposes. Not for final output."""
    if not html:
        return ""
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:5000]


# --------------------------------------------------------------------------- discrepancy log
def _log_discrepancy(entry: dict) -> None:
    """Append a discrepancy entry to ledger/render-discrepancy-log.json (never raises)."""
    if not LEDGER_DISCREPANCY_LOG.parent.exists():
        return
    entry = {"ts": datetime.now(timezone.utc).isoformat(), **entry}
    try:
        existing = json.loads(LEDGER_DISCREPANCY_LOG.read_text()) if LEDGER_DISCREPANCY_LOG.exists() else []
        existing.append(entry)
        LEDGER_DISCREPANCY_LOG.write_text(json.dumps(existing, indent=2))
    except Exception:
        pass  # logging must never crash the main flow


# --------------------------------------------------------------------------- aggregation
def _aggregate_results(prong_results: list[dict], url: str) -> dict:
    """Merge multiple prong results into a single high-confidence handoff contract.

    Compares text content across prongs using token overlap. When prongs disagree significantly
    (overlap < 0.70), sets minority_report: True and logs the discrepancy to the audit ledger.
    Returns the best-quality result with a cross-prong confidence bonus applied.
    """
    import difflib

    successful = [r for r in prong_results if r.get("ok") and (r.get("text") or r.get("html"))]
    if not successful:
        return {"html": "", "text": "", "confidence": 0.0, "minority_report": False,
                "source_prong": "none", "prongs_aggregated": []}

    if len(successful) == 1:
        r = successful[0]
        return {
            "html": r.get("html", ""),
            "text": r.get("text", "") or _extract_text_fast(r.get("html", "")),
            "confidence": r.get("confidence", 0.5),
            "minority_report": False,
            "source_prong": r.get("prong_name", "unknown"),
            "prongs_aggregated": [r.get("prong_name", "unknown")],
        }

    # Pairwise text comparison (compare first two successful prongs)
    texts = [(r.get("prong_name", "?"),
              r.get("text", "") or _extract_text_fast(r.get("html", "")))
             for r in successful]

    minority_report = False
    cross_confidence_bonus = 0.0

    a_name, a_text = texts[0]
    b_name, b_text = texts[1]
    ratio = difflib.SequenceMatcher(None, a_text[:3000].lower(), b_text[:3000].lower()).ratio()

    if ratio >= 0.80:
        cross_confidence_bonus = 0.20
    elif ratio >= 0.60:
        cross_confidence_bonus = 0.10
    else:
        minority_report = True
        _log_discrepancy({
            "url": url,
            "field": "body_text",
            "prong_a": a_name,
            "prong_b": b_name,
            "value_a_snippet": a_text[:300],
            "value_b_snippet": b_text[:300],
            "overlap_ratio": round(ratio, 3),
            "confidence_delta": round(
                abs(successful[0].get("confidence", 0.0) - successful[1].get("confidence", 0.0)), 3),
        })

    # Pick the best: highest combined score of text length + individual confidence
    best = max(successful, key=lambda r: (
        len(r.get("text", "") or _extract_text_fast(r.get("html", ""))) * 0.5
        + r.get("confidence", 0.0) * 500
    ))

    return {
        "html": best.get("html", ""),
        "text": best.get("text", "") or _extract_text_fast(best.get("html", "")),
        "confidence": min(1.0, round(best.get("confidence", 0.5) + cross_confidence_bonus, 3)),
        "minority_report": minority_report,
        "source_prong": best.get("prong_name", "aggregated"),
        "prongs_aggregated": [r.get("prong_name", "?") for r in successful],
        "cross_prong_overlap": round(ratio, 3),
    }


# --------------------------------------------------------------------------- archive comparison
def _wayback_compare(url: str, current_html: str) -> dict:
    """Compare current content against the most recent Wayback Machine snapshot.

    Uses the archive.org CDX API (no authentication required). Degrades gracefully when
    network is unavailable. Helps confirm whether a page genuinely changed, was removed,
    or whether the current fetch is unreliable (transient failure).
    """
    base = {"available": False, "archived_at": None, "overlap_score": None,
            "page_removed": False, "changed": None, "stable": None}
    try:
        cdx_url = (
            "https://web.archive.org/cdx/search/cdx"
            f"?url={urllib.parse.quote(url, safe='')}"
            "&output=json&limit=1&fl=timestamp,statuscode"
            "&filter=statuscode:200&fastLatest=true"
        )
        req = urllib.request.Request(cdx_url, headers={"User-Agent": HONEST_UA})
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            data = json.loads(resp.read())
    except Exception as e:
        base["note"] = f"wayback CDX unavailable: {e}"
        return base

    # CDX returns [[header], [row], ...]; len 1 means no rows
    if not data or len(data) < 2:
        return {**base, "available": True, "note": "no archived snapshots found for this URL"}

    row = data[1]  # first data row (data[0] is the field-name header)
    ts = row[0]
    archived_at = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:14]}Z"

    try:
        wb_url = f"https://web.archive.org/web/{ts}/{url}"
        req2 = urllib.request.Request(wb_url, headers={"User-Agent": HONEST_UA})
        with urllib.request.urlopen(req2, timeout=20) as resp2:  # nosec B310
            archived_html = resp2.read().decode("utf-8", "replace")
    except Exception as e:
        return {**base, "available": True, "archived_at": archived_at,
                "note": f"could not fetch archived version: {e}"}

    def _word_set(h: str) -> set:
        return set(re.sub(r"<[^>]+>|\s+", " ", h.lower()).split())

    cur_words = _word_set(current_html or "")
    arc_words = _word_set(archived_html)
    if not cur_words and not arc_words:
        overlap = 1.0
    elif not cur_words or not arc_words:
        overlap = 0.0
    else:
        overlap = len(cur_words & arc_words) / max(len(cur_words), len(arc_words))

    page_removed = (not current_html or len(current_html.strip()) < 300) and bool(archived_html)
    changed = overlap < 0.70
    stable = overlap >= 0.85

    return {
        "available": True,
        "archived_at": archived_at,
        "overlap_score": round(overlap, 3),
        "page_removed": page_removed,
        "changed": changed,
        "stable": stable,
        "note": f"compared against snapshot from {archived_at}",
    }


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
            page = browser.new_page(user_agent=ua, locale="en-US")
            try:
                page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            except Exception:
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
    """Run the docintel pipeline offline; return extracted text + confidence + governance summary."""
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
                    confidence_threshold: float = CONFIDENCE_THRESHOLD_DEFAULT,
                    out_dir: Optional[str] = None, timeout: float = 30.0, ua: str = HONEST_UA,
                    respect_robots: bool = True, enable_cloud: bool = False) -> dict:
    """Try the redundancy prong chain, aggregating results into a single high-confidence contract.

    Fallback prongs activate on ANY obstacle (HTTP error, bot gate, encoding issue, rate-limit)
    OR when confidence < confidence_threshold (default 0.95) — not only on js_required pages.
    When multiple prongs succeed, results are aggregated and discrepancies are logged to
    ledger/render-discrepancy-log.json with minority_report: True.

    After aggregation, if network is available the Wayback Machine CDX API is queried to confirm
    whether the page genuinely changed vs. the archived snapshot.

    CAPTCHA detection STOPS the chain entirely — we never bypass access controls.
    Robots.txt disallow STOPS the chain — we always respect crawl policies.
    """
    prong_order = prongs or DEFAULT_ORDER
    report = {
        "tool": "render_prongs.resilient_fetch",
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "prong_order": prong_order,
        "prongs_attempted": [],
        "prong_succeeded": "none",
        "trigger_reasons": [],
        "html": "", "text": "", "screenshot_path": None, "artifact": None,
        "confidence": 0.0,
        "confidence_threshold": confidence_threshold,
        "capability_gaps": [],
        "captcha_detected": False,
        "minority_report": False,
        "wayback_compare": None,
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
    prong_results: list[dict] = []  # accumulate for aggregation

    def record(name: str, ok: bool, note: str = "", gap: Optional[str] = None) -> None:
        entry: dict = {"prong": name, "ok": ok}
        if note:
            entry["note"] = note
        if gap:
            entry["capability_gap"] = gap
            if gap not in report["capability_gaps"]:
                report["capability_gaps"].append(gap)
        report["prongs_attempted"].append(entry)

    def _captcha_stop(prong_name: str, note: str) -> dict:
        report["captcha_detected"] = True
        record(prong_name, False, note)
        report["notes"].append(note)
        return report

    # ---- prong 1: http_static
    if "http_static" in prong_order:
        r = prong_http_static(url, ua, timeout)
        status = r.get("status", 0)
        html = r.get("html", "")
        flags = detect(html, status)

        if html:
            best_html, best_bytes = html, r.get("bytes", b"")

        if flags.get("captcha"):
            return _captcha_stop("http_static", "CAPTCHA wall detected — STOPPING (we never bypass CAPTCHAs)")

        conf = _score_confidence(html, status)
        prong_results.append({"prong_name": "http_static", "ok": r.get("ok", False),
                               "html": html, "text": "", "confidence": conf})

        needs_more = (
            not r.get("ok") or
            flags.get("js_required") or
            flags.get("obstacle") or
            flags.get("rate_limited") or
            flags.get("http_error") or
            conf < confidence_threshold
        )

        if flags.get("js_required"):
            report["trigger_reasons"].append("js_required")
        if flags.get("obstacle"):
            report["trigger_reasons"].append("obstacle_detected")
        if flags.get("rate_limited"):
            report["trigger_reasons"].append("rate_limited")
        if flags.get("http_error"):
            report["trigger_reasons"].append(f"http_error_{status}")
        if conf < confidence_threshold and r.get("ok"):
            report["trigger_reasons"].append(f"low_confidence_{conf:.2f}")

        record("http_static", not needs_more,
               "ok" if not needs_more else
               f"escalating (conf={conf:.2f}, triggers={','.join(report['trigger_reasons']) or 'none'})")

        if not needs_more and not all_prongs:
            report["prong_succeeded"] = "http_static"
            report["html"] = html
            report["confidence"] = conf
            di = _docintel_extract(best_bytes or html.encode("utf-8"), "page.html", "text/html")
            if di.get("ok"):
                report["text"] = di["text"]
                report["confidence"] = di.get("confidence", conf)
            if out:
                (out / "page.html").write_text(html, encoding="utf-8")
            # still run wayback compare to confirm page stability
            report["wayback_compare"] = _wayback_compare(url, html)
            return report

    # ---- prong 2: local_render (JS SPA pages, or escalated from low-confidence http_static)
    if "local_render" in prong_order:
        want_shot = "screenshot_ocr" in prong_order
        r = prong_local_render(url, ua, timeout, want_screenshot=want_shot)
        if r.get("ok"):
            html = r.get("html", "")
            flags = detect(html)
            if flags.get("captcha"):
                return _captcha_stop("local_render", "CAPTCHA wall after render — STOPPING (never bypass)")
            best_html, best_bytes = html, html.encode("utf-8")
            conf = _score_confidence(html)
            if r.get("screenshot"):
                screenshot_bytes = r["screenshot"]
                if out:
                    (out / "page.png").write_bytes(screenshot_bytes)
                    report["screenshot_path"] = str(out / "page.png")
            rendered_ok = bool(html) and not flags.get("js_required")
            prong_results.append({"prong_name": "local_render", "ok": rendered_ok,
                                   "html": html, "text": "", "confidence": conf})
            record("local_render", rendered_ok, "rendered" if rendered_ok else "rendered but still thin")
            if out and html:
                (out / "rendered.html").write_text(html, encoding="utf-8")
            if rendered_ok and conf >= confidence_threshold and not all_prongs:
                report["prong_succeeded"] = "local_render"
                report["html"] = html
                di = _docintel_extract(best_bytes, "rendered.html", "text/html")
                if di.get("ok"):
                    report["text"] = di["text"]
                    report["confidence"] = di.get("confidence", conf)
                report["wayback_compare"] = _wayback_compare(url, html)
                return report
        else:
            record("local_render", False, r.get("note", "render unavailable"), r.get("capability_gap"))

    # ---- prong 3: offline_docintel (structure the best HTML we have, fully offline)
    if "offline_docintel" in prong_order and best_html:
        di = _docintel_extract(best_bytes or best_html.encode("utf-8"), "page.html", "text/html")
        if di.get("ok"):
            conf = di.get("confidence", 0.5)
            prong_results.append({"prong_name": "offline_docintel", "ok": True,
                                   "html": best_html, "text": di["text"], "confidence": conf})
            report["artifact"] = {k: di[k] for k in ("parser", "governance_ok", "capability_gaps")
                                  if k in di}
            record("offline_docintel", True, f"extracted {len(di['text'])} chars offline")
            if out:
                (out / "extracted.txt").write_text(di["text"], encoding="utf-8")
            if not all_prongs and conf >= confidence_threshold:
                report["html"] = best_html
                report["text"] = di["text"]
                report["confidence"] = conf
                report["prong_succeeded"] = "offline_docintel"
                report["wayback_compare"] = _wayback_compare(url, best_html)
                return report
        else:
            record("offline_docintel", False, di.get("note", "no text recovered"),
                   di.get("capability_gap"))

    # ---- prong 4: screenshot_ocr (offline parse of the rendered pixels)
    if "screenshot_ocr" in prong_order:
        if screenshot_bytes is None and _have_module("playwright"):
            r = prong_local_render(url, ua, timeout, want_screenshot=True)
            screenshot_bytes = r.get("screenshot")
            if screenshot_bytes and out:
                (out / "page.png").write_bytes(screenshot_bytes)
                report["screenshot_path"] = str(out / "page.png")
        if screenshot_bytes:
            di = _docintel_extract(screenshot_bytes, "page.png", "image/png")
            if di.get("ok"):
                conf = di.get("confidence", 0.5)
                prong_results.append({"prong_name": "screenshot_ocr", "ok": True,
                                       "html": "", "text": di["text"], "confidence": conf})
                record("screenshot_ocr", True, f"OCR recovered {len(di['text'])} chars offline")
                if out:
                    (out / "ocr.txt").write_text(di["text"], encoding="utf-8")
                if not all_prongs:
                    report["prong_succeeded"] = "screenshot_ocr"
                    report["text"] = di["text"]
                    report["confidence"] = conf
                    report["wayback_compare"] = _wayback_compare(url, best_html)
                    return report
            else:
                record("screenshot_ocr", False, di.get("note", "OCR recovered no text"),
                       di.get("capability_gap") or "ocr")
        else:
            record("screenshot_ocr", False, "no screenshot (local_render unavailable)", "local_render")

    # ---- prong 5: cloud_render (only if explicitly enabled AND configured)
    if "cloud_render" in prong_order and enable_cloud:
        r = prong_cloud_render(url)
        if r.get("ok"):
            html = r.get("html", "")
            text = r.get("text", "")
            conf = _score_confidence(html) if html else (0.7 if text else 0.0)
            prong_results.append({"prong_name": "cloud_render", "ok": True,
                                   "html": html, "text": text, "confidence": conf})
            record("cloud_render", True, "firecrawl managed render")
            if not all_prongs:
                report["html"] = html or report["html"]
                report["text"] = text or report["text"]
                report["confidence"] = conf
                report["prong_succeeded"] = "cloud_render"
                report["wayback_compare"] = _wayback_compare(url, html or best_html)
                return report
        else:
            record("cloud_render", False, r.get("note", "cloud render unavailable"),
                   r.get("capability_gap"))
    elif "cloud_render" in prong_order:
        record("cloud_render", False, "cloud prong OFF (offline-first; pass enable_cloud=True to allow)")

    # ---- final: aggregate all successful prong results into a single contract
    if prong_results:
        agg = _aggregate_results(prong_results, url)
        report["html"] = agg.get("html", best_html)
        report["text"] = agg.get("text", "")
        report["confidence"] = agg.get("confidence", 0.0)
        report["minority_report"] = agg.get("minority_report", False)
        report["notes"].append(
            f"aggregated {len(prong_results)} prong(s): {agg.get('prongs_aggregated', [])}")
        if agg.get("minority_report"):
            report["notes"].append(
                "minority_report: prong discrepancy logged to ledger/render-discrepancy-log.json")
        if report["text"] or report["html"]:
            report["prong_succeeded"] = agg.get("source_prong", "aggregated")
        elif best_html:
            report["prong_succeeded"] = "partial_html"
            report["html"] = best_html
            report["notes"].append("recovered raw HTML but no clean text — human review needed")
        else:
            report["notes"].append("all prongs exhausted; content not recovered (honest gap, not faked)")
    else:
        report["notes"].append("all prongs exhausted; content not recovered (honest gap, not faked)")

    report["wayback_compare"] = _wayback_compare(url, report.get("html", "") or best_html)
    return report
