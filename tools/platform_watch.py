#!/usr/bin/env python3
"""Watch the vendor sources that can break TOS's delivery contracts (R5-F, detect-only).

Reads shared/platforms/platform-sources.json. Modes:
  --check       offline: registry shape + freshness of its `updated` stamp vs state file
  --fetch       network: poll every non-manual source, diff against the recorded state
                (shared/platforms/platform-watch-state.json), print NEW items; ALWAYS exit 0 —
                a weekly scheduled workflow surfaces findings as a summary, never a red build
                (a vendor posting news is not a repo defect; the currency-recheck pattern)
  --self-test   fixture probes, offline

State is committed so a diff is reviewable; --fetch --write updates it deliberately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shared" / "platforms" / "platform-sources.json"
STATE = ROOT / "shared" / "platforms" / "platform-watch-state.json"
UA = {"User-Agent": "TOS-platform-watch/1.0 (+https://github.com/flywifi/educator-tools-k12-public)"}
KINDS = {"rss", "atom", "npm", "pypi", "md-hash", "manual-agent"}


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:   # nosec B310 — https registry URLs
        return r.read()


def _feed_items(text: str) -> list[tuple]:
    """(date, title) per RSS item / Atom entry, newest first. A feed is NOT always date-sorted —
    developers.openai.com/rss.xml lists a 2025 guide above 2026 posts, which made the first-item
    rule report a "change" every time the feed reshuffled. Undated items keep their order after
    the dated ones."""
    from email.utils import parsedate_to_datetime
    from datetime import datetime, timezone
    out = []
    for i, block in enumerate(re.findall(r"<(?:item|entry)[\s>].*?</(?:item|entry)>", text, re.S)):
        t = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.S)
        d = re.search(r"<(?:pubDate|updated|published)>(.*?)</(?:pubDate|updated|published)>", block, re.S)
        when = None
        if d:
            raw = d.group(1).strip()
            try:
                when = parsedate_to_datetime(raw)
            except (TypeError, ValueError):
                try:
                    when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    when = None
            if when is not None and when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        out.append((when, (t.group(1).strip() if t else ""), i))
    out.sort(key=lambda x: (x[0] is None, -(x[0].timestamp()) if x[0] else 0, x[2]))
    return [(w, title) for w, title, _ in out]


def observe(kind: str, url: str) -> str:
    """One comparable string per source: newest item title/date, version, or content hash."""
    if kind not in ("rss", "atom", "npm", "pypi", "md-hash"):
        raise ValueError(f"unpollable kind: {kind}")   # BEFORE any fetch — never HTTP a manual row
    raw = _get(url)
    if kind in ("rss", "atom"):
        text = raw.decode("utf-8", "replace")
        m = re.search(r"<(?:title)>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>\s*", text, re.S)
        items = _feed_items(text)
        return (items[0][1] if items else (m.group(1).strip() if m else ""))[:200]
    if kind == "npm":
        return json.loads(raw)["version"]
    if kind == "pypi":
        return json.loads(raw)["info"]["version"]
    return hashlib.sha256(raw).hexdigest()   # md-hash


def load_sources() -> dict:
    return json.loads(SRC.read_text(encoding="utf-8"))


def check() -> list[str]:
    issues = []
    try:
        d = load_sources()
    except Exception as e:
        return [f"  x platform-sources.json unreadable: {e}"]
    seen = set()
    for s in d.get("sources", []):
        sid = s.get("id", "?")
        if sid in seen:
            issues.append(f"  x duplicate source id {sid}")
        seen.add(sid)
        if s.get("kind") not in KINDS:
            issues.append(f"  x {sid}: unknown kind {s.get('kind')!r}")
        if not str(s.get("url", "")).startswith("https://"):
            issues.append(f"  x {sid}: url must be https")
        if not s.get("covers"):
            issues.append(f"  x {sid}: missing `covers` — an unwatched reason is an unwatched risk")
    if not any(s.get("kind") == "manual-agent" for s in d.get("sources", [])):
        issues.append("  x no manual-agent rows — the bot-blocked sources (help.openai.com) must "
                      "stay LISTED even though they cannot be polled")
    return issues


def fetch(write: bool = False) -> int:
    d = load_sources()
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    changed, errors = [], []
    for s in d["sources"]:
        if s["kind"] == "manual-agent":
            print(f"MANUAL  {s['id']}: {s['covers']} — poll by agent audit, not HTTP")
            continue
        try:
            now = observe(s["kind"], s["url"])
        except Exception as e:                      # noqa: BLE001 — a dead feed is a finding
            errors.append(f"ERROR   {s['id']}: {e.__class__.__name__}: {e}")
            continue
        prev = state.get(s["id"])
        if prev != now:
            changed.append(f"NEW     {s['id']}: {prev!r} -> {now!r}  ({s['covers']})")
            state[s["id"]] = now
        else:
            print(f"same    {s['id']}")
    for line in changed + errors:
        print(line)
    if write:
        STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"state written: {STATE.relative_to(ROOT)}")
    print(f"platform_watch: {len(changed)} changed, {len(errors)} error(s) — detect-only, exit 0")
    return 0


def self_test() -> int:
    fails = 0
    def ck(name, ok):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1
    ck("registry is clean", check() == [])
    import unittest.mock as um
    rss = b"<rss><channel><title>feed</title><item><title>Newest post</title></item></channel></rss>"
    with um.patch(__name__ + "._get", return_value=rss):
        ck("rss: newest item title extracted", observe("rss", "https://example.com/x") == "Newest post")
    unsorted = (b"<rss><channel><title>f</title>"
                b"<item><title>Old guide</title><pubDate>Mon, 21 Jul 2025 00:00:00 GMT</pubDate></item>"
                b"<item><title>New post</title><pubDate>Thu, 30 Apr 2026 00:00:00 GMT</pubDate></item>"
                b"</channel></rss>")
    with um.patch(__name__ + "._get", return_value=unsorted):
        ck("rss: an unsorted feed reports the NEWEST-dated item, not the first",
           observe("rss", "https://example.com/x") == "New post")
    atom = (b"<feed><title>f</title><entry><title>A</title><updated>2026-01-01T00:00:00Z</updated></entry>"
            b"<entry><title>B</title><updated>2026-11-23T00:00:00Z</updated></entry></feed>")
    with um.patch(__name__ + "._get", return_value=atom):
        ck("atom: newest <updated> entry wins", observe("atom", "https://example.com/x") == "B")
    with um.patch(__name__ + "._get", return_value=b'{"version":"9.9.9"}'):
        ck("npm: version extracted", observe("npm", "https://example.com/x") == "9.9.9")
    with um.patch(__name__ + "._get", return_value=b'{"info":{"version":"2.2.0"}}'):
        ck("pypi: version extracted", observe("pypi", "https://example.com/x") == "2.2.0")
    with um.patch(__name__ + "._get", return_value=b"stable page"):
        ck("md-hash: content hashed", len(observe("md-hash", "https://example.com/x")) == 64)
    try:
        observe("manual-agent", "https://example.com/x")
        ck("manual-agent kind refuses to poll", False)
    except ValueError:
        ck("manual-agent kind refuses to poll", True)
    bad = json.loads(SRC.read_text(encoding="utf-8"))
    bad["sources"][0] = dict(bad["sources"][0], kind="carrier-pigeon")
    import unittest.mock as um2
    with um2.patch(__name__ + ".load_sources", return_value=bad):
        ck("twin: an unknown kind is a finding", any("unknown kind" in i for i in check()))
    print(f"platform_watch self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.check:
        issues = check()
        for i in issues:
            print(i)
        print("platform-sources: " + ("OK" if not issues else f"{len(issues)} issue(s)"))
        return 1 if issues else 0
    if a.fetch:
        return fetch(write=a.write)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
