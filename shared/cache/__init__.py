"""cache — Local-First standards cache (L1) engine (package).

Re-exports the cache API from cache.py so `import cache` works when `shared/` is on
the path. The on-disk index (`index.local.db`) is a regenerable, gitignored build
artifact — never committed; rebuild with `cache.py --build`.
Canonical docs: README.md.
"""
from .cache import (
    build,
    query,
    stats,
    verify,
)

__all__ = ["build", "query", "stats", "verify"]
