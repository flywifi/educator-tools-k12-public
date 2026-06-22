#!/usr/bin/env python3
"""Run the docintel pipeline on a file and emit a governed knowledge artifact.

Usage:
  python3 tools/docintel_run.py --check                 # list parsers + availability (offline)
  python3 tools/docintel_run.py <file> [--out art.json] [--udom udom.json] [--quiet]

Parser-independent + stdlib-only by default (PlainTextParser handles .txt/.md/.html/.docx);
PDF support activates automatically if PyMuPDF is installed. Nothing is fabricated: unrecovered
content is reported with low/zero confidence, and the artifact is never "certified" here -
that is quality-review's job (protocols/quality-gates.md).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared"))

import docintel  # noqa: E402  (path set above)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run the docintel document-intelligence pipeline.")
    ap.add_argument("file", nargs="?", help="document to process (.txt/.md/.html/.docx/.pdf)")
    ap.add_argument("--check", action="store_true", help="list registered parsers and exit")
    ap.add_argument("--out", help="write the knowledge artifact JSON here")
    ap.add_argument("--udom", help="write the raw UDOM JSON here")
    ap.add_argument("--quiet", action="store_true", help="only print the validation summary")
    a = ap.parse_args(argv)

    registry = docintel.default_registry()

    if a.check:
        print(f"docintel {docintel.__version__} - registered parsers:")
        for p in registry.describe():
            flag = "available" if p["available"] else "unavailable (deps not installed)"
            print(f"  - {p['name']} v{p['version']}: {flag}; capabilities: {', '.join(p['capabilities'])}")
        print("registered table engines:")
        for e in docintel.default_table_registry().describe():
            flag = "available" if e["available"] else "unavailable (deps not installed)"
            print(f"  - {e['name']} v{e['version']}: {flag}")
        print("\nstdlib-only by default; PDF text via PyMuPDF, PDF tables via pdfplumber when installed.")
        return 0

    if not a.file:
        ap.error("provide a file to process, or use --check")
    path = Path(a.file)
    if not path.exists():
        print(f"[!] not found: {path}")
        return 1

    data = path.read_bytes()
    pipeline = docintel.Pipeline(registry=registry)
    doc = pipeline.run(data, str(path))
    artifact = docintel.build_knowledge_artifact(doc)
    report = docintel.validate(doc, artifact)
    artifact["metadata"]["score_summary"] = report

    if a.udom:
        Path(a.udom).write_text(json.dumps(doc.to_dict(), indent=2), encoding="utf-8")
    if a.out:
        Path(a.out).write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    rec = doc.diagnostics.get("recovery", {})
    print(f"document: {doc.source.filename}  ({doc.source.media_type})")
    print(f"  parser: {rec.get('parser', 'none')}  method: {rec.get('extraction_method', '-')}"
          f"  capability_gaps: {rec.get('capability_gaps', [])}")
    print(f"  pages: {doc.properties.get('page_count', 0)}  blocks: {doc.properties.get('block_count', 0)}"
          f"  doc_confidence: {getattr(doc.confidence, 'value', 0.0):.3f}")
    print(f"  lineage stages: {[e.stage for e in doc.lineage]}")
    print("validation:")
    print(f"  governance_ok: {report['summary']['governance_ok']}  "
          f"reading_order_ok: {report['summary']['reading_order_ok']}  "
          f"schema: {report['schema'].get('status')}")
    print(f"  human_review_required: {artifact['metadata']['human_review_required']}  "
          f"decision: {artifact['metadata']['decision']} ({artifact['metadata']['status']})")
    if a.out:
        print(f"wrote artifact -> {a.out}")
    if a.udom:
        print(f"wrote udom -> {a.udom}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
