#!/usr/bin/env python3
"""Seed curator (L8) — keep the feed catalog accurate. Auto-apply SAFE repairs, log everything.

The catalog librarian for shared/feeds/feeds.json. It:
  * VALIDATES every feed (reusing the F2 currency engine) — dead links, unreachable, stale, plus static
    label checks (category/authority/tier/purpose sanity) and a redirect probe.
  * DISCOVERS candidate feeds by RSS autodiscovery from an authoritative page.
  * PROPOSES a single human-reviewable change set (add / remove / repair / relabel), each entry tagged
    `safe_repair`.
  * APPLIES **mechanically-safe repairs automatically** (remove a confirmed 404/410, follow a verified
    301/302 redirect); everything else stays a proposal you approve.
  * LOGS *every* change — auto or approved — to ledger/feeds-change-log.json with before/after + reason,
    and can `--revert` any entry. Nothing is fabricated; advisory + human-reviewed throughout.

Usage:
  python3 tools/seed_curator.py --validate [--offline]            # per-feed health + label checks
  python3 tools/seed_curator.py --propose  [--offline]            # dry-run change set (no writes)
  python3 tools/seed_curator.py --discover-from <PAGE_URL>        # RSS autodiscovery candidates
  python3 tools/seed_curator.py --apply                          # auto-apply SAFE repairs (writes + logs)
  python3 tools/seed_curator.py --apply-proposal <FILE> [--approve]  # apply an approved proposal
  python3 tools/seed_curator.py --log                            # show the audit trail
  python3 tools/seed_curator.py --revert <ENTRY_ID>             # undo a logged change
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "shared" / "feeds"))
import source_currency as sc  # noqa: E402
import feeds as engine        # noqa: E402

LOG = ROOT / "ledger" / "feeds-change-log.json"
VALID_AUTHORITY = {"primary", "secondary"}
VALID_TIER = {"canonical", "news_teacher_student", "product_updates"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- audit log
def load_log() -> dict:
    if not LOG.exists():
        return {"version": "0.1.0", "_comment": "Append-only audit trail of feed-catalog changes "
                "(auto-applied safe repairs + approved edits). Each entry is reversible via "
                "seed_curator.py --revert <id>.", "entries": []}
    return json.loads(LOG.read_text(encoding="utf-8"))


def append_log(action: str, feed_id: str, before, after, reason: str, source: str, mode: str) -> str:
    log = load_log()
    entry_id = f"fc-{len(log['entries']) + 1:04d}"
    log["entries"].append({"id": entry_id, "ts": _now(), "feed_id": feed_id, "action": action,
                           "before": before, "after": after, "reason": reason, "source": source,
                           "mode": mode})
    LOG.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return entry_id


# --------------------------------------------------------------------------- validation
def static_label_checks(feed: dict) -> list[str]:
    """No-network sanity checks on a feed's catalog labels."""
    issues = []
    if feed.get("authority") not in VALID_AUTHORITY:
        issues.append(f"authority '{feed.get('authority')}' not in {sorted(VALID_AUTHORITY)}")
    if feed.get("tier") not in VALID_TIER:
        issues.append(f"tier '{feed.get('tier')}' not in {sorted(VALID_TIER)}")
    if not (feed.get("purpose") or "").strip():
        issues.append("missing 'purpose' label")
    if feed.get("tier") == "canonical" and feed.get("authority") != "primary":
        issues.append("tier 'canonical' but authority is not 'primary' (only primary confirms a change)")
    return issues


def _redirect_probe(url: str, timeout: int) -> str | None:
    """Return a new URL if the source answers a 301/302 (a safe, mechanical repair). Network-best-effort."""
    if getattr(sc, "_HAS_REQUESTS", False):
        try:
            import requests
            r = requests.get(url, allow_redirects=False, timeout=timeout,
                             headers={"User-Agent": getattr(sc, "DEFAULT_UA", "TOS-curator/0.1")})
            if r.status_code in (301, 302, 308) and r.headers.get("location"):
                return r.headers["location"]
        except Exception:
            return None
    return None


def validate_catalog(catalog: dict, offline: bool, timeout: int) -> dict:
    policy = catalog.get("freshness_policy", {})
    rows = []
    for f in catalog.get("feeds", []):
        cls = sc._classify(f, policy, offline, timeout)
        labels = static_label_checks(f)
        redirect = None if offline or cls["state"] in ("removed_404",) else _redirect_probe(f["url"], timeout)
        rows.append({"id": f["id"], "url": f["url"], "tier": f.get("tier"),
                     "authority": f.get("authority"), "state": cls["state"], "reason": cls["reason"],
                     "label_issues": labels, "redirect_to": redirect,
                     "verified": f.get("verified", False)})
    summary = {}
    for r in rows:
        summary[r["state"]] = summary.get(r["state"], 0) + 1
    return {"tool": "seed-curator", "generated_at": _now(), "offline": offline,
            "feeds": len(rows), "state_counts": summary, "reports": rows,
            "human_review_required": True}


# --------------------------------------------------------------------------- discovery
_RSS_LINK = re.compile(
    rb'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+>',
    re.IGNORECASE)
_HREF = re.compile(rb'href=["\']([^"\']+)["\']', re.IGNORECASE)


def discover_from_page(page_url: str, timeout: int) -> dict:
    """RSS autodiscovery: fetch an authoritative page, surface its declared feed links as candidates."""
    status, body, _ = sc._conditional_get(page_url, None, None, timeout)
    if status in (0, 404, 410) or not body:
        return {"page": page_url, "status": status, "candidates": [],
                "gap": "page unreachable/gone — cannot autodiscover (egress or bad URL)"}
    cands = []
    for tag in _RSS_LINK.findall(body):
        m = _HREF.search(tag)
        if m:
            href = m.group(1).decode("utf-8", "replace")
            cands.append({"url": href, "discovered_from": page_url, "authority": "secondary",
                          "tier": "news_teacher_student", "verified": False,
                          "note": "candidate — classify/label + human-approve before adding"})
    return {"page": page_url, "status": status, "candidates": cands,
            "human_review_required": True}


# --------------------------------------------------------------------------- proposal
def build_proposal(catalog: dict, report: dict) -> dict:
    """Turn a validation report into a change set. safe_repair=True ⇒ eligible for auto-apply."""
    remove, repair, relabel = [], [], []
    for r in report["reports"]:
        if r["state"] in ("removed_404",):
            remove.append({"id": r["id"], "safe_repair": True,
                           "reason": f"{r['state']}: {r['reason']}"})
        if r.get("redirect_to"):
            repair.append({"id": r["id"], "field": "url", "old": r["url"], "new": r["redirect_to"],
                           "safe_repair": True, "reason": "verified 301/302 redirect"})
        if r["label_issues"]:
            relabel.append({"id": r["id"], "safe_repair": False, "issues": r["label_issues"],
                            "reason": "label sanity — human decides the correct labels"})
    return {"tool": "seed-curator", "generated_at": _now(), "add": [], "remove": remove,
            "repair": repair, "relabel": relabel, "human_review_required": True,
            "note": "safe_repair:true entries auto-apply with --apply; others need --apply-proposal --approve"}


# --------------------------------------------------------------------------- apply / revert
def _find_feed(catalog: dict, fid: str) -> dict | None:
    return next((f for f in catalog.get("feeds", []) if f["id"] == fid), None)


def apply_proposal(catalog: dict, proposal: dict, approve: bool, source: str) -> dict:
    """Apply changes. Safe repairs always apply; non-safe only when approve=True. Every change logged."""
    applied, skipped = [], []

    def _do_remove(item, mode):
        f = _find_feed(catalog, item["id"])
        if not f:
            return
        catalog["feeds"] = [x for x in catalog["feeds"] if x["id"] != item["id"]]
        eid = append_log("remove", item["id"], f, None, item["reason"], source, mode)
        applied.append({"id": item["id"], "action": "remove", "log": eid})

    def _do_repair(item, mode):
        f = _find_feed(catalog, item["id"])
        if not f:
            return
        before = f.get(item["field"])
        f[item["field"]] = item["new"]
        if item["field"] == "url":
            f.setdefault("state", {}).update({"etag": None, "last_modified": None, "content_sha256": None})
        eid = append_log("repair", item["id"], {item["field"]: before}, {item["field"]: item["new"]},
                         item["reason"], source, mode)
        applied.append({"id": item["id"], "action": "repair", "log": eid})

    for item in proposal.get("remove", []):
        (_do_remove(item, "auto") if item.get("safe_repair") else
         (_do_remove(item, "approved") if approve else skipped.append({"id": item["id"], "action": "remove"})))
    for item in proposal.get("repair", []):
        (_do_repair(item, "auto") if item.get("safe_repair") else
         (_do_repair(item, "approved") if approve else skipped.append({"id": item["id"], "action": "repair"})))
    for item in proposal.get("relabel", []):  # never safe; only on approve, with explicit new labels
        if approve and item.get("new_labels"):
            f = _find_feed(catalog, item["id"])
            if f:
                before = {k: f.get(k) for k in item["new_labels"]}
                f.update(item["new_labels"])
                eid = append_log("relabel", item["id"], before, item["new_labels"],
                                 item.get("reason", "relabel"), source, "approved")
                applied.append({"id": item["id"], "action": "relabel", "log": eid})
        else:
            skipped.append({"id": item["id"], "action": "relabel"})
    for item in proposal.get("add", []):
        if approve:
            catalog.setdefault("feeds", []).append(item["feed"])
            eid = append_log("add", item["feed"]["id"], None, item["feed"],
                             item.get("reason", "add discovered feed"), source, "approved")
            applied.append({"id": item["feed"]["id"], "action": "add", "log": eid})
        else:
            skipped.append({"id": item.get("feed", {}).get("id"), "action": "add"})

    return {"applied": applied, "skipped": skipped,
            "note": "skipped items need --approve (with explicit new_labels for relabels)"}


def revert_entry(catalog: dict, entry_id: str) -> dict:
    log = load_log()
    entry = next((e for e in log["entries"] if e["id"] == entry_id), None)
    if not entry:
        return {"status": "not_found", "id": entry_id}
    act = entry["action"]
    if act == "remove":                       # re-add the removed feed
        catalog.setdefault("feeds", []).append(entry["before"])
    elif act == "add":                        # remove the added feed
        catalog["feeds"] = [x for x in catalog["feeds"] if x["id"] != entry["feed_id"]]
    elif act in ("repair", "relabel"):        # restore the prior field values
        f = _find_feed(catalog, entry["feed_id"])
        if f and isinstance(entry["before"], dict):
            f.update(entry["before"])
    append_log(f"revert:{act}", entry["feed_id"], entry["after"], entry["before"],
               f"revert of {entry_id}", "seed_curator --revert", "approved")
    return {"status": "reverted", "id": entry_id, "action": act}


# --------------------------------------------------------------------------- CLI
def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Seed curator (L8) — keep the feed catalog accurate")
    ap.add_argument("--validate", action="store_true", help="per-feed health + label checks")
    ap.add_argument("--propose", action="store_true", help="dry-run change set (no writes)")
    ap.add_argument("--discover-from", metavar="PAGE_URL", dest="discover_from",
                    help="RSS autodiscovery candidates from an authoritative page")
    ap.add_argument("--apply", action="store_true", help="auto-apply SAFE repairs (writes + logs)")
    ap.add_argument("--apply-proposal", metavar="FILE", dest="apply_proposal",
                    help="apply an approved (possibly hand-edited) proposal JSON")
    ap.add_argument("--approve", action="store_true", help="with --apply-proposal: apply non-safe edits too")
    ap.add_argument("--log", action="store_true", help="show the audit trail")
    ap.add_argument("--revert", metavar="ENTRY_ID", help="undo a logged change")
    ap.add_argument("--offline", action="store_true", help="age-only triage; no network")
    ap.add_argument("--timeout", type=int, default=15)
    a = ap.parse_args(argv)

    catalog = engine.load_catalog()

    if a.log:
        print(json.dumps(load_log(), indent=2, ensure_ascii=False)); return 0
    if a.validate:
        print(json.dumps(validate_catalog(catalog, a.offline, a.timeout), indent=2, ensure_ascii=False)); return 0
    if a.discover_from:
        print(json.dumps(discover_from_page(a.discover_from, a.timeout), indent=2, ensure_ascii=False)); return 0
    if a.propose:
        rep = validate_catalog(catalog, a.offline, a.timeout)
        print(json.dumps(build_proposal(catalog, rep), indent=2, ensure_ascii=False)); return 0
    if a.apply:
        rep = validate_catalog(catalog, a.offline, a.timeout)
        prop = build_proposal(catalog, rep)
        res = apply_proposal(catalog, prop, approve=False, source="seed_curator --apply")
        if res["applied"]:
            engine.save_catalog(catalog)
        print(json.dumps({"mode": "auto-safe-repairs", **res}, indent=2, ensure_ascii=False)); return 0
    if a.apply_proposal:
        prop = json.loads(Path(a.apply_proposal).read_text(encoding="utf-8"))
        res = apply_proposal(catalog, prop, approve=a.approve, source=f"seed_curator --apply-proposal")
        if res["applied"]:
            engine.save_catalog(catalog)
        print(json.dumps({"mode": "approved" if a.approve else "safe-only", **res}, indent=2, ensure_ascii=False)); return 0
    if a.revert:
        res = revert_entry(catalog, a.revert)
        if res["status"] == "reverted":
            engine.save_catalog(catalog)
        print(json.dumps(res, indent=2)); return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
