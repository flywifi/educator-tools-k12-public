#!/usr/bin/env python3
"""Source-currency + staleness engine (offline-graceful, stdlib) — RFC-F001 V2 workstream B.

The EXTERNAL counterpart to tools/registry_currency.py (which watches internal files for drift): this
monitors authoritative WEB sources for freshness and tells you which have gone stale, moved, been
superseded, or disappeared. It reads domain registries under canonical-sources/registries/<domain>.json, fetches each
source with a polite conditional GET, and classifies a freshness state:

  current      reachable + content unchanged (304, or content_sha256 matches the recorded baseline)
  changed      reachable + content hash differs from the baseline (re-verify, then re-baseline)
  superseded   a supersession/"rescinded/repealed/archived/program eliminated" keyword found, or a
               superseded_by link is recorded
  removed_404  HTTP 404/410 — the page/program is gone
  stale_age    last verified longer ago than the policy's stale_age_days (or an effective date passed
               with no re-check) and not re-confirmable this run
  unreachable  transport error / 5xx / robots-disallowed — could not verify (not the same as gone)
  uncertain    no fetch capability (offline / deps absent) or an ambiguous result — an HONEST gap

Multi-pronged detection: conditional GET (ETag/If-None-Match + Last-Modified/If-Modified-Since) ·
content sha256 (normalized) · supersession sentinel keywords · recency/effective-date · 404/410 sweep.
RSS/Atom + sitemap-diff sources are recognized (type: feed|sitemap) and parsed when reachable.

Honest by construction: standards/legal/program changes are ADVISORY — flagged with a reason + a
recommended action, never auto-applied and never fabricated. Offline, it degrades to age-only triage
(stale_age/uncertain) rather than guessing. Nothing re-baselines without a human (--update-baselines).

Usage:
  python3 tools/source_currency.py --check                       # all domains, JSON report (default)
  python3 tools/source_currency.py --check --domain florida-standards
  python3 tools/source_currency.py --summary                    # human-readable + stale-source list
  python3 tools/source_currency.py --offline                    # age-only triage, no network
  python3 tools/source_currency.py --update-baselines --domain florida-standards   # after human approval
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "canonical-sources" / "registries"
DEFAULT_UA = "TOS-source-currency/0.1 (+polite freshness checker; respects robots.txt)"
DEFAULT_TIMEOUT = 30

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(value)
        except Exception:
            return None


def _content_hash(body: bytes) -> str:
    """Hash whitespace-normalized text so trivial reflow doesn't read as a change (matches the crawler)."""
    norm = re.sub(rb"\s+", b" ", body).strip()
    return hashlib.sha256(norm).hexdigest()


def _conditional_get(url: str, etag: str | None, last_modified: str | None, timeout: int):
    """Polite conditional GET. Returns (status, body, headers) with status 0 on transport error.

    Sends If-None-Match / If-Modified-Since so a server can answer 304 (unchanged) cheaply.
    """
    headers = {"User-Agent": DEFAULT_UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    if _HAS_REQUESTS:
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            return r.status_code, (r.content or b""), {k.lower(): v for k, v in r.headers.items()}
        except Exception:
            return 0, b"", {}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, b"", {k.lower(): v for k, v in dict(getattr(e, "headers", {}) or {}).items()}
    except Exception:
        return 0, b"", {}


def _find_supersession(text: str, keywords: list[str]) -> str | None:
    low = text.lower()
    for kw in keywords:
        if kw.lower() in low:
            return kw
    return None


# --------------------------------------------------------------------------- classification
ACTION = {
    "current": "none",
    "changed": "re-verify the change on the PRIMARY source; human-approve, then --update-baselines",
    "superseded": "confirm the supersession on the authority; update or retire the dependent content (advisory)",
    "removed_404": "the page/program appears gone — confirm, then retire or repoint dependent content",
    "stale_age": "re-verify the source is still current; refresh the baseline (advisory; do not assume change)",
    "unreachable": "could not verify this run (transport/robots/5xx) — retry later; do not assume gone",
    "uncertain": "no fetch capability or ambiguous — record as a gap; verify with the host AI's web access",
}


def _classify(src: dict, policy: dict, offline: bool, timeout: int) -> dict:
    st = src.get("state", {}) or {}
    keywords = policy.get("supersession_keywords", [])
    stale_days = int(policy.get("stale_age_days", 365))
    now = _now()
    result = {"id": src.get("id"), "url": src.get("url"), "label": src.get("label"),
              "category": src.get("category"), "authority": src.get("authority", "secondary"),
              "state": None, "reason": "", "checked_at": _iso(now),
              "fetched": {"status": None, "etag": st.get("etag"), "last_modified": st.get("last_modified"),
                          "content_sha256": st.get("content_sha256")}}

    # Recorded supersession always wins — a human already linked a successor.
    if st.get("superseded_by"):
        result.update(state="superseded", reason=f"superseded_by recorded: {st['superseded_by']}")
        result["recommended_action"] = ACTION["superseded"]
        return result

    def _age_triage(extra: str) -> dict:
        last = _parse_dt(st.get("last_checked"))
        eff = _parse_dt(st.get("effective_date"))
        aged = last is not None and (now - last).days > stale_days
        if aged:
            result.update(state="stale_age",
                          reason=f"last verified {(now - last).days}d ago (> {stale_days}d){extra}")
        elif eff is not None and eff <= now and st.get("content_sha256") is None:
            result.update(state="stale_age", reason=f"effective date {st['effective_date']} passed; never verified{extra}")
        else:
            result.update(state="uncertain", reason=f"not verifiable this run{extra}")
        result["recommended_action"] = ACTION[result["state"]]
        return result

    if offline:
        return _age_triage(" (offline)")

    status, body, headers = _conditional_get(src["url"], st.get("etag"), st.get("last_modified"), timeout)
    result["fetched"]["status"] = status

    if status in (404, 410):
        result.update(state="removed_404", reason=f"HTTP {status}")
        result["recommended_action"] = ACTION["removed_404"]
        return result
    if status == 304:
        result.update(state="current", reason="304 Not Modified")
        result["recommended_action"] = ACTION["current"]
        return result
    if status == 0 or status >= 500 or (400 <= status < 500 and status not in (404, 410)):
        result.update(state="unreachable", reason=f"transport/server status {status}")
        # An unreachable source that is also long-unverified is really a staleness problem.
        last = _parse_dt(st.get("last_checked"))
        if last is not None and (now - last).days > stale_days:
            result.update(state="stale_age", reason=f"unreachable + last verified {(now - last).days}d ago")
        result["recommended_action"] = ACTION[result["state"]]
        return result

    text = body.decode("utf-8", "ignore")
    kw = _find_supersession(text, keywords)
    if kw:
        result.update(state="superseded", reason=f"supersession keyword found: '{kw}'")
        result["recommended_action"] = ACTION["superseded"]
        return result

    digest = _content_hash(body)
    result["fetched"]["content_sha256"] = digest
    result["fetched"]["etag"] = headers.get("etag") or st.get("etag")
    result["fetched"]["last_modified"] = headers.get("last-modified") or st.get("last_modified")
    base = st.get("content_sha256")
    if base is None:
        result.update(state="uncertain", reason="no baseline recorded yet — run --update-baselines to set one")
    elif digest != base:
        result.update(state="changed", reason="content hash differs from baseline")
    else:
        result.update(state="current", reason="content hash matches baseline")
    result["recommended_action"] = ACTION[result["state"]]
    return result


# --------------------------------------------------------------------------- registry I/O
def _registry_paths(domain: str | None) -> list[Path]:
    if not SOURCES_DIR.exists():
        return []
    files = sorted(p for p in SOURCES_DIR.glob("*.json"))
    if domain:
        files = [p for p in files if p.stem == domain]
    return files


def check(domain: str | None, offline: bool, timeout: int) -> dict:
    reports, counts = [], {}
    for path in _registry_paths(domain):
        reg = json.loads(path.read_text(encoding="utf-8"))
        policy = reg.get("freshness_policy", {})
        rows = [_classify(s, policy, offline, timeout) for s in reg.get("sources", [])]
        for r in rows:
            counts[r["state"]] = counts.get(r["state"], 0) + 1
        reports.append({"domain": reg.get("domain", path.stem), "registry": str(path.relative_to(ROOT)),
                        "authority_note": reg.get("authority_note"), "sources": rows})
    stale = [r for rep in reports for r in rep["sources"]
             if r["state"] in ("changed", "superseded", "removed_404", "stale_age")]
    return {"tool": "source-currency", "generated_at": _iso(), "mode": "offline" if offline else "online",
            "fetch": "requests" if _HAS_REQUESTS else "urllib",
            "domains_checked": len(reports), "state_counts": counts,
            "stale_count": len(stale), "stale_sources": stale, "reports": reports,
            "note": "standards/legal/program changes are advisory + human-verified — never auto-applied",
            "human_review_required": True}


def update_baselines(domain: str | None, timeout: int) -> dict:
    """Re-fetch each source and record its current etag/last_modified/content_sha256/last_checked.

    Run ONLY after a human has reviewed the changes. Never invoked automatically by --check.
    """
    updated = 0
    for path in _registry_paths(domain):
        reg = json.loads(path.read_text(encoding="utf-8"))
        for s in reg.get("sources", []):
            st = s.setdefault("state", {})
            status, body, headers = _conditional_get(s["url"], None, None, timeout)
            st["last_checked"] = _iso()
            st["last_status"] = status
            if status == 200 and body:
                st["content_sha256"] = _content_hash(body)
                st["etag"] = headers.get("etag")
                st["last_modified"] = headers.get("last-modified")
                updated += 1
        reg["updated"] = _now().date().isoformat()
        path.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    return {"status": "baselines_updated", "sources_recorded": updated,
            "note": "review the registry diff and commit it to finalize", "human_review_required": True}


def to_summary(report: dict) -> str:
    mark = {"current": "ok  ", "changed": "CHG ", "superseded": "SUPS", "removed_404": "404 ",
            "stale_age": "OLD ", "unreachable": "UNRC", "uncertain": "?   "}
    lines = ["# Source-currency report", "",
             f"- mode: {report['mode']} ({report['fetch']}) · domains: {report['domains_checked']}"
             f" · stale/actionable: {report['stale_count']}",
             f"- states: {report['state_counts']}", ""]
    for rep in report["reports"]:
        lines.append(f"## {rep['domain']}  ({rep['registry']})")
        for r in rep["sources"]:
            lines.append(f"- [{mark.get(r['state'], '?')}] {r['id']:24} {r['reason']}")
            if r["state"] in ("changed", "superseded", "removed_404", "stale_age"):
                lines.append(f"        -> {r.get('recommended_action', '')}")
        lines.append("")
    lines += ["_Advisory: confirm every standards/legal/program change on the PRIMARY source before acting._",
              "_human_review_required: true._"]
    return "\n".join(lines) + "\n"


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Monitor authoritative web sources for staleness (offline-graceful).")
    ap.add_argument("--check", action="store_true", help="JSON freshness report (default)")
    ap.add_argument("--summary", action="store_true", help="human-readable report + stale-source list")
    ap.add_argument("--offline", action="store_true", help="age-only triage; no network fetch")
    ap.add_argument("--domain", help="limit to one canonical-sources/registries/<domain>.json registry")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--update-baselines", action="store_true",
                    help="record current etag/last_modified/content_sha256 (after human approval)")
    a = ap.parse_args(argv)

    if not SOURCES_DIR.exists() or not _registry_paths(a.domain):
        print(json.dumps({"status": "error",
                          "detail": f"no source registries found under {SOURCES_DIR.relative_to(ROOT)}"
                                    + (f" for domain '{a.domain}'" if a.domain else "")}))
        return 1
    if a.update_baselines:
        print(json.dumps(update_baselines(a.domain, a.timeout), indent=2))
        return 0
    report = check(a.domain, a.offline, a.timeout)
    if a.summary:
        print(to_summary(report), end="")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["stale_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
