"""Traversal + evidence-accumulation engine (Area 2). See traversal.py and traversal-model.md."""
from .traversal import (
    DEFAULT_MAX_LAYERS, RETRIEVAL_STATES, FetchResult, Finding, Seed, TraversalState,
    docintel_file_fetcher, route_handoff, run_traversal, to_envelope,
)

__all__ = [
    "Seed", "Finding", "FetchResult", "TraversalState", "run_traversal", "to_envelope",
    "docintel_file_fetcher", "route_handoff", "RETRIEVAL_STATES", "DEFAULT_MAX_LAYERS",
]
