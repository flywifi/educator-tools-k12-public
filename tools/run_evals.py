#!/usr/bin/env python3
"""Execute the eval cases that CAN be executed, and say honestly which cannot.

WHY THIS EXISTS. 75 eval cases were authored across 18 skills and NONE had ever been run by a
machine. The proof is a case that is false right now: skills/core/skill-health asserts
`readiness_band: "strong"` while `health.py --scan` reports `"not_ready"`. CI's step named
"Validate eval files" ran `json.load()` and nothing else, so a file containing `{}` passed and a
wrong assertion passed too.

WHAT RUNS. Two case kinds are declarative and deterministic, so they execute here:
  kind "command" — run an allow-listed argv, parse stdout as JSON, check `assert`
  kind "call"    — import an in-repo function, pass `input`, check `assert` on its return
A third kind, "prompt", is model-facing. It is NEVER executed here; it is reported as `recorded`
(its evidence lives under benchmarks/) or `unrun`. Pretending otherwise is the failure this tool
exists to end.

SKIPS ARE FINDINGS, NOT PASSES. A case is skipped — and counted, and printed — when its command
carries an unfilled `<placeholder>`, names a fixture that does not exist, needs the network, or
names a tool that is absent. Each skip is a coverage gap someone chose not to close, so it is
visible rather than green.

Exit: 0 when no case FAILED · 1 when any case failed · 2 on usage/shape error.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Only these interpreters/entry points may be spawned. A `command` case is data in a JSON file;
#: without an allow-list, editing an eval file would be arbitrary code execution in CI.
ALLOWED_ARGV0 = {"python3", "python", sys.executable}

#: A command touching one of these is network-bound and never runs in the default mode.
NETWORK_MARKERS = ("http://", "https://", "--discover-from", "--crawl", "--fetch")

PLACEHOLDER = re.compile(r"<[^>]+>")


def _dig(obj, dotted: str):
    """Walk `a.b.c` through nested dicts/lists. Returns (found, value).

    Dotted paths are already in the data — meeting-classifier uses `required_cadence.authority` —
    so the runner must speak them rather than the cases being rewritten to suit the runner.
    """
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False, None
    return True, cur


_OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b, "<": lambda a, b: a < b, "!=": lambda a, b: a != b}


def check_one(actual, expected):
    """Compare one assertion. Returns (ok, explanation).

    Grammar kept deliberately small because the committed data is small: 82 assertions, of which
    56 are strings, 19 bools, 5 lists, 1 int, 1 null — and exactly ONE comparison expression
    (`">=1"`). Anything richer would be inventing a language no case uses.
    """
    if isinstance(expected, str):
        for op, fn in _OPS.items():
            if expected.startswith(op):
                rhs = expected[len(op):].strip()
                try:
                    lhs = len(actual) if isinstance(actual, (list, dict)) else float(actual)
                    ok = fn(lhs, float(rhs))
                except (TypeError, ValueError):
                    return False, f"cannot compare {actual!r} {op} {rhs!r}"
                return ok, f"{lhs} {op} {rhs}"
    if isinstance(expected, list):
        # order-insensitive: these are membership sets in every committed case
        ok = isinstance(actual, list) and sorted(map(str, actual)) == sorted(map(str, expected))
        return ok, f"list {actual!r} vs {expected!r}"
    if isinstance(expected, bool):
        # bool BEFORE int: isinstance(True, int) is True, so 1 would satisfy a `true` assertion
        return actual is expected, f"{actual!r} is {expected!r}"
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return actual == expected, f"{actual!r} == {expected!r}"
    return actual == expected, f"{actual!r} == {expected!r}"


def _skip_reason(cmd: str) -> str | None:
    """Why this command cannot honestly be executed — or None if it can."""
    if PLACEHOLDER.search(cmd):
        return f"unfilled placeholder {PLACEHOLDER.search(cmd).group(0)} — the case was authored " \
               f"against a fixture that was never created"
    if any(m in cmd for m in NETWORK_MARKERS):
        return "needs network; this runner is offline by default (pass --allow-network to run it)"
    parts = shlex.split(cmd)
    if not parts:
        return "empty command"
    if parts[0] not in ALLOWED_ARGV0:
        return f"interpreter {parts[0]!r} is not in the allow-list"
    for tok in parts[1:]:
        if tok.startswith("-"):
            continue
        p = ROOT / tok
        if tok.endswith((".py",)) and not p.exists():
            return f"script not found: {tok}"
        if tok.endswith((".pptx", ".pdf", ".docx", ".json")) and not p.exists():
            return f"fixture not found: {tok}"
    return None


def run_command_case(case: dict, allow_network: bool) -> dict:
    cmd = case.get("command", "")
    reason = _skip_reason(cmd)
    if reason and not (allow_network and "needs network" in reason):
        return {"status": "skip", "why": reason}
    argv = shlex.split(cmd)
    argv[0] = sys.executable                      # never spawn a bare name (mac_audit check 19)
    try:
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
    except Exception as e:
        return {"status": "fail", "why": f"{e.__class__.__name__}: {e}"}
    asserts = case.get("assert") or {}
    text_only = {"stdout_contains", "exit_code"}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        # A tool that emits prose (skill_repair emits markdown) can still be asserted on, but ONLY
        # with the text forms. A case asserting structured keys against a prose tool is not a
        # runner bug — it is a case that was never executable, and it is reported as such.
        if not set(asserts) <= text_only:
            structured = sorted(set(asserts) - text_only)
            return {"status": "unrunnable",
                    "why": f"tool emits non-JSON stdout but the case asserts structured key(s) "
                           f"{structured} — the case needs a --json mode on the tool, or to be "
                           f"reclassified; exit was {proc.returncode}"}
        payload = {}
    return _apply_asserts(payload, asserts, stdout=proc.stdout, exit_code=proc.returncode)


def run_call_case(case: dict) -> dict:
    """`call` cases name an in-repo dotted target, e.g. "routing.router:atom_route"."""
    target = case.get("call")
    if not target or ":" not in target:
        return {"status": "skip", "why": "no `call` target"}
    modpath, fname = target.split(":", 1)
    sys.path[:0] = [str(ROOT / "shared"), str(ROOT / "tools")]
    try:
        mod = __import__(modpath, fromlist=[fname])
        fn = getattr(mod, fname)
    except Exception as e:
        return {"status": "skip", "why": f"cannot import {target}: {e.__class__.__name__}: {e}"}
    try:
        arg = case.get("input")
        out = fn(**arg) if isinstance(arg, dict) and case.get("kwargs") else fn(arg)
    except Exception as e:
        return {"status": "fail", "why": f"{target} raised {e.__class__.__name__}: {e}"}
    return _apply_asserts(out, case.get("assert") or {})


def _apply_asserts(payload, asserts: dict, stdout: str = "", exit_code=None) -> dict:
    """Apply one case's assertions.

    Beyond plain and dotted keys, three forms appear in (or are needed by) the committed data:
      has: [k, ...]            every key present on the payload   (feed-curator uses this today)
      each.<listkey>: [k, ...] every item of that list has those keys (feed-curator's
                               `each_report_has` generalised, so the DSL is not per-author)
      stdout_contains: [s, ...]  substring of raw stdout — the only honest way to assert on a
                               tool that emits prose rather than JSON
      exit_code: N
    """
    if not asserts:
        return {"status": "skip", "why": "no `assert` block"}
    bad = []
    for key, expected in asserts.items():
        if key == "has":
            missing = [k for k in expected if not _dig(payload, k)[0]]
            if missing:
                bad.append(f"has: missing {missing}")
            continue
        if key == "stdout_contains":
            missing = [s for s in expected if s not in stdout]
            if missing:
                bad.append(f"stdout_contains: missing {missing}")
            continue
        if key == "exit_code":
            if exit_code != expected:
                bad.append(f"exit_code: {exit_code} == {expected}")
            continue
        if key.startswith("each."):
            listkey = key[len("each."):]
            found, items = _dig(payload, listkey)
            if not found or not isinstance(items, list):
                bad.append(f"each.{listkey}: no such list on the output")
                continue
            for i, item in enumerate(items):
                miss = [k for k in expected if not _dig(item, k)[0]]
                if miss:
                    bad.append(f"each.{listkey}[{i}]: missing {miss}")
                    break
            continue
        found, actual = _dig(payload, key)
        if not found:
            bad.append(f"{key}: MISSING from output")
            continue
        ok, how = check_one(actual, expected)
        if not ok:
            bad.append(f"{key}: {how}")
    return {"status": "pass"} if not bad else {"status": "fail", "why": "; ".join(bad)}


def kind_of(case: dict) -> str:
    """The case's kind, inferred when not declared, so the 4 legacy dialects run unmigrated."""
    if case.get("kind"):
        return case["kind"]
    if "command" in case:
        return "command"
    if "call" in case:
        return "call"
    if "input" in case and "assert" in case:
        return "call_legacy"     # Dialect C: an input+assert with no callable named yet
    return "prompt"              # Dialects A/D: model-facing


def collect() -> list:
    out = []
    for f in sorted(glob.glob(str(ROOT / "skills/**/evals/evals.json"), recursive=True)):
        rel = Path(f).relative_to(ROOT).as_posix()
        skill = Path(f).parts[-3]
        try:
            doc = json.loads(Path(f).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            out.append({"skill": skill, "file": rel, "case": {"name": "<file>"},
                        "kind": "broken", "why": f"unparseable: {e}"})
            continue
        for i, case in enumerate(doc.get("evals") or []):
            out.append({"skill": skill, "file": rel, "case": case, "kind": kind_of(case),
                        "label": case.get("name") or case.get("id") or f"#{i}"})
    return out


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Run the executable eval cases.")
    ap.add_argument("--run", action="store_true", help="execute command/call cases")
    ap.add_argument("--check", action="store_true", help="shape only; execute nothing (CI default)")
    ap.add_argument("--allow-network", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()

    cases = collect()
    tally = {"pass": 0, "fail": 0, "skip": 0, "unrunnable": 0, "prompt": 0, "broken": 0}
    failures = []
    for c in cases:
        k, label = c["kind"], f"{c['skill']}/{c['label']}"
        if k == "broken":
            tally["broken"] += 1
            failures.append(f"  FAIL {label}: {c['why']}")
            continue
        if k == "prompt":
            tally["prompt"] += 1
            continue
        if a.check or not a.run:
            continue
        res = run_command_case(c["case"], a.allow_network) if k == "command" else run_call_case(c["case"])
        tally[res["status"]] += 1
        mark = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP",
                "unrunnable": "UNRUNNABLE"}[res["status"]]
        line = f"  {mark} {label}" + (f" — {res.get('why')}" if res.get("why") else "")
        print(line)
        if res["status"] == "fail":
            failures.append(line)

    ran = tally["pass"] + tally["fail"]
    print(f"\neval cases: {len(cases)} total\n"
          f"  executed        {ran:3d}  (pass {tally['pass']}, FAIL {tally['fail']})\n"
          f"  skipped         {tally['skip']:3d}  (placeholder / missing fixture / network)\n"
          f"  UNRUNNABLE      {tally['unrunnable']:3d}  (case asserts keys the tool never emits)\n"
          f"  model-facing    {tally['prompt']:3d}  (never executed here; see benchmarks/)")
    if tally["skip"]:
        print(f"note: {tally['skip']} executable case(s) could not run — each is a coverage gap, "
              f"not a pass. See the SKIP lines above.")
    if failures:
        print("\nFAILURES:\n" + "\n".join(failures))
        return 1
    return 0


def _self_test() -> int:
    fails = 0

    def ck(label, cond):
        nonlocal fails
        print(f"{'PASS' if cond else 'FAIL'} {label}")
        if not cond:
            fails += 1

    ck("dotted path resolves", _dig({"a": {"b": {"c": 7}}}, "a.b.c") == (True, 7))
    ck("dotted path reports MISSING rather than None", _dig({"a": {}}, "a.z") == (False, None))
    ck("list index in a dotted path", _dig({"r": [{"x": 1}]}, "r.0.x") == (True, 1))
    ck("bool is checked by identity, so 1 does NOT satisfy true",
       check_one(1, True)[0] is False)
    ck("true satisfies true", check_one(True, True)[0] is True)
    ck("the one comparison form in the data ('>=1') works",
       check_one(3, ">=1")[0] is True and check_one(0, ">=1")[0] is False)
    ck("'>=1' counts a LIST by length", check_one([1, 2], ">=1")[0] is True)
    ck("list compare is order-insensitive",
       check_one(["B", "A"], ["A", "B"])[0] is True)
    ck("string equality", check_one("iep_meeting", "iep_meeting")[0] is True)
    ck("string inequality is a failure", check_one("x", "y")[0] is False)
    ck("placeholder command is SKIPPED, never passed",
       "placeholder" in (_skip_reason("python3 tools/x.py --traces <saved-traces>") or ""))
    ck("network command is skipped by default",
       "network" in (_skip_reason("python3 tools/seed_curator.py --discover-from https://example.com/x") or ""))
    ck("missing fixture is skipped with the filename",
       "truncated.pptx" in (_skip_reason("python3 tools/validate_document.py truncated.pptx") or ""))
    ck("non-allow-listed interpreter is refused",
       "allow-list" in (_skip_reason("bash -c 'rm -rf /'") or ""))
    ck("a real runnable command is NOT skipped",
       _skip_reason("python3 shared/health/health.py --scan") is None)
    ck("missing assert key fails loudly",
       _apply_asserts({"a": 1}, {"b": 2})["status"] == "fail")
    ck("empty assert block is a skip, not a pass",
       _apply_asserts({"a": 1}, {})["status"] == "skip")
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
