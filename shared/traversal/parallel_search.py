#!/usr/bin/env python3
"""Parallel-search helper — bounded, rate-limited fan-out for external searches/fetches (stdlib core).

Reusable pieces for running many EXTERNAL lookups at once without tripping rate limits:
  - `RateLimiter`  : thread-safe token bucket (smooths bursts; stay below provider limits).
  - `parallel_map` : bounded ThreadPoolExecutor fan-out; a failed item degrades to a gap, never a crash.
  - `web_fetch_fetcher(...)` : a traversal `Fetcher` for `url` seeds (uses `requests` when present, honors
    Retry-After + exponential backoff; gap when `requests` is absent — never fabricates a page).
  - `search_fetcher(search_fn)` : wraps an INJECTED search callable (the host AI's native web search, or a
    configured API) into a `Fetcher` for `query` seeds, emitting findings + `url` seeds for the next layer.

Core (RateLimiter/parallel_map) is dependency-free; live fetching is gated. Plugs into the traversal
engine's parallel scheduler so external searches fan out the same way internal file reads do.
"""
from __future__ import annotations

import importlib.util
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List

from .traversal import FetchResult, Finding, Seed


class RateLimiter:
    """Token bucket: ~`rate` permits/sec with a `burst` ceiling. Thread-safe; blocks until a token frees."""

    def __init__(self, rate_per_sec: float = 5.0, burst: int = 5) -> None:
        self.rate = float(rate_per_sec)
        self.capacity = float(burst)
        self.tokens = float(burst)
        self._ts = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self._ts) * self.rate)
                self._ts = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
            time.sleep(max(wait, 0.001))


def parallel_map(fn: Callable, items: list, max_workers: int = 8, limiter: RateLimiter | None = None) -> list:
    """Run fn over items concurrently (bounded). Returns (item, result, error) triples; one failure is a
    captured error, not a crash (graceful degradation — the rest of the batch still completes)."""
    if not items:
        return []

    def _wrap(item):
        if limiter:
            limiter.acquire()
        try:
            return item, fn(item), None
        except Exception as exc:
            return item, None, f"{exc.__class__.__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as ex:
        return list(ex.map(_wrap, items))


def firecrawl_config() -> dict | None:
    """Auto-detect Firecrawl with NO per-use setup: a SaaS key (`FIRECRAWL_API_KEY`) OR a self-hosted
    base URL (`FIRECRAWL_BASE_URL`, e.g. http://localhost:3002). None when neither is set → callers fall
    back to the polite stdlib path. Configure once at deploy and every crawl uses it automatically."""
    import os
    key, base = os.environ.get("FIRECRAWL_API_KEY"), os.environ.get("FIRECRAWL_BASE_URL")
    if not key and not base:
        return None
    return {"key": key, "base": (base or "https://api.firecrawl.dev").rstrip("/")}


def firecrawl_scrape(url: str, cfg: dict, timeout: int = 30) -> str | None:
    """Scrape a (possibly JS-rendered) page via Firecrawl → markdown. None on failure. Same /v1/scrape
    contract for the SaaS API and a self-hosted instance."""
    if importlib.util.find_spec("requests") is None:
        return None
    import requests
    headers = {"Content-Type": "application/json"}
    if cfg.get("key"):
        headers["Authorization"] = f"Bearer {cfg['key']}"
    try:
        r = requests.post(f"{cfg['base']}/v1/scrape", json={"url": url, "formats": ["markdown"]},
                          headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json().get("data", {}) or {}
        return data.get("markdown") or data.get("content")
    except Exception:
        return None


def web_fetch_fetcher(limiter: RateLimiter | None = None, timeout: int = 10, max_retries: int = 3) -> Callable:
    """A traversal Fetcher for `url` seeds. **Prefers Firecrawl when configured** (handles JS-rendered
    district pages), else a polite `requests` GET (Retry-After + exponential backoff), else an honest
    gap — never invents a page."""
    have_requests = importlib.util.find_spec("requests") is not None
    fc = firecrawl_config()

    def fetch(seed: Seed) -> FetchResult:
        if not have_requests:
            return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "requests_unavailable",
                                      "value": seed.value, "note": "install tools/requirements-scraper.txt"}])
        if limiter:
            limiter.acquire()
        if fc:  # Firecrawl first — JS pages "just work"
            md = firecrawl_scrape(seed.value, fc, timeout=max(timeout, 30))
            if md:
                return FetchResult(findings=[Finding(finding_id=f"{seed.seed_id}:fc",
                    summary=" ".join(md.split())[:600], source="firecrawl", added_by="web_fetch_fetcher",
                    confidence="medium", locator=seed.value, retrieval_state="content_ingested")])
        import requests  # lazy fallback
        delay = 1.0
        for attempt in range(max_retries):
            try:
                r = requests.get(seed.value, timeout=timeout,
                                 headers={"User-Agent": "TOS-traversal/0.1 (+education; polite)"})
                if r.status_code == 429:  # honor the server's own backoff
                    time.sleep(float(r.headers.get("Retry-After", delay)))
                    delay *= 2
                    continue
                r.raise_for_status()
                text = " ".join(r.text.split())[:600]
                return FetchResult(findings=[Finding(
                    finding_id=f"{seed.seed_id}:web", summary=text, source="web", added_by="web_fetch_fetcher",
                    confidence="medium", locator=seed.value, retrieval_state="content_ingested")])
            except Exception as exc:
                if attempt == max_retries - 1:
                    return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "fetch_failed",
                                              "value": seed.value, "detail": f"{exc.__class__.__name__}: {exc}"}])
                time.sleep(delay)
                delay *= 2
        return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "exhausted_retries", "value": seed.value}])

    return fetch


def search_fetcher(search_fn: Callable[[str], List[dict]]) -> Callable:
    """Wrap an INJECTED search callable into a `query`-seed Fetcher. `search_fn(query)` returns a list of
    {title, url, snippet}; we emit a finding per hit + a `url` seed for deepening on the next layer. The
    host AI's native web search, or a configured API, supplies search_fn — we build no search client."""
    def fetch(seed: Seed) -> FetchResult:
        try:
            hits = search_fn(seed.value) or []
        except Exception as exc:
            return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "search_failed",
                                      "value": seed.value, "detail": f"{exc.__class__.__name__}: {exc}"}])
        findings, seeds = [], []
        for i, h in enumerate(hits, 1):
            url = h.get("url", "")
            findings.append(Finding(finding_id=f"{seed.seed_id}:hit:{i}",
                                    summary=(h.get("title", "") + " — " + h.get("snippet", "")).strip(" —"),
                                    source="search", added_by="search_fetcher", confidence="low",
                                    locator=url, retrieval_state="referenced"))
            if url:
                seeds.append(Seed(seed_id=f"{seed.seed_id}:url:{i}", seed_type="url", value=url,
                                  source_hint="search_result", discovered_from=seed.seed_id, confidence="low"))
        return FetchResult(findings=findings, seeds=seeds)

    return fetch


def rss_fetcher(limiter: RateLimiter | None = None) -> Callable:
    """A traversal Fetcher for `feed` seeds (RSS/Atom) — a low-cost prong for 'what changed' on
    authoritative sources. Uses `feedparser` when installed, else a stdlib ElementTree fallback. Emits a
    finding per item + a `url` seed to deepen; honest gap if the feed can't be fetched/parsed."""
    have_requests = importlib.util.find_spec("requests") is not None
    have_fp = importlib.util.find_spec("feedparser") is not None

    def fetch(seed: Seed) -> FetchResult:
        if not have_requests:
            return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "requests_unavailable", "value": seed.value}])
        import requests
        if limiter:
            limiter.acquire()
        try:
            raw = requests.get(seed.value, timeout=15, headers={"User-Agent": "TOS-traversal/0.1 (+education)"}).content
        except Exception as exc:
            return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "feed_fetch_failed",
                                      "value": seed.value, "detail": f"{exc.__class__.__name__}: {exc}"}])
        items = []
        if have_fp:
            import feedparser
            for e in feedparser.parse(raw).entries:
                items.append((getattr(e, "title", ""), getattr(e, "link", ""), getattr(e, "summary", "")))
        else:
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(raw)
            except Exception:
                return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "feed_parse_failed", "value": seed.value}])
            for it in root.iter():
                if it.tag.split("}")[-1] not in ("item", "entry"):
                    continue
                title = link = summary = ""
                for ch in it:
                    ct = ch.tag.split("}")[-1]
                    if ct == "title":
                        title = (ch.text or "").strip()
                    elif ct == "link":
                        link = (ch.get("href") or ch.text or "").strip()
                    elif ct in ("summary", "description"):
                        summary = (ch.text or "").strip()
                items.append((title, link, summary))
        findings, seeds = [], []
        for i, (title, link, summary) in enumerate(items, 1):
            findings.append(Finding(finding_id=f"{seed.seed_id}:item:{i}",
                                    summary=(f"{title} — {summary}").strip(" —")[:300], source="rss",
                                    added_by="rss_fetcher", confidence="low", locator=link, retrieval_state="referenced"))
            if link:
                seeds.append(Seed(seed_id=f"{seed.seed_id}:url:{i}", seed_type="url", value=link,
                                  source_hint="rss_item", discovered_from=seed.seed_id, confidence="low"))
        return FetchResult(findings=findings, seeds=seeds)

    return fetch
