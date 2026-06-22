#!/usr/bin/env python3
"""Compute the Quality Gates composite score and decision (deterministic).

Weights are the authoritative QG §33.1 model; thresholds are QG §35.3; the
critical-failure override is QG §35.4/§37 (any dimension scored 0, or an explicit
--critical flag, forces Rejected regardless of composite).

Usage:
  python3 score.py '{"integrity":5,"safety":5,"governance":4,"accuracy":4,"alignment":4,
                     "educational_quality":4,"accessibility":4,"professional_quality":4,"user_intent":5}'
  python3 score.py <scores.json> [--critical "reason"]
  echo '{...}' | python3 score.py

All 9 dimensions are required, each an integer 0-5.
"""
from __future__ import annotations

import json
import sys

WEIGHTS = {
    "integrity": 0.25,
    "accuracy": 0.20,
    "alignment": 0.15,
    "educational_quality": 0.15,
    "governance": 0.10,
    "user_intent": 0.07,
    "accessibility": 0.03,
    "professional_quality": 0.03,
    "safety": 0.02,
}


def decide(composite: float) -> str:
    if composite >= 4.0:
        return "Approved"
    if composite >= 3.0:
        return "Conditionally Approved"
    if composite >= 2.0:
        return "Remediation Required"
    return "Rejected"


def main(argv: list[str]) -> int:
    critical_reason = None
    if "--critical" in argv:
        i = argv.index("--critical")
        critical_reason = argv[i + 1] if i + 1 < len(argv) else "unspecified critical failure"
        argv = argv[:i] + argv[i + 2:]

    raw = ""
    if argv:
        arg = argv[0]
        # treat as a file path if it looks like one and exists
        try:
            with open(arg, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError:
            raw = arg
    else:
        raw = sys.stdin.read()

    try:
        scores = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[!] could not parse scores JSON: {e}")
        return 2

    missing = [d for d in WEIGHTS if d not in scores]
    if missing:
        print(f"[!] missing dimension score(s): {', '.join(missing)}")
        return 2
    bad = {d: v for d, v in scores.items() if d in WEIGHTS and not (isinstance(v, int) and 0 <= v <= 5)}
    if bad:
        print(f"[!] scores must be integers 0-5; offending: {bad}")
        return 2

    composite = round(sum(scores[d] * w for d, w in WEIGHTS.items()), 3)
    zeros = [d for d in WEIGHTS if scores[d] == 0]

    if critical_reason or zeros:
        decision = "Rejected"
        why = critical_reason or f"critical failure: dimension(s) scored 0 -> {', '.join(zeros)}"
        override = True
    else:
        decision = decide(composite)
        why = "composite vs. thresholds (QG §35.3)"
        override = False

    out = {
        "composite": composite,
        "decision": decision,
        "decision_basis": why,
        "critical_override": override,
        "weights_model": "QG §33.1 (9-dimension, authoritative)",
        "scores": {d: scores[d] for d in WEIGHTS},
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
