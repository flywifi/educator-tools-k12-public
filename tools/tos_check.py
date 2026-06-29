#!/usr/bin/env python3
"""tos_check — TOS ecosystem health check orchestrator.

Runs every available read-only / offline-safe TOS diagnostic tool in sequence, captures output
and exit codes, and writes a consolidated tos_report.json + tos_report.md summary.

Usage:
  python3 tools/tos_check.py                          # full check, print summary table
  python3 tools/tos_check.py --out reports/           # also save tos_report.json + tos_report.md
  python3 tools/tos_check.py --quiet                  # JSON only, no console progress
  python3 tools/tos_check.py --skip feeds,render      # skip named check groups
  python3 tools/tos_check.py --only drift,caps        # run only named groups
  python3 tools/tos_check.py --timeout 60             # per-check timeout in seconds (default 30)
  python3 tools/tos_check.py --out reports/ --open    # open tos_report.md after writing

Check groups (run in this order):
  drift     — python3 tools/sync_check.py (CRITICAL: fail → overall=fail)
  version   — python3 tools/version.py --check
  caps      — python3 shared/health/capabilities.py --json
  render    — python3 tools/render_fetch.py --check
  feeds     — python3 tools/feeds_update.py --status
  cache     — python3 shared/cache/cache.py --stats
  seeds     — python3 tools/seed_curator.py --validate
  registry  — python3 tools/registry_currency.py
  sources   — python3 tools/source_currency.py --summary
  security  — python3 tools/security_scan.py (skipped if absent)

Output is always advisory — this tool never modifies any files. Exit code: 0=pass, 1=warn, 2=fail.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = sys.executable  # reuse the same Python interpreter

# --------------------------------------------------------------------------- check definitions
# Each entry: (group_name, command_parts, is_critical, output_note_fn)
# is_critical=True means a non-zero exit sets overall status to FAIL (not just WARN).
# output_note_fn(stdout, stderr) -> str | None  extracts a short human note from the output.

def _caps_note(out: str, err: str) -> str | None:
    """Extract capability gap count from capabilities.py --json output."""
    try:
        data = json.loads(out)
        gaps = [k for k, v in data.items() if not v.get("available", True)]
        return f"{len(gaps)} gap(s): {', '.join(gaps[:4])}" if gaps else "all capabilities present"
    except Exception:
        return None


def _render_note(out: str, err: str) -> str | None:
    lines = [l.strip() for l in out.splitlines() if "available" in l.lower() or "unavailable" in l.lower()]
    avail = sum(1 for l in lines if "available " in l and "unavailable" not in l)
    total = len(lines)
    return f"{avail}/{total} prongs available" if total else None


def _feeds_note(out: str, err: str) -> str | None:
    for kw in ("no database", "no feeds", "0 feed"):
        if kw in out.lower():
            return "no feed DB yet — run feeds_update.py --update"
    if "due" in out.lower():
        due = sum(1 for l in out.splitlines() if "due" in l.lower())
        return f"{due} feed(s) due for update" if due else None
    return None


def _sources_note(out: str, err: str) -> str | None:
    uncertain = out.lower().count("uncertain")
    if uncertain:
        return f"{uncertain} source(s) uncertain — run source_currency.py --update-baselines"
    return None


def _repair_note(out: str, err: str) -> str | None:
    for line in out.splitlines():
        if "Issues found:" in line:
            return line.strip().replace("**", "")
    return None


CHECKS: list[tuple[str, list[str], bool, object]] = [
    ("drift",    [TOOL, "tools/sync_check.py"],                          True,  None),
    ("version",  [TOOL, "tools/version.py", "--check"],                  False, None),
    ("caps",     [TOOL, "shared/health/capabilities.py", "--json"],      False, _caps_note),
    ("render",   [TOOL, "tools/render_fetch.py", "--check"],             False, _render_note),
    ("feeds",    [TOOL, "tools/feeds_update.py", "--status"],            False, _feeds_note),
    ("cache",    [TOOL, "shared/cache/cache.py", "--stats"],             False, None),
    ("seeds",    [TOOL, "tools/seed_curator.py", "--validate"],          False, None),
    ("registry", [TOOL, "tools/registry_currency.py"],                   False, None),
    ("sources",  [TOOL, "tools/source_currency.py", "--summary"],        False, _sources_note),
    ("security", [TOOL, "tools/security_scan.py"],                       False, None),
    ("repair",   [TOOL, "tools/repair_loop.py"],                         False, _repair_note),
]

CHECK_NAMES = [c[0] for c in CHECKS]

MAX_OUTPUT_CHARS = 4000  # cap stored output per check to keep JSON manageable


# --------------------------------------------------------------------------- action-item inference
def _infer_action_items(results: dict) -> list[str]:
    items = []
    if results.get("drift", {}).get("status") == "fail":
        items.append("URGENT: fix sync_check.py drift before any other changes")
    caps_out = results.get("caps", {}).get("output", "")
    try:
        caps_data = json.loads(caps_out)
        gaps = [k for k, v in caps_data.items() if not v.get("available", True)]
        if gaps:
            items.append(f"Install missing capabilities: {', '.join(gaps)} "
                         "(see tools/requirements-*.txt for each)")
    except Exception:
        pass
    if results.get("sources", {}).get("status") in ("warn", "fail"):
        items.append("Run source_currency.py --update-baselines on open-net machine to seed F2 baselines")
    feeds_out = results.get("feeds", {}).get("output", "")
    if "no database" in feeds_out.lower() or "no feed" in feeds_out.lower():
        items.append("Run tools/feeds_update.py --update to harvest initial feed items")
    cache_out = results.get("cache", {}).get("output", "")
    if "not built" in cache_out.lower() or "no rows" in cache_out.lower() or "empty" in cache_out.lower():
        items.append("Run shared/cache/cache.py --build to index the standards corpus")
    if results.get("security", {}).get("status") == "fail":
        items.append("Review tools/security_scan.py output and address flagged issues")
    return items


# --------------------------------------------------------------------------- markdown report
def _make_markdown(ts: str, branch: str, overall: str, results: dict,
                   action_items: list[str]) -> str:
    status_icon = {"pass": "✅ PASS", "warn": "⚠️ WARN", "fail": "❌ FAIL",
                   "skipped": "— skip"}.get(overall, overall)
    lines = [
        f"# TOS Health Check — {ts[:10]}",
        f"",
        f"**Branch:** `{branch}` | **Overall:** {status_icon}",
        f"",
        "## Check Results",
        "",
        "| Check | Status | Duration | Notes |",
        "|---|---|---|---|",
    ]
    for name in CHECK_NAMES:
        r = results.get(name)
        if not r:
            continue
        s = r["status"]
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skipped": "—"}.get(s, s)
        dur = f"{r.get('duration_ms', 0)/1000:.1f}s"
        note = r.get("note", "") or ""
        lines.append(f"| `{name}` | {icon} {s} | {dur} | {note} |")

    if action_items:
        lines += ["", "## Action Items", ""]
        for i, item in enumerate(action_items, 1):
            lines.append(f"{i}. {item}")

    caps_out = results.get("caps", {}).get("output", "")
    if caps_out.strip().startswith("{"):
        lines += ["", "## Capability Inventory", "", "```json", caps_out[:3000], "```"]

    lines += ["", f"*Generated by `tools/tos_check.py` at {ts}*"]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="TOS ecosystem health check orchestrator.")
    ap.add_argument("--out", metavar="DIR", help="write tos_report.json + tos_report.md here")
    ap.add_argument("--quiet", action="store_true", help="suppress console progress; JSON report only")
    ap.add_argument("--skip", metavar="GROUPS", help="comma-separated check groups to skip")
    ap.add_argument("--only", metavar="GROUPS", help="run only these comma-separated groups")
    ap.add_argument("--timeout", type=float, default=30.0, help="per-check timeout in seconds (default 30)")
    ap.add_argument("--open", action="store_true", dest="open_md",
                    help="open tos_report.md after writing (--out required)")
    a = ap.parse_args(argv)

    skip_set = {g.strip() for g in a.skip.split(",")} if a.skip else set()
    only_set = {g.strip() for g in a.only.split(",")} if a.only else set()

    ts = datetime.now(timezone.utc).isoformat()

    # Detect git branch (advisory; graceful if git unavailable)
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT,
            stderr=subprocess.DEVNULL, text=True).strip() or "unknown"
    except Exception:
        branch = "unknown"

    if not a.quiet:
        print(f"TOS health check — branch: {branch}")
        print(f"Timeout per check: {a.timeout}s\n")

    results: dict[str, dict] = {}
    overall = "pass"

    for group, cmd, is_critical, note_fn in CHECKS:
        if only_set and group not in only_set:
            continue
        if group in skip_set:
            results[group] = {"status": "skipped", "exit_code": None, "duration_ms": 0,
                               "output": "", "error": "", "note": "skipped by --skip"}
            if not a.quiet:
                print(f"  — {group:<12} skipped")
            continue

        # Skip if the script doesn't exist
        script = ROOT / cmd[1] if len(cmd) > 1 else None
        if script and not script.exists():
            results[group] = {"status": "skipped", "exit_code": None, "duration_ms": 0,
                               "output": "", "error": "", "note": f"{cmd[1]} not found"}
            if not a.quiet:
                print(f"  — {group:<12} skipped ({cmd[1]} not found)")
            continue

        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=a.timeout, cwd=ROOT)
            duration_ms = int((time.monotonic() - t0) * 1000)
            stdout = proc.stdout[:MAX_OUTPUT_CHARS]
            stderr = proc.stderr[:1000]
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            duration_ms = int(a.timeout * 1000)
            stdout, stderr, exit_code = "", f"timed out after {a.timeout}s", -1
        except Exception as e:
            duration_ms = int((time.monotonic() - t0) * 1000)
            stdout, stderr, exit_code = "", str(e), -1

        # Derive status
        if exit_code == 0:
            status = "pass"
        elif exit_code == -1 and "timed out" in stderr:
            status = "warn"
        elif is_critical and exit_code != 0:
            status = "fail"
            overall = "fail"
        else:
            status = "warn"
            if overall == "pass":
                overall = "warn"

        note = (note_fn(stdout, stderr) if note_fn else None) or ""
        if "timed out" in stderr:
            note = f"timed out after {a.timeout}s"

        results[group] = {
            "status": status,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "output": stdout,
            "error": stderr,
            "note": note,
        }

        if not a.quiet:
            icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skipped": "—"}.get(status, status)
            print(f"  {icon} {group:<12} {status:<6}  {duration_ms:>5}ms  {note}")

    action_items = _infer_action_items(results)
    passed = sum(1 for r in results.values() if r["status"] == "pass")
    warned = sum(1 for r in results.values() if r["status"] == "warn")
    failed = sum(1 for r in results.values() if r["status"] == "fail")
    skipped = sum(1 for r in results.values() if r["status"] == "skipped")

    # Extract capability gaps for the summary
    cap_gaps: list[str] = []
    try:
        cap_gaps = [k for k, v in json.loads(results.get("caps", {}).get("output", "{}")).items()
                    if not v.get("available", True)]
    except Exception:
        pass

    report = {
        "timestamp": ts,
        "branch": branch,
        "overall": overall,
        "checks": results,
        "summary": {
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "skipped": skipped,
            "capability_gaps": cap_gaps,
            "action_items": action_items,
        },
    }

    if not a.quiet:
        print(f"\nOverall: {overall.upper()}  "
              f"({passed} passed, {warned} warned, {failed} failed, {skipped} skipped)")
        if action_items:
            print("\nAction items:")
            for i, item in enumerate(action_items, 1):
                print(f"  {i}. {item}")

    if a.out:
        out_dir = Path(a.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "tos_report.json"
        md_path = out_dir / "tos_report.md"
        json_path.write_text(json.dumps(report, indent=2))
        md_path.write_text(_make_markdown(ts, branch, overall, results, action_items))
        if not a.quiet:
            print(f"\nSaved: {json_path}")
            print(f"Saved: {md_path}")
        if a.open_md:
            import subprocess as _sp
            _sp.run(["open" if sys.platform == "darwin" else "xdg-open", str(md_path)],
                    check=False)
    else:
        print(json.dumps(report, indent=2))

    return {"pass": 0, "warn": 1, "fail": 2}.get(overall, 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
