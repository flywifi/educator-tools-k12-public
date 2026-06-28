#!/usr/bin/env python3
"""local_harvest — token-free, run-on-your-own-machine school data harvester.

WHY THIS EXISTS
  The Claude Code web sandbox runs behind an allowlist egress policy (only GitHub +
  package registries are reachable), so it CANNOT fetch ocps.net / fldoe.org. Your
  laptop has normal internet. This script is the bridge: you run it locally, it does
  all the network + parsing work with PLAIN PYTHON (no LLM, no API key, zero tokens),
  writes the results into the repo, and pushes them to the feature branch. Next time
  Claude opens the repo it reads the harvested data + the report you pushed — that is
  how the work "reports back" without spending tokens.

WHAT IT DOES (deterministic, offline-first, idempotent)
  1. msid_lookup.py --fetch         download the FLDOE Master School ID file (once, cached)
  2. msid_lookup.py --match --apply  stamp real 6-digit MSIDs onto every district's schools.json
  3. ocps_resources.py --fetch       crawl OCPS public pages -> districts/ocps/resources.json
  4. write HARVEST_REPORT.md         a plain-text summary of what changed (match rates, gaps)
  5. (optional) git commit + push    so the results reach Claude with no tokens spent

EVERYTHING here is stdlib + the two scraper tools already in this repo. No model calls.

USAGE (on your own computer, inside the repo)
  python3 tools/local_harvest.py                      # harvest all 7 districts, write report, DON'T push
  python3 tools/local_harvest.py --district 48        # just OCPS
  python3 tools/local_harvest.py --push               # also git add+commit+push to the current branch
  python3 tools/local_harvest.py --district 48 --push # OCPS only, then push
  python3 tools/local_harvest.py --no-resources       # skip the OCPS page crawl (MSID matching only)

Network is required (this is the whole point — run it where ocps.net/fldoe.org are reachable).
If a fetch fails, the step degrades to a gap in the report; it never fabricates data.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
SCHOOLS_DIR = ROOT / "canonical-sources" / "schools"
REPORT = ROOT / "HARVEST_REPORT.md"

DISTRICTS = {
    "48": "ocps", "59": "seminole", "49": "osceola",
    "35": "lake", "05": "brevard", "64": "volusia", "53": "polk",
}


def _run(cmd: list[str], capture: bool = True) -> tuple[int, str]:
    """Run a subprocess, return (returncode, combined_output)."""
    print(f"  $ {' '.join(cmd)}", file=sys.stderr)
    try:
        r = subprocess.run(
            cmd, cwd=str(ROOT),
            capture_output=capture, text=True, timeout=600,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after 600s"
    except Exception as e:
        return 1, f"ERROR: {e}"


def _district_stats(alias: str) -> dict:
    """Count schools and how many carry a real (non-placeholder) MSID."""
    path = SCHOOLS_DIR / alias / "schools.json"
    if not path.exists():
        return {"file": str(path), "exists": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    schools = data.get("schools", [])
    real = sum(1 for s in schools
               if s.get("msid") and "X" not in str(s["msid"]).upper() and len(str(s["msid"])) == 6)
    return {
        "exists": True,
        "total": len(schools),
        "real_msid": real,
        "placeholder_msid": len(schools) - real,
        "completeness": data.get("completeness"),
    }


def harvest(districts: list[str], do_resources: bool, do_push: bool) -> None:
    started = datetime.now(timezone.utc).isoformat()
    log: list[str] = []

    def note(msg: str) -> None:
        print(msg, file=sys.stderr)
        log.append(msg)

    note(f"# Local harvest started {started}")

    # --- Step 1: fetch the FLDOE MSID file (once) -------------------------------
    note("\n## Step 1 - fetch FLDOE Master School ID file")
    rc, out = _run([sys.executable, str(TOOLS / "msid_lookup.py"), "--fetch"])
    note(f"  exit={rc}")
    msid_ok = rc == 0
    if not msid_ok:
        note("  MSID auto-fetch FAILED (FLDOE relocates this file yearly and blocks bots).")
        note("  RELIABLE PATH: download the 'Master School Identification File' in a browser from")
        note("    https://www.fldoe.org/accountability/data-sys/school-fin-data/master-school-id-files.stml")
        note("  then re-run, e.g.:")
        note("    python3 tools/msid_lookup.py --match --district 48 --apply --confirm \\")
        note("      --msid-file C:\\path\\to\\MasterSchoolID.csv")
        note("  " + (out.strip().splitlines()[-1] if out.strip() else ""))

    # --- Step 2: match + apply MSIDs per district -------------------------------
    before = {DISTRICTS[d]: _district_stats(DISTRICTS[d]) for d in districts if d in DISTRICTS}

    if msid_ok:
        note("\n## Step 2 - match + apply real MSIDs")
        for d in districts:
            alias = DISTRICTS.get(d)
            if not alias:
                note(f"  unknown district {d}, skipping")
                continue
            rc, out = _run([
                sys.executable, str(TOOLS / "msid_lookup.py"),
                "--match", "--district", d, "--apply", "--confirm",
            ])
            tail = out.strip().splitlines()[-1] if out.strip() else ""
            note(f"  {alias} (district {d}): exit={rc}  {tail}")
    else:
        note("\n## Step 2 - SKIPPED (no MSID file)")

    after = {DISTRICTS[d]: _district_stats(DISTRICTS[d]) for d in districts if d in DISTRICTS}

    # --- Step 3: OCPS resources crawl (only if OCPS in scope) -------------------
    if do_resources and "48" in districts:
        note("\n## Step 3 - crawl OCPS public resource pages")
        rc, out = _run([sys.executable, str(TOOLS / "ocps_resources.py"), "--fetch"])
        note(f"  exit={rc}")
        if rc != 0 and out.strip():
            note("  " + out.strip().splitlines()[-1])
    else:
        note("\n## Step 3 - resources crawl skipped")

    # --- Step 4: write the report -----------------------------------------------
    note("\n## Step 4 - write HARVEST_REPORT.md")
    lines = [
        "# School Data Harvest Report",
        "",
        f"- **Run (UTC):** {started}",
        f"- **Host:** local machine (token-free deterministic run)",
        f"- **MSID file fetched:** {'yes' if msid_ok else 'NO — fetch failed'}",
        f"- **Districts processed:** {', '.join(DISTRICTS[d] for d in districts if d in DISTRICTS)}",
        "",
        "## MSID coverage (before vs after)",
        "",
        "| District | Schools | Real MSID before | Real MSID after | Still placeholder |",
        "|---|---|---|---|---|",
    ]
    for d in districts:
        alias = DISTRICTS.get(d)
        if not alias or not after.get(alias, {}).get("exists"):
            continue
        b, a = before[alias], after[alias]
        lines.append(
            f"| {alias} ({d}) | {a['total']} | {b.get('real_msid', 0)} | "
            f"{a.get('real_msid', 0)} | {a.get('placeholder_msid', 0)} |"
        )
    lines += [
        "",
        "## Run log",
        "",
        "```",
        *log,
        "```",
        "",
        "> Generated by `tools/local_harvest.py` — no model tokens were used. "
        "All data is from FLDOE MSID + OCPS public pages; every record keeps its "
        "`source`/`verified` provenance. `human_review_required: true`.",
        "",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    note(f"  wrote {REPORT}")

    # --- Step 5: optional push --------------------------------------------------
    if do_push:
        note("\n## Step 5 - commit + push (token-free report-back channel)")
        rc, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        branch = branch.strip() or "HEAD"
        _run(["git", "add",
              "canonical-sources/schools", "canonical-sources/districts", str(REPORT)],
             capture=True)
        msg = (
            "data(schools): local harvest — real MSIDs + OCPS resources\n\n"
            f"Deterministic local run ({started}). FLDOE MSID matching + OCPS page crawl. "
            "No model tokens used. See HARVEST_REPORT.md for coverage."
        )
        rc, out = _run(["git", "commit", "-m", msg])
        if rc != 0 and "nothing to commit" in out.lower():
            note("  nothing changed — no commit needed.")
        else:
            note(f"  commit exit={rc}")
            rc, out = _run(["git", "push", "-u", "origin", branch])
            note(f"  push exit={rc} (branch {branch})")
            if rc == 0:
                note("  [OK] Pushed. Claude will read HARVEST_REPORT.md + updated JSON next session.")
    else:
        note("\n## Step 5 - push skipped (run with --push to report back to Claude)")

    note("\n# Done.")
    print("\n" + "=" * 60)
    print(f"Harvest complete. Report: {REPORT}")
    if not do_push:
        print("Re-run with --push to send results back to Claude (no tokens).")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--district", help="District number(s), comma-separated (default: all 7)")
    p.add_argument("--no-resources", action="store_true", help="Skip the OCPS page crawl")
    p.add_argument("--push", action="store_true",
                   help="git add+commit+push results to the current branch (reports back to Claude)")
    args = p.parse_args(argv)

    if args.district:
        districts = [d.strip().zfill(2) for d in args.district.split(",") if d.strip()]
    else:
        districts = list(DISTRICTS.keys())

    harvest(districts, do_resources=not args.no_resources, do_push=args.push)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
