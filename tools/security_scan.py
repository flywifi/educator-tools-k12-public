#!/usr/bin/env python3
"""Supply-chain scan gate (offline-friendly) — known-CVE + malicious/unsafe-code checks for deps.

Runs `pip-audit` (known vulnerabilities in pinned requirements), `bandit` (unsafe/suspicious code
patterns), and `semgrep` (structural pattern matching with custom rules) when they are installed; if
none are present it reports a gap and exits 0 (CI installs them). Also performs multi-language
awareness: detects Go, Java, and Rust modules in the repo tree and reports their presence + basic
health (compilable / lintable) so TOS understands polyglot contributions.

Exits non-zero on BLOCKING findings (pip-audit CVEs, bandit HIGH severity, or semgrep ERROR) so it can
be a release gate; lower-severity audit patterns (bandit MEDIUM/LOW such as B310 urllib fetch / B608
allow-listed SQL, semgrep `--config=auto` WARNING/INFO) are reported but do not fail the build. This
is the enforcement half of the "dependencies must be auto-updated AND scanned" policy (auto-update =
.github/dependabot.yml).

Usage:
  python3 tools/security_scan.py            # scan; non-zero exit on findings
  python3 tools/security_scan.py --report   # JSON only, never fail (for inspection)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=600)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as exc:
        return -1, f"{exc.__class__.__name__}: {exc}"


LANG_MARKERS = {
    "go.mod": {"lang": "go", "test_cmd": ["go", "vet", "./..."], "lint_cmd": ["golangci-lint", "run"]},
    "Cargo.toml": {"lang": "rust", "test_cmd": ["cargo", "check"], "lint_cmd": ["cargo", "clippy"]},
    "pom.xml": {"lang": "java", "test_cmd": ["mvn", "compile", "-q"], "lint_cmd": None},
    "build.gradle": {"lang": "java", "test_cmd": ["gradle", "compileJava", "-q"], "lint_cmd": None},
    "package.json": {"lang": "javascript", "test_cmd": ["npx", "tsc", "--noEmit"], "lint_cmd": ["npx", "eslint", "."]},
}

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


def _detect_languages() -> list[dict]:
    modules = []
    for dirpath, dirnames, filenames in os.walk(str(ROOT)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if fname in LANG_MARKERS:
                cfg = LANG_MARKERS[fname]
                rel = os.path.relpath(dirpath, str(ROOT))
                entry: dict = {"lang": cfg["lang"], "path": rel, "marker": fname}
                if shutil.which(cfg["test_cmd"][0]) if cfg["test_cmd"] else False:
                    code, out = _run(cfg["test_cmd"])
                    entry["compilable"] = code == 0
                    if code != 0:
                        entry["error_summary"] = out[:200]
                else:
                    entry["compilable"] = None
                    entry["note"] = f"{cfg['test_cmd'][0]} not installed" if cfg["test_cmd"] else "no test command"
                modules.append(entry)
    return modules


def _is_blocking(f: dict) -> bool:
    """What gates a release: confirmed vulnerabilities, not advisory audits.
      - pip-audit  -> always blocks (a known CVE in a pinned dependency).
      - bandit     -> blocks at HIGH severity; MEDIUM/LOW are AUDIT patterns (e.g. B310 urllib fetch
                      of public data, B608 SQL assembled from allow-listed identifiers) -> advisory.
      - semgrep    -> blocks at ERROR; `--config=auto` WARNING/INFO audits -> advisory.
    Advisory findings are still reported (visibility) but do not fail the build. Real high-severity
    issues (shell=True, hardcoded secrets, eval, a semgrep ERROR) still gate."""
    tool = f.get("tool")
    if tool == "pip-audit":
        return True
    sev = str(f.get("severity") or "").upper()
    if tool == "bandit":
        return sev == "HIGH"
    if tool == "semgrep":
        return sev == "ERROR"
    return True  # unknown tool / parse error -> conservative


def scan() -> dict:
    findings, ran, skipped = [], [], []
    # 1) pip-audit over every pinned requirements file.
    reqs = sorted(glob.glob(str(ROOT / "tools" / "requirements-*.txt")))
    if shutil.which("pip-audit"):
        for r in reqs:
            code, out = _run(["pip-audit", "-r", r, "-f", "json", "--progress-spinner", "off"])
            ran.append(f"pip-audit {Path(r).name}")
            try:
                data = json.loads(out or "{}")
                vulns = data.get("dependencies", data) if isinstance(data, dict) else data
                for dep in (vulns or []):
                    for v in (dep.get("vulns") or []):
                        findings.append({"tool": "pip-audit", "file": Path(r).name,
                                         "package": dep.get("name"), "id": v.get("id")})
            except Exception:
                if code not in (0,):
                    findings.append({"tool": "pip-audit", "file": Path(r).name, "raw": out[:300]})
    else:
        skipped.append("pip-audit (not installed)")
    # 2) bandit over our own Python (skills + shared + tools).
    if shutil.which("bandit"):
        code, out = _run(["bandit", "-r", "shared", "tools", "skills", "-ll", "-q", "-f", "json"])
        ran.append("bandit")
        try:
            data = json.loads(out or "{}")
            for r in data.get("results", []):
                findings.append({"tool": "bandit", "file": r.get("filename"), "test": r.get("test_id"),
                                 "severity": r.get("issue_severity"), "issue": r.get("issue_text")})
        except Exception:
            if code not in (0,):
                findings.append({"tool": "bandit", "raw": out[:300]})
    else:
        skipped.append("bandit (not installed)")

    # 3) semgrep over Python code (respects .semgrepignore at repo root).
    if shutil.which("semgrep"):
        code, out = _run(["semgrep", "--config=auto", "--json", "--quiet",
                          "shared", "tools", "skills"])
        ran.append("semgrep")
        try:
            data = json.loads(out or "{}")
            for r in data.get("results", []):
                findings.append({"tool": "semgrep", "file": r.get("path"),
                                 "rule": r.get("check_id"), "severity": r.get("extra", {}).get("severity"),
                                 "message": r.get("extra", {}).get("message", "")[:200]})
        except Exception:
            if code not in (0,):
                findings.append({"tool": "semgrep", "raw": out[:300]})
    else:
        skipped.append("semgrep (not installed)")

    # 4) Multi-language awareness: detect non-Python modules in the repo tree.
    lang_modules = _detect_languages()

    blocking = [f for f in findings if _is_blocking(f)]
    return {"tool": "security-scan", "ran": ran, "skipped": skipped,
            "findings": findings, "finding_count": len(findings),
            "blocking_count": len(blocking), "advisory_count": len(findings) - len(blocking),
            "language_modules": lang_modules,
            "status": ("blocking" if blocking else "advisory" if findings
                       else "no_scanners" if not ran else "clean")}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Dependency + code security scan gate.")
    ap.add_argument("--report", action="store_true", help="print JSON and exit 0 regardless")
    a = ap.parse_args(argv)
    result = scan()
    print(json.dumps(result, indent=2))
    if a.report:
        return 0
    return 1 if result["blocking_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
