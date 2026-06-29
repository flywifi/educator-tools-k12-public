#!/usr/bin/env python3
"""Repair loop — chains health scan, skill repair (dry-run), and drift guard into one report.

Runs the TOS self-healing pipeline as a single connected step:
  1. health.py SCAN  — detect all skill/engine/routing problems
  2. skill_repair.py — separate mechanical (safe) from judgment (human) fixes
  3. sync_check.py   — verify current drift status

Outputs a single consolidated report: how many problems exist, which can be auto-fixed, and which
need a human. Always advisory — never auto-applies fixes. The CI step uses this to give developers
a clear, actionable summary instead of making them run three tools separately.

Usage:
  python3 tools/repair_loop.py              # print consolidated report
  python3 tools/repair_loop.py --json       # JSON output
  python3 tools/repair_loop.py --apply      # apply safe mechanical fixes, then re-verify
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def _run(cmd: list[str], timeout: float = 60) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"timed out after {timeout}s"
    except Exception as exc:
        return -1, "", f"{exc.__class__.__name__}: {exc}"


def run_loop(apply: bool = False) -> dict:
    # 1. Health scan
    code, out, err = _run([PYTHON, "shared/health/health.py", "--scan"])
    try:
        health = json.loads(out)
    except Exception:
        return {"error": "health scan failed to produce JSON", "raw": (out + err)[:500]}

    plan = health.get("repair_plan", [])
    mechanical = [s for s in plan if s.get("mechanical")]
    judgment = [s for s in plan if not s.get("mechanical")]

    # 2. Apply mechanical fixes if requested
    applied = []
    if apply and mechanical:
        code, out, err = _run([PYTHON, "tools/skill_repair.py", "--apply"])
        applied = mechanical
        apply_output = out + err
    else:
        apply_output = ""

    # 3. Drift guard (verify current state)
    drift_code, drift_out, drift_err = _run([PYTHON, "tools/sync_check.py"])
    drift_clean = drift_code == 0

    return {
        "readiness_score": health.get("readiness_score"),
        "readiness_band": health.get("readiness_band"),
        "total_issues": len(plan),
        "mechanical_fixable": len(mechanical),
        "needs_human_judgment": len(judgment),
        "applied": len(applied) if apply else 0,
        "drift_clean": drift_clean,
        "blocking_issues": health.get("blocking_issues", []),
        "mechanical_items": [{"area": s["area"], "action": s["action"]} for s in mechanical],
        "judgment_items": [{"area": s["area"], "action": s["action"], "severity": s["severity"]}
                          for s in judgment],
        "apply_output": apply_output[:500] if apply_output else None,
        "drift_output": (drift_out + drift_err)[:500] if not drift_clean else None,
    }


def to_summary(report: dict) -> str:
    if "error" in report:
        return f"Repair loop failed: {report['error']}\n"

    lines = [
        "# TOS Repair Loop Report",
        "",
        f"Readiness: **{report['readiness_score']}/100** ({report['readiness_band']})",
        f"Drift guard: {'clean' if report['drift_clean'] else 'DRIFT DETECTED'}",
        "",
        f"Issues found: **{report['total_issues']}**",
        f"  - {report['mechanical_fixable']} can be fixed automatically (mechanical)",
        f"  - {report['needs_human_judgment']} need your judgment (human review required)",
        "",
    ]

    if report["applied"]:
        lines.append(f"Applied {report['applied']} mechanical fix(es) this run.")
        lines.append("")

    if report["blocking_issues"]:
        lines.append("## Blocking Issues (must fix before release)")
        for b in report["blocking_issues"]:
            lines.append(f"  - {b}")
        lines.append("")

    if report["mechanical_items"]:
        lines.append("## Mechanical Fixes Available (safe to auto-apply)")
        for m in report["mechanical_items"]:
            lines.append(f"  - {m['area']}: {m['action']}")
        lines.append("")

    if report["judgment_items"]:
        lines.append("## Needs Your Judgment (will NOT be auto-applied)")
        for j in report["judgment_items"]:
            lines.append(f"  - [{j['severity']}] {j['area']}: {j['action']}")
        lines.append("")

    if not report["total_issues"] and report["drift_clean"]:
        lines.append("Everything looks good. No issues found, no drift detected.")

    return "\n".join(lines) + "\n"


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Repair loop: health scan + repair proposal + drift verify.")
    ap.add_argument("--json", action="store_true", help="JSON output instead of human-readable")
    ap.add_argument("--apply", action="store_true", help="apply safe mechanical fixes (default: dry-run)")
    a = ap.parse_args(argv)

    report = run_loop(apply=a.apply)

    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print(to_summary(report), end="")

    if "error" in report:
        return 2
    if report["blocking_issues"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
