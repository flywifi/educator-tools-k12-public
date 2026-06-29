#!/usr/bin/env python3
"""Google Workspace output bridge — produce advanced Google Docs/Sheets/Slides without building an OAuth client.

Two complementary outputs from one spec:
  1. the **Office file** (.docx/.xlsx/.pptx via shared/office) — Google imports these to native
     Docs/Sheets/Slides losslessly (the simple, reliable path); plus a `google-import.json` manifest
     describing the converting upload.
  2. a generated **Apps Script** (`.gs`) that builds the file **natively** (SlidesApp/DocumentApp/
     SpreadsheetApp) for advanced automation beyond import.

Consistent with the architecture: live creation is performed by the **host AI's native Google
integration** when connected, or by a deployment-provided Node/clasp runner (`@google/clasp` +
`googleapis`) — credentials come from the environment, never the repo. This bridge produces the
artifacts + instructions; it does not call Google itself.

CLI:
  python3 shared/office/google_bridge.py --type slides --spec deck.json --outdir out/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

KINDS = {
    "docs": {"office": "docx", "google_mime": "application/vnd.google-apps.document"},
    "sheets": {"office": "xlsx", "google_mime": "application/vnd.google-apps.spreadsheet"},
    "slides": {"office": "pptx", "google_mime": "application/vnd.google-apps.presentation"},
}


def _apps_script(kind: str, spec: dict) -> str:
    spec_lit = json.dumps(spec, ensure_ascii=False)
    head = f"// Auto-generated Apps Script — native Google {kind} from a TOS spec.\n" \
           f"// Run via the host's native Google integration or clasp+node (creds from env, never repo).\n" \
           f"var SPEC = {spec_lit};\n\n"
    if kind == "slides":
        body = (
            "function buildDeck() {\n"
            "  var pres = SlidesApp.create(SPEC.title || 'Deck');\n"
            "  (SPEC.slides || []).forEach(function(s) {\n"
            "    var slide = pres.appendSlide(SlidesApp.PredefinedLayout.TITLE_AND_BODY);\n"
            "    try { slide.getPlaceholder(SlidesApp.PlaceholderType.TITLE).asShape().getText().setText(s.title || ''); } catch (e) {}\n"
            "    try { slide.getPlaceholder(SlidesApp.PlaceholderType.BODY).asShape().getText().setText((s.bullets || []).join('\\n')); } catch (e) {}\n"
            "  });\n"
            "  Logger.log(pres.getUrl());\n"
            "}\n")
    elif kind == "docs":
        body = (
            "function buildDoc() {\n"
            "  var doc = DocumentApp.create(SPEC.title || 'Doc'); var b = doc.getBody();\n"
            "  if (SPEC.title) b.appendParagraph(SPEC.title).setHeading(DocumentApp.ParagraphHeading.TITLE);\n"
            "  (SPEC.sections || []).forEach(function(sec) {\n"
            "    if (sec.heading) b.appendParagraph(sec.heading).setHeading(DocumentApp.ParagraphHeading.HEADING1);\n"
            "    (sec.paragraphs || []).forEach(function(p) { b.appendParagraph(p); });\n"
            "  });\n"
            "  Logger.log(doc.getUrl());\n"
            "}\n")
    else:  # sheets
        body = (
            "function buildSheet() {\n"
            "  var ss = SpreadsheetApp.create(SPEC.title || 'Sheet');\n"
            "  (SPEC.sheets || []).forEach(function(sh, i) {\n"
            "    var s = (i === 0) ? ss.getActiveSheet() : ss.insertSheet();\n"
            "    s.setName(sh.name || ('Sheet' + (i + 1)));\n"
            "    (sh.rows || []).forEach(function(r) { s.appendRow(r); });\n"
            "  });\n"
            "  Logger.log(ss.getUrl());\n"
            "}\n")
    return head + body


def to_google(kind: str, spec: dict, outdir: Path) -> dict:
    from office import build_docx, build_pptx, build_xlsx  # type: ignore
    builders = {"docx": build_docx, "xlsx": build_xlsx, "pptx": build_pptx}
    outdir.mkdir(parents=True, exist_ok=True)
    office_type = KINDS[kind]["office"]
    office_path = outdir / f"source.{office_type}"
    office_result = builders[office_type](spec, office_path)

    gs_path = outdir / "apps_script.gs"
    gs_path.write_text(_apps_script(kind, spec), encoding="utf-8")

    manifest = {
        "google_kind": kind, "google_mime": KINDS[kind]["google_mime"],
        "import_source": office_result.get("path", str(office_path)),
        "native_script": str(gs_path),
        "apply_options": [
            "host AI native Google integration (preferred; no client built here)",
            "converting upload: Drive create with mimeType=" + KINDS[kind]["google_mime"] + " (lossless import of the Office file)",
            "advanced/native: run apps_script.gs via clasp+node (googleapis) — credentials from the environment",
        ],
        "credentials": "from environment only (e.g. GOOGLE_APPLICATION_CREDENTIALS); never the repo",
        "human_review_required": True,
    }
    (outdir / "google-import.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"status": "ok" if office_result.get("status") == "ok" else office_result.get("status"),
            "office": office_result, "apps_script": str(gs_path),
            "manifest": str(outdir / "google-import.json")}


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Produce Google Docs/Sheets/Slides outputs from a spec (no live calls).")
    ap.add_argument("--type", choices=list(KINDS), required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    print(json.dumps(to_google(a.type, spec, Path(a.outdir)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
