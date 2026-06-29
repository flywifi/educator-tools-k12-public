#!/usr/bin/env python3
"""rate_governor.py — per-host politeness + lockout avoidance for local harvesting.

The combined acquirer can throw many requests at a site. This governor keeps that from tripping a
rate-limit LOCKOUT (a temporary IP ban) by learning and respecting how hard each host can be hit:

  * ROBOTS LIMIT      reads robots.txt Crawl-delay / Request-rate per host (the site's OWN stated
                      pace) and never goes faster than that — or a polite floor, whichever is slower.
  * PER-HOST SPACING  enforces a minimum interval between requests to the same host, with jitter,
                      so bursts are smoothed out.
  * SERVER BACKOFF    on 429/503 it honors Retry-After / RateLimit-Reset, then backs off exponentially
                      (bounded retries). It never evades a limit — it waits it out.
  * CIRCUIT BREAKER   after N consecutive throttles/blocks (429/503/403) it STOPS hitting that host
                      for a cooldown, so one refusing site can never escalate into an IP lockout.
  * REQUEST BUDGET    a per-host cap per run; once spent, that host is done (self-limiting crawl).
  * MEMORY            persists what it learned (observed crawl-delay, recent breaker trips) to
                      .harvest-cache/host_limits.json, so the NEXT run already knows each host's limits.

Usage:
    gov = RateGovernor(ua, per_host_budget=120)
    ok, why = gov.can_request(url)          # False if breaker tripped / budget spent / robots-disallowed
    if ok:
        gov.wait(url)                       # block until this host's min interval has elapsed
        status, headers = do_the_fetch(url)
        retry_after = gov.note(url, status, headers)   # updates breaker/backoff; returns wait-or-None
        if retry_after is not None: time.sleep(retry_after); ...retry the SAME url...
    gov.save()
"""
from __future__ import annotations

import json
import random
import time
import urllib.parse
import urllib.robotparser
from pathlib import Path

DEFAULT_MIN_INTERVAL = 1.5          # polite floor between same-host requests (seconds)
JITTER = (0.3, 1.2)                 # added to every wait so requests aren't perfectly periodic
THROTTLE_STATUSES = {429, 503}      # server explicitly saying "slow down"
BLOCK_STATUSES = {403, 429, 503}    # count toward the breaker (403 can be a soft bot-block / pre-ban)
BREAKER_THRESHOLD = 4               # consecutive blocks before the host breaker trips
BREAKER_COOLDOWN = 900.0            # 15 min host cooldown after a trip
MAX_BACKOFF = 120.0                 # cap any single backoff wait
DEFAULT_BUDGET = 200                # default max requests per host per run

_CACHE_DIRNAME = ".harvest-cache"


def _root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(6):
        if (p / "tools" / "sync_check.py").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return Path(__file__).resolve().parent.parent


def host_of(url: str) -> str:
    """Registrable-ish host key (drop port + leading www.) so api.x.com and www.x.com share a budget
    at the host level but stay distinct from other subdomains we might pace differently."""
    net = urllib.parse.urlparse(url).netloc.split("@")[-1].split(":")[0].lower()
    return net[4:] if net.startswith("www.") else net


class _HostState:
    __slots__ = ("min_interval", "last_request", "consecutive_bad", "breaker_until",
                 "count", "robots_checked", "robots")

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.last_request = 0.0
        self.consecutive_bad = 0
        self.breaker_until = 0.0
        self.count = 0
        self.robots_checked = False
        self.robots: urllib.robotparser.RobotFileParser | None = None


class RateGovernor:
    def __init__(self, ua: str, *, per_host_budget: int = DEFAULT_BUDGET,
                 min_interval: float = DEFAULT_MIN_INTERVAL, respect_robots: bool = True,
                 persist: bool = True, verbose: bool = True):
        self.ua = ua
        self.per_host_budget = per_host_budget
        self.floor = min_interval
        self.respect_robots = respect_robots
        self.verbose = verbose
        self._hosts: dict[str, _HostState] = {}
        self._cache = (_root() / _CACHE_DIRNAME / "host_limits.json") if persist else None
        self.events: list[str] = []   # human-readable log of waits/backoffs/breaker trips
        self._load()

    # ---- robots-derived limits ------------------------------------------------
    def _robots(self, url: str):
        st = self._state(url)
        if st.robots_checked or not self.respect_robots:
            return st.robots
        st.robots_checked = True
        pr = urllib.parse.urlparse(url)
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{pr.scheme}://{pr.netloc}/robots.txt")
        try:
            rp.read()
            st.robots = rp
            # The site's OWN stated pace wins if it's slower than our floor.
            cd = rp.crawl_delay(self.ua)
            rr = rp.request_rate(self.ua)
            stated = 0.0
            if cd:
                stated = max(stated, float(cd))
            if rr and rr.requests:
                stated = max(stated, float(rr.seconds) / float(rr.requests))
            if stated > st.min_interval:
                st.min_interval = stated
                self._log(f"{host_of(url)}: robots states ~{stated:.1f}s between requests; honoring it")
        except Exception:
            st.robots = None  # no robots reachable -> allowed, keep the floor
        return st.robots

    def allowed_by_robots(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        rp = self._robots(url)
        return True if rp is None else rp.can_fetch(self.ua, url)

    # ---- state ----------------------------------------------------------------
    def _state(self, url: str) -> _HostState:
        h = host_of(url)
        if h not in self._hosts:
            self._hosts[h] = _HostState(self.floor)
        return self._hosts[h]

    def _log(self, msg: str) -> None:
        self.events.append(msg)
        if self.verbose:
            import sys
            print(f"[rate] {msg}", file=sys.stderr)

    # ---- gate / pace / observe ------------------------------------------------
    def can_request(self, url: str) -> tuple[bool, str]:
        st = self._state(url)
        now = time.time()
        if st.breaker_until > now:
            return False, f"{host_of(url)}: breaker open for {int(st.breaker_until - now)}s (avoiding lockout)"
        if st.count >= self.per_host_budget:
            return False, f"{host_of(url)}: per-host budget ({self.per_host_budget}) spent"
        if not self.allowed_by_robots(url):
            return False, f"{host_of(url)}: disallowed by robots.txt"
        return True, ""

    def wait(self, url: str) -> None:
        """Block until this host's minimum interval has elapsed since the last request, + jitter."""
        st = self._state(url)
        self._robots(url)  # ensure robots-derived interval is loaded before pacing
        gap = st.min_interval + random.uniform(*JITTER)
        elapsed = time.time() - st.last_request
        if st.last_request and elapsed < gap:
            time.sleep(gap - elapsed)
        st.last_request = time.time()
        st.count += 1

    def cooldown(self, url: str, reason: str = "", seconds: float = BREAKER_COOLDOWN) -> None:
        """Proactively open the breaker for a host — e.g. when a block DETECTOR (fetch_diag) is already
        confident the host is serving a challenge/IP-block, so we rest it now instead of waiting for the
        consecutive-failure count to add up (and risk a real lockout in the meantime)."""
        st = self._state(url)
        st.breaker_until = max(st.breaker_until, time.time() + seconds)
        st.consecutive_bad = 0
        self._log(f"{host_of(url)}: cooldown {int(seconds/60)} min ({reason or 'detector-directed'})")
        self.save()

    def note(self, url: str, status: int | None, headers: dict | None = None) -> float | None:
        """Record a response. On a throttle, return how long to wait before retrying the SAME url
        (None = don't retry). Trips the per-host breaker after repeated blocks to avoid a lockout."""
        st = self._state(url)
        if status in BLOCK_STATUSES:
            st.consecutive_bad += 1
            if st.consecutive_bad >= BREAKER_THRESHOLD:
                st.breaker_until = time.time() + BREAKER_COOLDOWN
                st.consecutive_bad = 0
                self._log(f"{host_of(url)}: {BREAKER_THRESHOLD} blocks in a row -> breaker tripped, "
                          f"backing off {int(BREAKER_COOLDOWN/60)} min to avoid a lockout")
                self.save()
            if status in THROTTLE_STATUSES:
                ra = _retry_after_seconds(headers or {})
                wait = min(ra if ra is not None else (st.min_interval * 2 ** st.consecutive_bad), MAX_BACKOFF)
                self._log(f"{host_of(url)}: HTTP {status}; backing off {wait:.0f}s (server-directed)")
                return wait
            return None
        if status and 200 <= status < 400:
            st.consecutive_bad = 0  # recovered
        return None

    # ---- persistence ----------------------------------------------------------
    def _load(self) -> None:
        if not self._cache or not self._cache.exists():
            return
        try:
            data = json.loads(self._cache.read_text(encoding="utf-8"))
        except Exception:
            return
        now = time.time()
        for h, rec in data.get("hosts", {}).items():
            st = _HostState(max(self.floor, float(rec.get("min_interval", self.floor))))
            # carry a still-active breaker forward so a fresh run doesn't immediately re-hammer a host
            bu = float(rec.get("breaker_until", 0))
            st.breaker_until = bu if bu > now else 0.0
            self._hosts[h] = st

    def save(self) -> None:
        if not self._cache:
            return
        try:
            self._cache.parent.mkdir(parents=True, exist_ok=True)
            out = {"updated": time.time(),
                   "hosts": {h: {"min_interval": round(s.min_interval, 2),
                                 "breaker_until": round(s.breaker_until, 1)}
                             for h, s in self._hosts.items()}}
            self._cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
        except Exception:
            pass

    def summary(self) -> dict:
        return {h: {"requests": s.count, "min_interval": round(s.min_interval, 2),
                    "breaker_open": s.breaker_until > time.time()}
                for h, s in self._hosts.items()}


def _retry_after_seconds(headers: dict) -> float | None:
    """Honor the server's own backoff window: Retry-After (seconds or HTTP-date) or RateLimit-Reset."""
    if not headers:
        return None
    h = {str(k).lower(): v for k, v in headers.items()}
    ra = h.get("retry-after")
    if ra:
        try:
            return float(int(str(ra).strip()))
        except ValueError:
            try:
                from email.utils import parsedate_to_datetime
                from datetime import datetime
                dt = parsedate_to_datetime(ra)
                return max(0.0, (dt - datetime.now(dt.tzinfo)).total_seconds())
            except Exception:
                return None
    reset = h.get("ratelimit-reset") or h.get("x-ratelimit-reset")
    if reset:
        try:
            return float(int(str(reset).strip()))
        except ValueError:
            return None
    return None
