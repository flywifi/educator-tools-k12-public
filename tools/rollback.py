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
human reviews + commits. Tag known-good snapshots with `git tag` (see tools/version.py).

Usage:
  python3 tools/rollback.py --to <last-good-tag> --reason "major failure: X"            # dry-run, whole repo
  python3 tools/rollback.py --to <last-good-tag> --reason "..." --apply                  # human-approved
  python3 tools/rollback.py --to <tag> --reason "..." --auto --flags cfg.json            # if auto_rollback granted
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


def _git(args: list[str]) -> tuple[int, str]:
    p = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, (p.stdout + p.stderr).strip()


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
    ap.add_argument("--to", required=True, metavar="GIT_REF", help="known-good tag/commit to restore from")
    ap.add_argument("--reason", default="", help="the failure being addressed (logged)")
    ap.add_argument("--apply", action="store_true", help="perform the rollback (human approval)")
    ap.add_argument("--auto", action="store_true", help="automated apply — requires auto_rollback in --flags")
    ap.add_argument("--flags", help="deployment flags JSON (for the auto_rollback grant)")
    a = ap.parse_args(argv)

    if _git(["rev-parse", "--git-dir"])[0] != 0:
        print(json.dumps({"status": "error", "detail": "not a git repo; rollback needs git history"}))
        return 1
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
