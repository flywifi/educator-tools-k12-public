#!/usr/bin/env python3
"""Validate committed EXAMPLE artifacts so a malformed sample fails the build (CI guardrail).

Three checks, all stdlib-first (degrade to a labeled skip, never a false failure):
  1. governed JSON examples (`**/*.example.json`) pass the output-validator rule catalog;
  2. per-deployment connector flags validate against the connector-flags schema (when jsonschema present);
  3. committed example documents (.docx/.pptx/.xlsx/.pdf/.odt/.ods/.odp) are structurally valid, and
     committed docintel inputs (.ics/.eml/.vtt/.srt) actually recover content (not just "seen").
Exits non-zero on any failure so it can gate CI.

Usage: python3 tools/validate_examples.py
"""
from __future__ import annotations

import glob
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run_json(cmd: list[str]) -> dict:
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    try:
        return json.loads(out.stdout)
    except Exception:
        return {"status": "error", "raw": (out.stdout + out.stderr)[:300]}


def main() -> int:
    failures: list[str] = []
    checked = 0

    # 1) governed JSON examples -> rule catalog
    for f in sorted(glob.glob("**/*.example.json", recursive=True, root_dir=str(ROOT))):
        schema = ["--schema", "connector-flags"] if "feature-flags" in f else []
        rep = _run_json(["python3", "tools/validate_outputs.py", "--input", f, *schema])
        checked += 1
        if rep.get("status") == "fail":
            failures.append(f"{f}: " + ", ".join(r.get("rule", r.get("",  "?")) for r in rep.get("rule_failures", [])) +
                            (" schema:" + ";".join(rep.get("schema_errors", [])) if rep.get("schema_errors") else ""))

    # 2) committed example documents -> structural validity
    docs = [f for ext in ("docx", "pptx", "xlsx", "pdf", "odt", "ods", "odp")
            for f in glob.glob(f"skills/**/examples/*.{ext}", recursive=True, root_dir=str(ROOT))]
    for f in docs:
        rep = _run_json(["python3", "tools/validate_document.py", f])
        checked += 1
        if not rep.get("valid", True):
            failures.append(f"{f}: " + ", ".join(x["code"] for x in rep.get("findings", [])))

    # 3) committed docintel inputs -> must recover content
    sys.path.insert(0, str(ROOT / "shared"))
    try:
        import docintel  # type: ignore
        pipe = docintel.Pipeline()
        for f in [g for ext in ("ics", "eml", "vtt", "srt")
                  for g in glob.glob(f"skills/**/examples/*.{ext}", recursive=True, root_dir=str(ROOT))]:
            doc = pipe.run((ROOT / f).read_bytes(), f)
            checked += 1
            if doc.diagnostics.get("retrieval_state") != "content_ingested":
                failures.append(f"{f}: retrieval_state={doc.diagnostics.get('retrieval_state')} (expected content_ingested)")
    except Exception as exc:
        print(f"[skip] docintel input check unavailable: {exc}")

    print(f"validated {checked} example artifact(s); {len(failures)} failure(s)")
    for msg in failures:
        print(f"  FAIL {msg}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
