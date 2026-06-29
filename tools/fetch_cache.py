#!/usr/bin/env python3
"""fetch_cache.py — incremental / conditional fetch state, so the harvester only pulls what CHANGED.

Re-running the acquirer shouldn't re-download files that haven't changed: that wastes bandwidth and,
more importantly here, spends requests against a host's budget for nothing (every avoidable request is
extra lockout risk). This stores per-URL HTTP validators + a content hash and lets the caller do a
CONDITIONAL GET:

  * If-None-Match / If-Modified-Since  -> the server answers 304 Not Modified (no body re-sent) when
    the resource is unchanged. Cheapest possible "is this new?" check.
  * sha256(content)                    -> catches "changed status to 200 but body is byte-identical"
    (servers that ignore conditional headers), so we still skip re-writing unchanged data.

Realizes the r/webscraping advice: "compare the updated date / hash, only scrape the link if it
changed." State lives in .harvest-cache/fetch_state.json (gitignored), so it persists across runs.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


def _root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(6):
        if (p / "tools" / "sync_check.py").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return Path(__file__).resolve().parent.parent


class FetchCache:
    def __init__(self, persist: bool = True):
        self._path = (_root() / ".harvest-cache" / "fetch_state.json") if persist else None
        self._state: dict[str, dict] = {}
        self.hits = 0      # unchanged (304 or identical hash) -> skipped a re-download
        self.misses = 0    # new or changed -> fetched
        if self._path and self._path.exists():
            try:
                self._state = json.loads(self._path.read_text(encoding="utf-8")).get("urls", {})
            except Exception:
                self._state = {}

    def validators(self, url: str) -> dict:
        """Conditional-GET request headers for this url (empty if we've never seen it)."""
        rec = self._state.get(url)
        if not rec:
            return {}
        h = {}
        if rec.get("etag"):
            h["If-None-Match"] = rec["etag"]
        if rec.get("last_modified"):
            h["If-Modified-Since"] = rec["last_modified"]
        return h

    def unchanged_body(self, url: str, body: bytes) -> bool:
        """True if this exact content was already fetched before (byte-identical)."""
        rec = self._state.get(url)
        return bool(rec and body and rec.get("sha256") == hashlib.sha256(body).hexdigest())

    def note_unchanged(self, url: str) -> None:
        self.hits += 1
        rec = self._state.setdefault(url, {})
        rec["last_checked"] = int(time.time())

    def update(self, url: str, resp_headers: dict | None, body: bytes) -> bool:
        """Record validators + content hash after a real (200) fetch. Returns True if the content is
        NEW or CHANGED vs what we had (caller should write it), False if byte-identical (skip write)."""
        h = {str(k).lower(): v for k, v in (resp_headers or {}).items()}
        digest = hashlib.sha256(body).hexdigest() if body else ""
        prev = self._state.get(url, {})
        changed = digest != prev.get("sha256")
        self._state[url] = {"etag": h.get("etag"), "last_modified": h.get("last-modified"),
                            "sha256": digest, "bytes": len(body or b""),
                            "last_checked": int(time.time())}
        if changed:
            self.misses += 1
        else:
            self.hits += 1
        return changed

    def save(self) -> None:
        if not self._path:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"updated": int(time.time()), "urls": self._state},
                                             indent=2), encoding="utf-8")
        except Exception:
            pass

    def summary(self) -> dict:
        return {"unchanged_skipped": self.hits, "new_or_changed": self.misses,
                "known_urls": len(self._state)}
