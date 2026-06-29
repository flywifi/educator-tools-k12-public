#!/usr/bin/env python3
"""Guided skill repair (skill-repair-manager pattern) — apply an APPROVED health repair plan, minimally.

Consumes the repair plan from shared/health/health.py, separates **mechanical** (safe to auto-apply)
from **judgment** (needs a human) steps, and prints a plain-language approval summary. Dry-run by
default. With --apply it performs only the safe, reversible mechanical fixes (regenerate derived files,
re-baseline nothing without approval) and re-runs the drift guard; judgment items are always left for a
human. Keeps the scope tight and the approval trail explicit — it never silently expands a fix into a
redesign.

Usage:
  python3 tools/skill_repair.py                 # dry-run: what would change, what needs you
  python3 tools/skill_repair.py --apply         # apply safe mechanical fixes, then re-run sync_check
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared" / "health"))


def _plan(plan_path: str | None = None) -> list[dict]:
    """Read the repair plan from a saved skill-health report (--plan) or compute it live."""
    if plan_path:
        data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
        return data.get("repair_plan", data if isinstance(data, list) else [])
    import health  # type: ignore
    return health.build_report().get("repair_plan", [])


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout or p.stderr) else ""


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Apply an approved skill-health repair plan (minimally).")
    ap.add_argument("--apply", action="store_true", help="apply safe mechanical fixes (default: dry-run)")
    ap.add_argument("--plan", metavar="PATH", help="read the plan from a saved skill-health report (--out)")
    a = ap.parse_args(argv)

    plan = _plan(a.plan)
    mechanical = [s for s in plan if s.get("mechanical")]
    judgment = [s for s in plan if not s.get("mechanical")]

    print("# Skill-repair — proposed changes (plain language)\n")
    print(f"The health scan found {len(plan)} item(s): {len(mechanical)} mechanical (safe to automate), "
          f"{len(judgment)} that need your judgment.\n")
    if mechanical:
        print("## Mechanical (I can apply on approval)")
        for s in mechanical:
            print(f"- [{s['severity']}] {s['area']} — {s['action']}")
    if judgment:
        print("\n## Needs you (I will NOT auto-change these)")
        for s in judgment:
            print(f"- [{s['severity']}] {s['area']} — {s['action']}")

    print("\n## Validation plan\n- regenerate derived metrics; re-run tools/sync_check.py; "
          "judgment items remain for human edit + re-review by quality-review.")

    if not a.apply:
        print("\nFinalization status: **waiting for approval** (dry-run). Re-run with --apply to perform "
              "the safe mechanical fixes only.")
        return 0

    # Apply only safe, reversible, derived-file fixes; never touch judgment items.
    print("\n## Applying safe mechanical fixes")
    code, last = _run(["python3", "tools/metrics.py"])
    print(f"- metrics regenerated: {last or ('ok' if code == 0 else 'failed')}")
    code, last = _run(["python3", "tools/sync_check.py"])
    print(f"- drift guard: {last}")
    print("\nFinalization status: **safe fixes applied**; "
          f"{len(judgment)} judgment item(s) still need you. Review the diff, then approve/commit.")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
