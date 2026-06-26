"""feeds — feed self-update engine (L7) (package).

Re-exports the engine API from feeds.py so `import feeds` works when `shared/` is on the path.
The item store (`feed_items.local.db`) is a gitignored, regenerable local artifact — never committed.
The CLI runner lives in `tools/feeds_update.py`. Canonical docs: README.md.
"""
from .feeds import (
    digest,
    due_feeds,
    fetch_and_store,
    load_catalog,
    new_count,
    parse_feed,
    save_catalog,
    store_items,
    update,
)

__all__ = [
    "load_catalog", "save_catalog", "due_feeds", "parse_feed", "fetch_and_store",
    "store_items", "update", "digest", "new_count",
]
