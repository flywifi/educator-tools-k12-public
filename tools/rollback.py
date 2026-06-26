#!/usr/bin/env python3
"""Whole-ecosystem rollback — restore the entire repo to the most recently saved good snapshot (git).

Per the approved plan, rollback is a SINGLE whole-ecosystem restore to a known-good tagged snapshot — not
per-skill (that invites cross-version mismatch). Safe by construction:
  - **Dry-run by default** — shows exactly which files would change (`git diff --stat`); nothing moves.
  - **Human approval required** — `--apply` is the human approving. An automated caller must pass
    `--auto`, which is refused unless the deployment granted `auto_rollback: true` in its flags.
  - **Always logged** — every rollback (and its failure reason) is appended to ledger/rollback-log.json.
  - **Re-verified** — after a restore it re-runs the drift guard.
Restores the working tree (via `git checkout <ref> -- <target>`, target defaults to the whole repo); a
human reviews + commits.

Known-good "saved versions" live in ledger/snapshots.json, anchored on COMMIT SHAs (durable) rather than
git tags: this environment ref-scopes write access to the feature branch, so tag pushes are rejected by
egress policy (HTTP 403) and would not survive the ephemeral container — commit SHAs ride along with the
branch push. `--record` appends the current HEAD (after a drift-guard check); `--list` shows them; `--to`
accepts a snapshot id, a commit, or a (local) tag.

Usage:
  python3 tools/rollback.py --record --label "F2: currency engine"          # snapshot HEAD as known-good
  python3 tools/rollback.py --list                                           # show saved snapshots
  python3 tools/rollback.py --to F1 --reason "major failure: X"              # dry-run, whole repo
  python3 tools/rollback.py --to F1 --reason "..." --apply                   # human-approved restore
  python3 tools/rollback.py --to <commit> --reason "..." --auto --flags cfg.json   # if auto_rollback granted
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "ledger" / "rollback-log.json"
SNAPSHOTS = ROOT / "ledger" / "snapshots.json"


def _git(args: list[str]) -> tuple[int, str]:
    p = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, (p.stdout + p.stderr).strip()


def _load_snapshots() -> dict:
    if SNAPSHOTS.exists():
        return json.loads(SNAPSHOTS.read_text(encoding="utf-8"))
    return {"version": "0.1.0", "snapshots": []}


def _resolve_ref(ref: str) -> str:
    """Map a snapshot id (e.g. 'F1') to its commit SHA; otherwise return the ref unchanged."""
    for snap in _load_snapshots().get("snapshots", []):
        if snap.get("id") == ref:
            return snap.get("commit", ref)
    return ref


def record_snapshot(label: str, reason: str) -> dict:
    """Append the current HEAD as a durable known-good snapshot (commit-anchored), after a drift check."""
    rc, head = _git(["rev-parse", "HEAD"])
    if rc != 0:
        return {"status": "error", "detail": "cannot resolve HEAD"}
    sc_rc = subprocess.run(["python3", "tools/sync_check.py"], capture_output=True, text=True,
                           cwd=str(ROOT)).returncode
    data = _load_snapshots()
    snaps = data.setdefault("snapshots", [])
    snap_id = label.split(":", 1)[0].strip() or f"snap-{len(snaps) + 1}"
    if any(s.get("id") == snap_id for s in snaps):
        snap_id = f"{snap_id}-{len(snaps) + 1}"
    entry = {"id": snap_id, "commit": head, "label": label, "reason": reason,
             "timestamp": datetime.now(timezone.utc).isoformat(),
             "drift_guard": "pass" if sc_rc == 0 else "fail", "local_tag": None}
    snaps.append(entry)
    SNAPSHOTS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"status": "recorded", **entry,
            "note": "commit-anchored (durable); commit ledger/snapshots.json so it rides the branch push"}


def _auto_allowed(flags_path: str | None) -> bool:
    if not flags_path:
        return False
    try:
        return bool(json.loads(Path(flags_path).read_text(encoding="utf-8")).get("auto_rollback", False))
    except Exception:
        return False


def _log(entry: dict) -> None:
    data = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else []
    data.append(entry)
    LOG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Approval-gated versioned rollback (offline, git).")
    ap.add_argument("--target", default=".", help="path to restore (default '.' = the whole ecosystem)")
    ap.add_argument("--to", metavar="REF", help="known-good snapshot id / commit / tag to restore from")
    ap.add_argument("--reason", default="", help="the failure being addressed (logged)")
    ap.add_argument("--apply", action="store_true", help="perform the rollback (human approval)")
    ap.add_argument("--auto", action="store_true", help="automated apply — requires auto_rollback in --flags")
    ap.add_argument("--flags", help="deployment flags JSON (for the auto_rollback grant)")
    ap.add_argument("--record", action="store_true", help="record current HEAD as a known-good snapshot")
    ap.add_argument("--label", default="", help="label for --record (e.g. 'F2: currency engine')")
    ap.add_argument("--list", action="store_true", help="list saved known-good snapshots")
    a = ap.parse_args(argv)

    if a.list:
        print(json.dumps(_load_snapshots(), indent=2))
        return 0
    if a.record:
        if not a.label:
            print(json.dumps({"status": "error", "detail": "--record needs --label"}))
            return 1
        print(json.dumps(record_snapshot(a.label, a.reason), indent=2))
        return 0
    if not a.to:
        print(json.dumps({"status": "error", "detail": "--to is required (snapshot id / commit / tag)"}))
        return 1

    if _git(["rev-parse", "--git-dir"])[0] != 0:
        print(json.dumps({"status": "error", "detail": "not a git repo; rollback needs git history"}))
        return 1
    a.to = _resolve_ref(a.to)
    rc, ref_show = _git(["rev-parse", "--short", a.to])
    if rc != 0:
        print(json.dumps({"status": "error", "detail": f"unknown git ref '{a.to}'"}))
        return 1
    rc, diffstat = _git(["diff", "--stat", a.to, "--", a.target])
    changed = bool(diffstat.strip())

    if not (a.apply or a.auto):
        print(json.dumps({"status": "dry_run", "target": a.target, "to": a.to, "would_change": changed,
                          "diffstat": diffstat,
                          "next": "re-run with --apply (human approval) — or --auto + --flags if auto_rollback is granted",
                          "human_review_required": True}, indent=2))
        return 0

    if a.auto and not a.apply and not _auto_allowed(a.flags):
        print(json.dumps({"status": "refused", "reason": "auto_rollback not granted in flags; needs human --apply",
                          "human_review_required": True}, indent=2))
        return 1

    mode = "auto" if (a.auto and _auto_allowed(a.flags)) else "manual_approved"
    rc, out = _git(["checkout", a.to, "--", a.target])
    if rc != 0:
        _log({"timestamp": datetime.now(timezone.utc).isoformat(), "target": a.target, "to": a.to,
              "reason": a.reason, "mode": mode, "result": "checkout_failed", "detail": out})
        print(json.dumps({"status": "error", "detail": out}))
        return 1
    sc_rc, sc_out = subprocess.run(["python3", "tools/sync_check.py"], capture_output=True, text=True,
                                   cwd=str(ROOT)).returncode, "sync_check ran"
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "target": a.target, "to": a.to,
             "reason": a.reason, "mode": mode, "result": "restored_working_tree",
             "drift_guard": "pass" if sc_rc == 0 else "fail",
             "note": "working tree changed; review the diff and commit to finalize"}
    _log(entry)
    print(json.dumps({"status": "rolled_back", **entry, "human_review_required": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
