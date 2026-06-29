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
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "shared"))

import docintel  # noqa: E402  (path set above)


# --------------------------------------------------------------------------- deferred parse queue
# "Parse separately or at a later time": an upload can be CAPTURED now (registered with its bytes +
# metadata, retrieval_state 'referenced') and PARSED later in a batch. Nothing is fabricated; an item
# that can't be parsed yet (missing optional dep) stays queued with an honest status.
def _queue_manifest(qdir: Path) -> Path:
    return qdir / "queue.json"


def _load_queue(qdir: Path) -> dict:
    mf = _queue_manifest(qdir)
    if mf.exists():
        try:
            return json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"items": []}


def _save_queue(qdir: Path, q: dict) -> None:
    qdir.mkdir(parents=True, exist_ok=True)
    _queue_manifest(qdir).write_text(json.dumps(q, indent=2), encoding="utf-8")


def enqueue(path: Path, qdir: Path) -> dict:
    """Register an upload for later parsing (capture-now, parse-later). Dedups by content hash."""
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    q = _load_queue(qdir)
    if any(it["sha256"] == sha for it in q["items"]):
        return {"status": "duplicate", "sha256": sha, "filename": path.name}
    files = qdir / "files"; files.mkdir(parents=True, exist_ok=True)
    stored = files / f"{sha[:16]}_{path.name}"
    shutil.copyfile(path, stored)
    item = {"id": f"q_{sha[:12]}", "filename": path.name, "stored": stored.name,
            "sha256": sha, "media_type": docintel.guess_media_type(path.name),
            "retrieval_state": "referenced", "status": "pending",
            "queued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "parsed_at": None}
    q["items"].append(item)
    _save_queue(qdir, q)
    return item


def process_queue(qdir: Path, registry) -> list[dict]:
    """Parse every pending item now. Writes artifacts to <qdir>/artifacts/<id>.json and updates state."""
    q = _load_queue(qdir)
    arts = qdir / "artifacts"; arts.mkdir(parents=True, exist_ok=True)
    out = []
    pipeline = docintel.Pipeline(registry=registry)
    for it in q["items"]:
        if it["status"] == "parsed":
            continue
        src = qdir / "files" / it["stored"]
        if not src.exists():
            it["status"] = "missing_file"; out.append(it); continue
        doc = pipeline.run(src.read_bytes(), it["filename"], it["media_type"])
        artifact = docintel.build_knowledge_artifact(doc)
        artifact["metadata"]["score_summary"] = docintel.validate(doc, artifact)
        (arts / f"{it['id']}.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        it["retrieval_state"] = doc.diagnostics.get("retrieval_state", "referenced")
        it["status"] = "parsed"
        it["parsed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        it["recovery"] = doc.diagnostics.get("recovery", {})
        out.append(it)
    _save_queue(qdir, q)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run the docintel document-intelligence pipeline.")
    ap.add_argument("file", nargs="?", help="document to process (.txt/.md/.html/.docx/.pdf)")
    ap.add_argument("--check", action="store_true", help="list registered parsers and exit")
    ap.add_argument("--out", help="write the knowledge artifact JSON here")
    ap.add_argument("--udom", help="write the raw UDOM JSON here")
    ap.add_argument("--quiet", action="store_true", help="only print the validation summary")
    ap.add_argument("--queue", help="deferred-parse queue directory (capture-now, parse-later)")
    ap.add_argument("--enqueue", action="store_true",
                    help="register the given file into --queue for LATER parsing (does not parse now)")
    ap.add_argument("--process-queue", action="store_true",
                    help="parse every pending item in --queue now, writing artifacts to <queue>/artifacts/")
    ap.add_argument("--recursive", action="store_true",
                    help="also parse documents NESTED inside the file (zip / .eml attachments / OOXML "
                         "embeddings), depth-bounded with a cycle guard")
    a = ap.parse_args(argv)

    registry = docintel.default_registry()

    # deferred-parse modes: capture an upload now, parse it (or a whole batch) at a later time
    if a.enqueue or a.process_queue:
        if not a.queue:
            ap.error("--enqueue/--process-queue require --queue <dir>")
        qdir = Path(a.queue)
        if a.enqueue:
            if not a.file or not Path(a.file).exists():
                ap.error("--enqueue needs an existing file to register")
            item = enqueue(Path(a.file), qdir)
            print(f"queued for later parsing: {item.get('filename')} "
                  f"[{item.get('status')}] -> {qdir}/  (run --process-queue {qdir} when ready)")
            return 0
        results = process_queue(qdir, registry)
        parsed = sum(1 for r in results if r["status"] == "parsed")
        print(f"processed deferred queue {qdir}: {parsed}/{len(results)} item(s) parsed")
        for r in results:
            print(f"  {r['status']:12} {r['filename'][:50]}  retrieval_state={r.get('retrieval_state')}")
        return 0

    if a.check:
        print(f"docintel {docintel.__version__} - registered parsers:")
        for p in registry.describe():
            flag = "available" if p["available"] else "unavailable (deps not installed)"
            print(f"  - {p['name']} v{p['version']}: {flag}; capabilities: {', '.join(p['capabilities'])}")
        print("registered table engines:")
        for e in docintel.default_table_registry().describe():
            flag = "available" if e["available"] else "unavailable (deps not installed)"
            print(f"  - {e['name']} v{e['version']}: {flag}")
        print("registered OCR engines:")
        for e in docintel.default_ocr_registry().describe():
            flag = "available" if e["available"] else "unavailable (deps not installed)"
            print(f"  - {e['name']} v{e['version']}: {flag}")
        print("\nstdlib-only by default; PDF text via PyMuPDF, PDF tables via pdfplumber, "
              "image OCR via pytesseract - each activates when installed.")
        return 0

    if not a.file:
        ap.error("provide a file to process, or use --check")
    path = Path(a.file)
    if not path.exists():
        print(f"[!] not found: {path}")
        return 1

    if a.recursive:
        tree = docintel.parse_recursive(path.read_bytes(), str(path))

        def _show(n, indent=0):
            pad = "  " * indent
            kids = n.get("children", [])
            print(f"{pad}- {n['filename']} [{n.get('status')}] parser={n.get('parser')} "
                  f"blocks={n.get('blocks', 0)} state={n.get('retrieval_state')}"
                  + (f"  (+{len(kids)} nested)" if kids else ""))
            for k in kids:
                _show(k, indent + 1)
        print(f"recursive parse of {path.name}:")
        _show(tree)
        if a.out:
            Path(a.out).write_text(json.dumps(tree, indent=2), encoding="utf-8")
            print(f"wrote tree -> {a.out}")
        return 0

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
          f"  doc_confidence: {getattr(doc.confidence, 'value', 0.0):.3f}"
          f"  retrieval_state: {doc.diagnostics.get('retrieval_state')}")
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
