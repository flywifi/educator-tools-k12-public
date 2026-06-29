"""Traversal + evidence-accumulation engine (Area 2). See traversal.py and traversal-model.md."""
from .parallel_search import (
    RateLimiter, firecrawl_config, firecrawl_scrape, parallel_map, rss_fetcher, search_fetcher,
    web_fetch_fetcher,
)
from .traversal import (
    DEFAULT_MAX_LAYERS, RETRIEVAL_STATES, FetchResult, Finding, Seed, TraversalState,
    docintel_file_fetcher, route_handoff, run_traversal, to_envelope,
)

__all__ = [
    "Seed", "Finding", "FetchResult", "TraversalState", "run_traversal", "to_envelope",
    "docintel_file_fetcher", "route_handoff", "RETRIEVAL_STATES", "DEFAULT_MAX_LAYERS",
    "RateLimiter", "parallel_map", "web_fetch_fetcher", "search_fetcher", "rss_fetcher",
    "firecrawl_config", "firecrawl_scrape",
]
