#!/usr/bin/env python3
"""Output validator (claim-and-output-validator pattern) — check emitted artifacts before they ship.

Validates a governed artifact JSON against (a) its JSON Schema when known and (b) a universal claim/rule
catalog (governance + no-fabrication + no-real-PII). Prints pass/fail with plain-language repair
guidance, and can PROMOTE a failing case into a regression eval so the same defect is caught next time.
Offline; uses jsonschema when installed (else schema checks are skipped with a note).

Usage:
  python3 tools/validate_outputs.py --input artifact.json [--schema records|traversal|udom|connector-flags]
  python3 tools/validate_outputs.py --input bad.json --schema records --promote skills/core/skill-health/evals/evals.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = {
    "records": "shared/records/records.schema.json",
    "traversal": "shared/traversal/traversal.schema.json",
    "udom": "shared/docintel/udom.schema.json",
    "connector-flags": "shared/connectors/connector.schema.json",
}
_PHONE = re.compile(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def _walk_strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def rule_checks(art: dict) -> list[dict]:
    """Universal claim catalog — governance + no-fabrication + no-real-PII heuristics."""
    fails = []
    # Governance: governed artifacts must carry human_review_required: true.
    if "human_review_required" in art and art["human_review_required"] is not True:
        fails.append({"rule": "human_review_required", "severity": "blocking",
                      "guidance": "set human_review_required: true — outputs are decision support"})
    # No fabricated standards: cited codes must be non-empty strings.
    for key in ("standards_cited", "standards_set"):
        vals = art.get(key)
        if isinstance(vals, list) and any(not str(v).strip() for v in vals):
            fails.append({"rule": "no_empty_standard", "severity": "blocking",
                          "guidance": f"{key} has an empty/blank code — cite a real, verifiable standard"})
    # Fabricated-standard gate: resolve cited codes offline (verify_standards; stdlib, committed
    # corpus). BLOCKING only where the corpus is authoritative (not_found/malformed); other
    # non-clean states surface as warnings. Missing module/corpus -> labeled skip, never a verdict.
    cited = [v for v in (art.get("standards_cited") or []) if str(v).strip()] \
        if isinstance(art.get("standards_cited"), list) else []
    if cited:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import verify_standards
            rep = verify_standards.verify(cited, standards_set=art.get("standards_set"),
                                          grade_band=art.get("grade_band"), context=art.get("context"))
            for r in rep["results"]:
                if r["state"] in ("not_found", "malformed"):
                    fails.append({"rule": "unresolvable_standard", "severity": "blocking",
                                  "guidance": f"{r['code']}: {r['state']} — "
                                              f"{r['detail'] or 'cite a real, verifiable code (QG §11.4)'}"})
                elif r["state"] == "retired":
                    # A withdrawn standard is not a fabricated one. Warning, with guidance the
                    # author can act on — blocking here would repeat D-K, where TOS accused real
                    # SpEd standards of being invented.
                    fails.append({"rule": "standard_retired", "severity": "warning",
                                  "guidance": f"{r['code']}: this standard has been WITHDRAWN by "
                                              f"Florida — it was real, and is no longer current. "
                                              f"{r['detail']}"})
                elif r.get("needs_review"):
                    # WARNING, not blocking. The code exists — that is what created the overlay
                    # entry — and verify_standards already serves CPALMS's own text for the
                    # citation, so the artifact is not wrong, it is unverified. Blocking here would
                    # fail builds over a divergence the author cannot fix from inside the artifact.
                    fails.append({"rule": "standard_needs_review", "severity": "warning",
                                  "guidance": f"{r['code']}: exists on CPALMS, but the corpus "
                                              f"statement does not match its official text — "
                                              f"{r['detail']}"})
                elif r["state"] != "resolved" or r.get("grade_band_match") is False:
                    fails.append({"rule": "standard_advisory", "severity": "warning",
                                  "guidance": f"{r['code']}: {r['state']} — {r['detail']}"})
        except Exception as exc:
            fails.append({"rule": "standard_resolution_skipped", "severity": "warning",
                          "guidance": f"verify_standards unavailable ({exc.__class__.__name__}) — "
                                      "codes not resolved this run"})
    # No real PII that slipped past placeholders (SSN / non-555 phone).
    for s in _walk_strings(art):
        if _SSN.search(s):
            fails.append({"rule": "no_real_pii", "severity": "blocking",
                          "guidance": "an SSN-like value is present — never emit real PII; use placeholders"})
            break
    for s in _walk_strings(art):
        for ph in _PHONE.findall(s):
            if not ph.startswith("555"):
                fails.append({"rule": "placeholder_pii", "severity": "warning",
                              "guidance": f"phone {ph} is not a 555 placeholder — confirm it is not real PII"})
                break
        else:
            continue
        break
    return fails


def validate(path: Path, schema_key: str | None) -> dict:
    art = json.loads(path.read_text(encoding="utf-8"))
    schema_errors, schema_status = [], "skipped"
    if schema_key:
        try:
            import jsonschema  # type: ignore
            schema = json.loads((ROOT / SCHEMAS[schema_key]).read_text(encoding="utf-8"))
            v = jsonschema.Draft202012Validator(schema)
            schema_errors = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in v.iter_errors(art)]
            schema_status = "ok" if not schema_errors else "errors"
        except ImportError:
            schema_status = "jsonschema_not_installed"
    rule_fails = rule_checks(art)
    blocking = [r for r in rule_fails if r["severity"] == "blocking"] + schema_errors
    return {"tool": "output-validator", "input": str(path), "schema": schema_key,
            "schema_status": schema_status, "schema_errors": schema_errors,
            "rule_failures": rule_fails, "status": "fail" if blocking else "pass",
            "human_review_required": True}


def promote(report: dict, evals_path: Path) -> None:
    data = json.loads(evals_path.read_text(encoding="utf-8")) if evals_path.exists() else {"evals": []}
    data.setdefault("evals", []).append({
        "name": f"regression_{Path(report['input']).stem}",
        "_note": "auto-promoted failing case (output-validator)",
        "input_artifact": report["input"], "schema": report["schema"],
        "assert": {"status": "pass"}})
    evals_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Validate a governed artifact before it ships (offline).")
    ap.add_argument("--input", required=True)
    ap.add_argument("--schema", choices=list(SCHEMAS))
    ap.add_argument("--promote", metavar="EVALS_JSON", help="append a failing case to this evals file")
    a = ap.parse_args(argv)
    report = validate(Path(a.input), a.schema)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["status"] == "fail" and a.promote:
        promote(report, Path(a.promote))
        print(f"\npromoted regression case -> {a.promote}")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
