#!/usr/bin/env python3
"""Render a presentation-builder slide spec into a REAL .pptx via the shared Office engine.

Capability-gated: emits an actual editable .pptx when python-pptx is installed
(tools/requirements-office.txt); otherwise writes the spec sidecar and reports an honest gap (the host's
native `pptx` skill can also consume the spec). `--pdf` renders a PDF via LibreOffice for visual QA.

Usage:
  python3 scripts/build_deck.py --spec assets/templates/slide-spec.example.json --out out/deck.pptx --pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Build a real .pptx from a slide spec (capability-gated).")
    ap.add_argument("--spec", required=True, help="JSON slide spec (see assets/templates/slide-spec.example.json)")
    ap.add_argument("--out", required=True, help="output .pptx path")
    ap.add_argument("--pdf", action="store_true", help="also render a PDF via LibreOffice (QA)")
    ap.add_argument("--author", help="document author (the directing teacher); never AI/library")
    a = ap.parse_args(argv)
    try:
        from office import build_pptx, convert  # type: ignore
    except Exception as exc:
        print(json.dumps({"status": "engine_unavailable", "detail": str(exc)}, indent=2))
        return 0
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    res = build_pptx(spec, Path(a.out), author=a.author)
    if a.pdf and res.get("status") == "ok":
        res["pdf"] = convert(Path(a.out), "pdf")
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
