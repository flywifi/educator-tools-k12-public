#!/usr/bin/env python3
"""Turn an `unverified` URL in tools/url-provenance.json into a DATED OBSERVATION.

Why this exists. Seven OCPS URLs were registered on 2026-06-28 with the note "GUESSED …
Unconfirmed. Verify before relying on it." Nothing verified them in the seven weeks since, because
the build environment was believed to have no egress. The status vocabulary anticipated this — it
says an unverified URL "must be confirmed and re-statused before anything relies on it" — and no
tool ever existed to do the confirming, so "unverified" decayed into permanent unknown.

What it does NOT do:
  - It never promotes a URL it did not actually fetch.
  - It never deletes a record. A 404 becomes a dead STATUS with the date it was observed, because
    the fact that we once believed a URL existed is itself provenance.
  - It changes nothing but provenance metadata. No corpus, no standards, no overlay.
  - `--check` and `--offline` make ZERO network requests, so CI stays offline.

Politeness: robots.txt is fetched and parsed per host and a disallow is obeyed (recorded as
`skipped_robots`, never silently skipped); Crawl-delay is honoured (OCPS asks 5s); the User-Agent
is honest and identifies the project; one request per URL, no retries, no crawling — only the exact
registered URLs are fetched.

Usage:
  python3 tools/verify_urls.py --check      # report what WOULD be fetched; no network
  python3 tools/verify_urls.py --dry-run    # fetch and print findings; write nothing
  python3 tools/verify_urls.py --write      # fetch and record observations into url-provenance.json
  python3 tools/verify_urls.py --self-test  # offline probes of the promotion table
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROV = ROOT / "tools" / "url-provenance.json"

UA = ("TOS-verify-urls/1.0 (+educator-tools-k12; K-12 standards-reference link verification; "
      "one request per registered URL, robots-respecting)")
TIMEOUT = 25
DEFAULT_DELAY = 2.0

#: Statuses this tool is willing to look at. Everything else is already settled.
CANDIDATE_STATUSES = {"unverified", "exists_bot_blocked"}

#: Words that carry no evidence when they appear in a <title>. A title made only of these
#: corroborates nothing — it is the generic site chrome you get after a redirect to a landing page.
STOPWORDS = {"the", "a", "an", "of", "and", "for", "to", "in", "on", "at", "home", "page",
             "welcome", "site", "official", "website", "school", "schools", "public", "county",
             "district", "orange", "ocps", "florida", "fldoe", "department", "departments"}


def _tokens(text: str) -> set:
    return {w for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(w) > 2}


def path_tokens(url: str) -> set:
    """Meaningful words from a URL's path — what a corroborating title should echo."""
    path = urllib.parse.urlsplit(url).path
    return _tokens(path.replace("_", " ").replace("-", " ")) - STOPWORDS


def title_of(html: str):
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    if not m:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() or None


def classify(url: str, code, title, error=None, prior=None) -> tuple:
    """The promotion table. Returns (status, reason).

    Corroboration is deliberately strict: HTTP 200 alone is NOT evidence that a GUESSED path is the
    page we meant, because a CMS commonly answers an unknown path with its landing page. The title
    must echo a meaningful word from the path. /departments/gifted returning a bare "Departments"
    stays unverified — which is the case this rule exists for.

    And a 403 CONFIRMS an existing `exists_bot_blocked`; it never creates one. www.fldoe.org 403s
    every path including its own robots.txt, so a 403 there cannot distinguish "the page exists but
    blocks scripts" from "the page does not exist and the host refuses everyone". Promoting on a 403
    would have upgraded a URL whose own note says FABRICATED … does not exist into a record
    asserting the page is real — inventing evidence out of a blanket refusal."""
    if error == "robots":
        return "skipped_robots", "robots.txt disallows this path for our user-agent"
    if code is None:
        return "unreachable", f"no HTTP response ({error})"
    if code == 403:
        if prior == "exists_bot_blocked":
            return "exists_bot_blocked", "HTTP 403 — confirms the recorded bot-blocked status"
        return "unverified", ("HTTP 403 — the host refuses scripted clients, which is NOT evidence "
                              "the path exists; this host 403s unknown paths identically")
    if code == 404:
        return "dead_confirmed", "HTTP 404 — the host says this path does not exist"
    if code >= 400:
        return "unverified", f"HTTP {code} — not an answer we can promote on"
    if code != 200:
        return "unverified", f"HTTP {code}"
    want = path_tokens(url)
    got = _tokens(title or "")
    if not title:
        return "unverified", "HTTP 200 but no <title> to corroborate the path"
    if want & got:
        return "verified", f"HTTP 200 and the title echoes the path ({sorted(want & got)})"
    return "unverified", (f"HTTP 200 but the title does not corroborate the path — generic or "
                          f"redirected landing page (title: {title!r})")


class Fetcher:
    """One polite request per URL. Robots parsed once per host; Crawl-delay obeyed."""

    def __init__(self):
        self._robots, self._delay, self._last = {}, {}, {}

    def _robots_for(self, url: str):
        host = urllib.parse.urlsplit(url)[:2]
        key = urllib.parse.urlunsplit(host + ("", "", ""))
        if key in self._robots:
            return self._robots[key]
        rp, delay = urllib.robotparser.RobotFileParser(), DEFAULT_DELAY
        try:
            req = urllib.request.Request(key + "/robots.txt", headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=TIMEOUT).read().decode("utf-8", "replace")
            rp.parse(body.splitlines())
            for line in body.splitlines():
                if line.lower().startswith("crawl-delay"):
                    try:
                        delay = max(delay, float(line.split(":", 1)[1].strip()))
                    except ValueError:
                        pass
        except Exception:
            # No readable robots.txt is NOT permission to hammer. Keep the default delay and allow
            # the single request — the same posture cpalms_verify already takes.
            rp = None
        self._robots[key], self._delay[key] = rp, delay
        return rp

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return True if rp is None else rp.can_fetch(UA, url)

    def get(self, url: str) -> tuple:
        """(http_code, title, error). Exactly one request; no retries."""
        key = urllib.parse.urlunsplit(urllib.parse.urlsplit(url)[:2] + ("", "", ""))
        wait = self._delay.get(key, DEFAULT_DELAY) - (time.monotonic() - self._last.get(key, 0))
        if wait > 0:
            time.sleep(wait)
        self._last[key] = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:   # noqa: S310 — https only
                return resp.getcode(), title_of(resp.read(200_000).decode("utf-8", "replace")), None
        except urllib.error.HTTPError as e:
            return e.code, None, f"HTTPError {e.code}"
        except Exception as e:
            return None, None, f"{e.__class__.__name__}: {e}"


def candidates(doc: dict) -> list:
    """(url, record) for every record this tool is willing to look at.

    `urls` is a LIST of records carrying their own "url" key; records are mutated in place so the
    file's own ordering and every field this tool does not understand survive untouched."""
    out = []
    for r in doc.get("urls", []):
        if isinstance(r, dict) and r.get("status") in CANDIDATE_STATUSES and r.get("url"):
            out.append((r["url"], r))
    return out


def run(write: bool, offline: bool) -> int:
    doc = json.loads(PROV.read_text(encoding="utf-8"))
    todo = candidates(doc)
    today = date.today().isoformat()
    print(f"verify_urls — {len(todo)} record(s) with status in {sorted(CANDIDATE_STATUSES)}\n")
    if offline:
        for u, r in todo:
            print(f"  WOULD FETCH [{r['status']}] {u}")
        print(f"\n--check made 0 network requests. Run --dry-run or --write to fetch.")
        return 0

    f, changed = Fetcher(), 0
    for u, r in todo:
        if not f.allowed(u):
            status, reason, code, title = (*classify(u, None, None, error="robots",
                                                     prior=r["status"]), None, None)
        else:
            code, title, err = f.get(u)
            status, reason = classify(u, code, title, err, prior=r["status"])
        old = r["status"]
        mark = "=" if status == old else "->"
        print(f"  [{old}] {mark} [{status}] {u}")
        print(f"        http={code} title={title!r}")
        print(f"        {reason}")
        if write:
            r["status"] = status
            r["checked"] = today
            r["observed"] = {"http_status": code, "title": title, "reason": reason,
                             "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "by": "tools/verify_urls.py"}
            if status != old:
                # Never lose the history: a record that has changed status keeps what it was.
                r.setdefault("status_history", []).append({"from": old, "to": status, "on": today})
                changed += 1
    if write:
        doc["updated"] = today
        PROV.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwrote {PROV.relative_to(ROOT)} — {changed} status change(s), "
              f"{len(todo)} observation(s) recorded")
    else:
        print("\n--dry-run: nothing written.")
    return 0


def _self_test() -> int:
    fails = 0

    def ck(label, cond):
        nonlocal fails
        print(f"{'PASS' if cond else 'FAIL'} {label}")
        if not cond:
            fails += 1

    # example.com so these fixtures cannot trip the url-provenance scan they exercise
    U = "https://example.com/school-directory"
    ck("200 + corroborating title -> verified",
       classify(U, 200, "Orange County Public Schools - School Directory Home")[0] == "verified")
    ck("200 + GENERIC title -> stays unverified (the /departments/gifted case)",
       classify("https://example.com/departments/gifted", 200, "Departments")[0] == "unverified")
    ck("200 + no title -> stays unverified",
       classify(U, 200, None)[0] == "unverified")
    ck("403 CONFIRMS an existing exists_bot_blocked",
       classify("https://example.com/x", 403, None, prior="exists_bot_blocked")[0]
       == "exists_bot_blocked")
    ck("403 does NOT promote an unverified record — a blanket refusal is not proof of existence",
       classify("https://example.com/core/fileparse.php/7584/urlt/MSID.csv", 403, None,
                prior="unverified")[0] == "unverified")
    ck("404 -> dead_confirmed, never deletion",
       classify(U, 404, None)[0] == "dead_confirmed")
    ck("DNS/connection failure -> unreachable, not dead",
       classify(U, None, None, error="URLError")[0] == "unreachable")
    ck("robots disallow -> skipped_robots, never a silent skip",
       classify(U, None, None, error="robots")[0] == "skipped_robots")
    ck("a bogus URL cannot be promoted on a 200 alone",
       classify("https://example.com/zzzz-not-a-real-path", 200,
                "Orange County Public Schools")[0] == "unverified")
    ck("path tokens drop site chrome ('school'/'ocps' corroborate nothing)",
       path_tokens("https://example.com/departments/esol") == {"esol"})
    ck("title parsing strips tags and whitespace",
       title_of("<html><title>  A\n  B </title>") == "A B")
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Verify unverified URLs in url-provenance.json.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="list what would be fetched; NO network")
    g.add_argument("--dry-run", action="store_true", help="fetch and report; write nothing")
    g.add_argument("--write", action="store_true", help="fetch and record observations")
    g.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if a.write:
        return run(write=True, offline=False)
    if a.dry_run:
        return run(write=False, offline=False)
    return run(write=False, offline=True)          # --check is the default: never fetch by accident


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
