#!/usr/bin/env python3
"""fetch_diag.py — diagnose a fetch: WHY was it blocked, and is there a cleaner structured source?

Two honest, token-free diagnostics for the local acquirer. Both are DETECTION, never evasion — TOS
pulls PUBLIC government/education data openly, so when a site actively blocks automated access we want
to KNOW (and back off / prefer its official data / fall back to Wayback), not spoof a TLS/browser
fingerprint past it (that's the arms race that gets an IP banned — see security/ and CLAUDE.md ethics).

1. classify_block(status, headers, body)  -> which anti-bot vendor + challenge type, from STATIC HTTP
   signatures (response headers, set-cookie names, status, challenge-page markers). Inspired by the
   r/webscraping "antibot-print" idea, but used DEFENSIVELY: feed the result to the rate governor so a
   detected hard block trips the per-host breaker BEFORE repeated hits earn a real lockout.

2. find_data_sources(html, base_url)       -> structured sources already on the page (JSON-LD,
   __NEXT_DATA__/__NUXT__ state, RSS/Atom feeds, /api//wp-json endpoints, sitemap hint). Realizes the
   "you sure there's no API?" advice: prefer parsing structured data over scraping rendered HTML —
   more accurate (nothing inferred/fabricated) and it sidesteps the anti-bot wall entirely.
"""
from __future__ import annotations

import re
import urllib.parse

# vendor -> (header/cookie/server tells, body markers). Static signatures, cross-checked verbatim
# against the MIT-licensed corpus in github.com/mmewni/antibot-detect (the real, current detector;
# the "antibot-print" repo named in the source Reddit thread does not exist — confirmed 404 + 0 search
# hits, so its list was never used). Header tells match by line-start PREFIX (catches cf-*, x-datadome*,
# x-kpsdk-*, etc.). Detection only — used to back off honestly, never to evade.
_VENDORS = [
    ("Cloudflare", {
        "headers": ["cf-ray", "cf-mitigated", "cf-chl-bypass", "cf-cache-status"],
        "server": ["cloudflare"],
        "cookies": ["__cf_bm", "cf_clearance"],
        "body": ["just a moment", "/cdn-cgi/challenge-platform", "attention required",
                 "cf-challenge", "checking if the site connection is secure", "window._cf_chl_opt"],
    }),
    ("DataDome", {
        "headers": ["x-datadome", "x-dd-b"],
        "server": [],
        "cookies": ["datadome"],
        "body": ["geo.captcha-delivery.com", "captcha-delivery.com", "js.datadome.co", "datadome"],
    }),
    ("PerimeterX/HUMAN", {
        "headers": ["x-px"],
        "server": [],
        "cookies": ["_px", "_pxhd", "_pxvid", "_px2", "_px3", "pxcts"],
        "body": ["px-captcha", "client.perimeterx.net", "window._pxappid", "perimeterx", "/api/v1/px/"],
    }),
    ("Akamai Bot Manager", {
        "headers": ["x-akamai", "akamai-"],
        "server": ["akamaighost", "akamai"],
        "cookies": ["_abck", "ak_bmsc", "bm_sz", "bm_sv", "bm_mi", "bm_so"],
        "body": [],
    }),
    ("Imperva/Incapsula", {
        "headers": ["x-iinfo", "x-cdn"],
        "server": ["incapsula"],
        "cookies": ["incap_ses", "visid_incap", "nlbi_", "reese84"],
        "body": ["_incapsula_resource", "incapsula incident", "request unsuccessful"],
    }),
    ("AWS WAF", {
        "headers": ["x-amzn-waf-action"],
        "server": ["awselb"],
        "cookies": ["aws-waf-token"],
        "body": ["token.awswaf.com", "captcha.awswaf.com", "awswaf"],
    }),
    ("Kasada", {
        "headers": ["x-kpsdk"],
        "server": [],
        "cookies": [],
        "body": ["/ips.js", "kpsdk", "kasada"],
    }),
]

_CAPTCHAS = [
    ("hCaptcha", ["hcaptcha.com", "h-captcha", "hcaptcha"]),
    ("reCAPTCHA", ["recaptcha", "g-recaptcha", "google.com/recaptcha"]),
    ("Turnstile", ["cf-turnstile", "challenges.cloudflare.com/turnstile"]),
]


def _blob(headers: dict | None) -> str:
    if not headers:
        return ""
    parts = []
    for k, v in headers.items():
        parts.append(f"{str(k).lower()}: {str(v).lower()}")
    return "\n".join(parts)


def classify_block(status: int | None, headers: dict | None = None, body: str = "") -> dict:
    """Classify a (possibly blocked) response by anti-bot vendor + challenge kind, from static
    signatures. Returns {blocked, vendor, kind, confidence, signals, advice, retry_worthwhile}.
    kind in {challenge, captcha, rate_limit, ip_block, none}."""
    hdr = _blob(headers)
    low = (body or "").lower()[:200_000]
    signals: list[str] = []
    vendor = None

    for name, sig in _VENDORS:
        hits = []
        for h in sig["headers"]:
            if re.search(rf"(?:^|\n){re.escape(h)}", hdr):  # line-start prefix: catches cf-*, x-datadome*, ...
                hits.append(f"header {h}")
        for s in sig["server"]:
            if re.search(rf"server:.*{re.escape(s)}", hdr):
                hits.append(f"server {s}")
        for c in sig["cookies"]:
            if c in hdr:  # set-cookie names appear in the header blob
                hits.append(f"cookie {c}")
        for b in sig["body"]:
            if b in low:
                hits.append(f"body '{b}'")
        if hits:
            vendor = name
            signals = hits
            break

    captcha = None
    for name, marks in _CAPTCHAS:
        if any(m in low for m in marks):
            captcha = name
            signals.append(f"captcha {name}")
            break

    # decide kind + whether retrying the same method is worthwhile
    is_4xx_block = status in (401, 403, 406, 451)
    is_throttle = status in (429, 503)
    challenge_markers = any(s.startswith("body") for s in signals) or captcha
    blocked = bool(vendor or captcha or is_4xx_block or is_throttle)

    if captcha:
        kind, retry = "captcha", False
    elif is_throttle:
        kind, retry = "rate_limit", True            # waiting it out CAN succeed (governor handles backoff)
    elif vendor and challenge_markers:
        kind, retry = "challenge", False            # a JS/interactive wall — a plain GET won't pass
    elif vendor or is_4xx_block:
        kind, retry = "ip_block", False
    else:
        kind, retry = "none", True

    confidence = "high" if (vendor and challenge_markers) or captcha else \
                 "medium" if vendor or is_4xx_block or is_throttle else "low"

    advice = _advice(vendor, kind, captcha)
    return {"blocked": blocked, "vendor": vendor or captcha, "kind": kind,
            "confidence": confidence, "signals": signals[:8], "advice": advice,
            "retry_worthwhile": retry, "status": status}


def _advice(vendor, kind, captcha) -> str:
    if kind == "rate_limit":
        return ("Server is rate-limiting (honor Retry-After; the governor backs off). Slow down — "
                "do NOT add parallelism; that earns a real lockout.")
    if kind == "captcha" or captcha:
        return (f"Interactive {captcha or 'CAPTCHA'} challenge — automated access is not intended. "
                "Prefer the site's official data file / API, or a Wayback snapshot; otherwise mark an "
                "honest gap. Do not attempt to solve/bypass it.")
    if kind == "challenge":
        return (f"{vendor} managed challenge — a plain GET won't pass and hammering risks an IP block. "
                "The real-browser render prong may legitimately load it; otherwise prefer the official "
                "data/API or Wayback, and let the breaker rest the host.")
    if kind == "ip_block":
        return (f"{vendor or 'Server'} is refusing automated requests (no challenge to pass). Back off "
                "(breaker), use the official data source / API or Wayback, and do not retry in a loop.")
    return "No anti-bot block detected."


_FEED_RE = re.compile(
    r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*href=["\']([^"\']+)["\']', re.I)
_FEED_RE2 = re.compile(
    r'<link[^>]+href=["\']([^"\']+)["\'][^>]*type=["\']application/(?:rss|atom)\+xml["\']', re.I)
_JSONLD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>', re.I)
_HREF_RE = re.compile(r'(?:href|src|action)=["\']([^"\']+)["\']', re.I)


def find_data_sources(html: str, base_url: str) -> dict:
    """Spot structured/data sources already exposed by the page, so the acquirer can prefer them over
    scraping rendered HTML. 'Is there an API?' answered automatically. Nothing fetched here — detection
    only; the caller decides what to pull."""
    out = {"json_ld": 0, "embedded_state": [], "feeds": [], "api_endpoints": [], "sitemap": None}
    if not html:
        return out
    out["json_ld"] = len(_JSONLD_RE.findall(html))
    for marker, label in (("__NEXT_DATA__", "Next.js __NEXT_DATA__"),
                          ("__NUXT__", "Nuxt __NUXT__"),
                          ("window.__INITIAL_STATE__", "__INITIAL_STATE__"),
                          ("__APOLLO_STATE__", "Apollo cache")):
        if marker in html:
            out["embedded_state"].append(label)

    feeds = set(_FEED_RE.findall(html)) | set(_FEED_RE2.findall(html))
    out["feeds"] = sorted(urllib.parse.urljoin(base_url, f) for f in feeds)

    eps = set()
    for href in _HREF_RE.findall(html):
        low = href.lower().split("?")[0]
        if any(seg in low for seg in ("/api/", "/wp-json/", "/rest/", "/graphql", "/odata")) \
                or low.endswith((".json", ".geojson")):
            eps.add(urllib.parse.urljoin(base_url, href))
        if low.endswith("/sitemap.xml") or low.endswith("/sitemap_index.xml"):
            out["sitemap"] = urllib.parse.urljoin(base_url, href)
    out["api_endpoints"] = sorted(eps)[:25]
    return out


def summarize(block: dict, sources: dict) -> str:
    bits = []
    if block.get("blocked"):
        bits.append(f"block={block['vendor'] or block['kind']}({block['confidence']})")
    s = []
    if sources.get("json_ld"):
        s.append(f"{sources['json_ld']} JSON-LD")
    if sources.get("embedded_state"):
        s.append("+".join(sources["embedded_state"]))
    if sources.get("feeds"):
        s.append(f"{len(sources['feeds'])} feed(s)")
    if sources.get("api_endpoints"):
        s.append(f"{len(sources['api_endpoints'])} api-ish link(s)")
    if sources.get("sitemap"):
        s.append("sitemap")
    if s:
        bits.append("structured: " + ", ".join(s))
    return "; ".join(bits) or "no block, no structured-source hints"
