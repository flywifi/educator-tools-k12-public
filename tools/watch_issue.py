#!/usr/bin/env python3
"""Turn a weekly watcher report into ONE GitHub issue someone actually reads.

WHY (R2, 2026-11): platform-watch ran detect-only for nine weeks and reported the same 11 vendor
changes every Monday into a run summary nobody opened; feed-watch had the same shape. This keeps
a single open issue per watcher (found by its label): created when the report has findings,
its body replaced on every run while findings remain, closed with a comment when a run comes back
clean. GitHub notifies the repository's watchers on create — the alert reaches a person.

Usage (in a workflow step, GH_TOKEN set, `gh` is preinstalled on GitHub runners):
  python3 tools/watch_issue.py --report watch.out --label platform-watch \
      --title "Vendor platform changes to review" --findings '^(NEW|ERROR)\b'
  python3 tools/watch_issue.py --self-test     # offline, with a stub gh on PATH
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_BODY = 60000   # GitHub caps an issue body at 65,536 characters


def _gh(args: list[str], input_text: str | None = None) -> str:
    r = subprocess.run(["gh", *args], input=input_text, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"watch_issue: gh {' '.join(args[:2])} failed: {r.stderr.strip()[-400:]}")
    return r.stdout


def run(report: str, label: str, title: str, findings_re: str, run_url: str = "") -> str:
    text = Path(report).read_text(encoding="utf-8", errors="replace")
    hits = [l for l in text.splitlines() if re.search(findings_re, l)]
    open_issues = json.loads(_gh(["issue", "list", "--label", label, "--state", "open",
                                  "--json", "number", "--limit", "5"]) or "[]")
    number = open_issues[0]["number"] if open_issues else None
    if not hits:
        if number is None:
            return "clean: no open issue, nothing to do"
        _gh(["issue", "close", str(number), "--comment",
             f"This week's run came back clean{(' (' + run_url + ')') if run_url else ''}. Closing."])
        return f"clean: closed #{number}"
    body = (f"The weekly `{label}` run found {len(hits)} item(s) to review"
            f"{(' — [run log](' + run_url + ')') if run_url else ''}.\n\n"
            "Close this issue by acting on the findings (update the record they describe, then "
            "commit). It closes itself after the next clean run.\n\n"
            "```text\n" + text[-MAX_BODY:] + "\n```\n")
    if number is None:
        _gh(["label", "create", label, "--color", "BFD4F2", "--force",
             "--description", f"Opened by the weekly {label} workflow"])
        _gh(["issue", "create", "--title", title, "--label", label, "--body-file", "-"], body)
        return f"findings: created issue ({len(hits)} item(s))"
    _gh(["issue", "edit", str(number), "--body-file", "-"], body)
    return f"findings: updated #{number} ({len(hits)} item(s))"


def self_test() -> int:
    import tempfile
    fails = 0

    def ck(name, ok):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    with tempfile.TemporaryDirectory(prefix="wi-") as td:
        td = Path(td)
        log, state = td / "gh.log", td / "open.json"
        stub = td / "gh"
        stub.write_text(
            "#!/usr/bin/env python3\nimport sys, json, pathlib\n"
            f"log = pathlib.Path({str(log)!r}); state = pathlib.Path({str(state)!r})\n"
            "a = sys.argv[1:]; stdin = sys.stdin.read() if '-' in a else ''\n"
            "log.open('a').write(json.dumps({'args': a, 'stdin': stdin[:80]}) + '\\n')\n"
            "if a[:2] == ['issue', 'list']: print(state.read_text() if state.exists() else '[]')\n"
            "elif a[:2] == ['issue', 'create']: state.write_text(json.dumps([{'number': 7}]))\n"
            "elif a[:2] == ['issue', 'close']: state.write_text('[]')\n", encoding="utf-8")
        stub.chmod(0o755)
        os.environ["PATH"] = f"{td}{os.pathsep}{os.environ.get('PATH', '')}"
        rep = td / "watch.out"
        calls = lambda: [json.loads(l)["args"] for l in log.read_text(encoding="utf-8").splitlines()]
        rep.write_text("same    a\nNEW     b: 'x' -> 'y'\n", encoding="utf-8")
        r1 = run(str(rep), "platform-watch", "Vendor changes", r"^(NEW|ERROR)\b")
        ck("findings + no open issue -> label ensured, issue created", r1.startswith("findings: created")
           and ["issue", "create"] == calls()[-1][:2] and any(c[:2] == ["label", "create"] for c in calls()))
        r2 = run(str(rep), "platform-watch", "Vendor changes", r"^(NEW|ERROR)\b")
        ck("findings + open issue -> body replaced, no duplicate", r2 == "findings: updated #7 (1 item(s))"
           and calls()[-1][:3] == ["issue", "edit", "7"])
        rep.write_text("same    a\nsame    b\n", encoding="utf-8")
        r3 = run(str(rep), "platform-watch", "Vendor changes", r"^(NEW|ERROR)\b", "local-run-1")
        ck("clean run + open issue -> closed with a comment", r3 == "clean: closed #7"
           and calls()[-1][:3] == ["issue", "close", "7"])
        r4 = run(str(rep), "platform-watch", "Vendor changes", r"^(NEW|ERROR)\b")
        ck("clean run + no issue -> nothing", r4.startswith("clean: no open issue"))
        rep.write_text("x\n" * 100 + "| `ed-gov-news` | unreachable | 403 |\n3 need a look\n", encoding="utf-8")
        state.write_text("[]", encoding="utf-8")
        r5 = run(str(rep), "feed-watch", "Feed catalog", r"\b[1-9][0-9]* need a look\b")
        ck("feed-watch pattern: 'N need a look' (N>0) opens an issue", r5.startswith("findings: created"))
        rep.write_text("12 feeds checked: 12 healthy, 0 need a look.\n", encoding="utf-8")
        ck("feed-watch pattern: '0 need a look' is clean",
           run(str(rep), "feed-watch", "Feed catalog", r"\b[1-9][0-9]* need a look\b").startswith("clean"))
    print(f"watch_issue self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Open/update/close one GitHub issue from a watcher report")
    ap.add_argument("--report"); ap.add_argument("--label"); ap.add_argument("--title")
    ap.add_argument("--findings", help="regex; any matching report line counts as a finding")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not (a.report and a.label and a.title and a.findings):
        ap.error("--report, --label, --title and --findings are required")
    srv, repo, rid = (os.environ.get(k, "") for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    print(run(a.report, a.label, a.title, a.findings, f"{srv}/{repo}/actions/runs/{rid}" if rid else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
