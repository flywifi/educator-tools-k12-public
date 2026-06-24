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


def web_fetch_fetcher(limiter: RateLimiter | None = None, timeout: int = 10, max_retries: int = 3) -> Callable:
    """A traversal Fetcher for `url` seeds (public pages). Honors Retry-After + exponential backoff;
    reports a gap if `requests` is unavailable or the fetch fails — never invents a page."""
    have_requests = importlib.util.find_spec("requests") is not None

    def fetch(seed: Seed) -> FetchResult:
        if not have_requests:
            return FetchResult(gaps=[{"seed_id": seed.seed_id, "reason": "requests_unavailable",
                                      "value": seed.value, "note": "install tools/requirements-scraper.txt"}])
        import requests  # lazy
        if limiter:
            limiter.acquire()
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
