"""Recursive container parsing - parse a document AND the documents nested inside it.

A single upload is often a CONTAINER: a .zip of reports, an .eml with attachments, or an OOXML file
(.pptx/.docx/.xlsx) that embeds other documents (e.g. a PowerPoint extracted from a download link
that itself embeds an Excel workbook). `parse_recursive` runs the docintel pipeline on the document,
then enumerates its child documents and parses each, building a tree - bounded by depth and child
count, with a content-hash cycle guard so a self-referential or duplicated container can't loop.

Boundary (honest): this expands TRUE containers (files that physically contain other files). The
HTML -> download-link -> file chain is a FETCH concern handled by the harvest layer (tools/acquire.py
mirrors linked files, now with lxml link discovery); those mirrored files then land here as inputs.
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from typing import Dict, List, Optional, Tuple

from .orchestration import Pipeline, guess_media_type

# Child documents we know how to (try to) parse downstream.
_DOC_EXT = (".pdf", ".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls", ".odt", ".ods", ".odp",
            ".csv", ".tsv", ".html", ".htm", ".txt", ".md", ".rtf", ".eml", ".ics", ".vtt",
            ".srt", ".json", ".xml", ".zip")
_OOXML_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
Child = Tuple[str, bytes]


def _zip_children(data: bytes, only_embeddings: bool) -> List[Child]:
    out: List[Child] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                low = name.lower()
                if only_embeddings and "/embeddings/" not in low:
                    continue  # OOXML: only real embedded objects, not the package's own parts
                if not low.endswith(_DOC_EXT):
                    continue
                try:
                    out.append((name.rsplit("/", 1)[-1] or name, z.read(name)))
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass
    return out


def _eml_children(data: bytes) -> List[Child]:
    out: List[Child] = []
    try:
        import email
        msg = email.message_from_bytes(data)
        for i, part in enumerate(msg.walk()):
            if part.get_content_maintype() == "multipart":
                continue
            fn = part.get_filename()
            if not fn:
                continue
            payload = part.get_payload(decode=True)
            if payload:
                out.append((fn, payload))
    except Exception:  # noqa: BLE001
        pass
    return out


def iter_children(data: bytes, filename: str, media_type: str) -> List[Child]:
    """Child documents physically contained in this file (empty if it is not a container)."""
    low = filename.lower()
    if media_type in _OOXML_TYPES:
        return _zip_children(data, only_embeddings=True)
    if media_type == "application/zip" or low.endswith(".zip"):
        return _zip_children(data, only_embeddings=False)
    if media_type == "message/rfc822" or low.endswith(".eml"):
        return _eml_children(data)
    return []


def parse_recursive(data: bytes, filename: str, media_type: Optional[str] = None,
                    max_depth: int = 3, max_children: int = 50,
                    _seen: Optional[set] = None, _depth: int = 0) -> Dict:
    """Parse this document and (depth/count-bounded, cycle-guarded) every document nested inside it.
    Returns a tree node: {filename, media_type, parser, blocks, retrieval_state, children:[...]}."""
    seen = _seen if _seen is not None else set()
    media_type = media_type or guess_media_type(filename)
    sha = hashlib.sha256(data).hexdigest()
    node: Dict = {"filename": filename, "media_type": media_type, "sha256": sha[:16],
                  "depth": _depth, "children": []}
    if sha in seen:
        node["status"] = "duplicate_skipped"
        return node
    seen.add(sha)
    try:
        doc = Pipeline().run(data, filename, media_type)
        rec = doc.diagnostics.get("recovery", {})
        node.update({"status": "parsed", "parser": rec.get("parser"),
                     "blocks": doc.properties.get("block_count", 0),
                     "retrieval_state": doc.diagnostics.get("retrieval_state"),
                     "capability_gaps": rec.get("capability_gaps", [])})
    except Exception as exc:  # noqa: BLE001
        node["status"] = f"parse_error:{exc.__class__.__name__}"
    if _depth < max_depth:
        for cname, cbytes in iter_children(data, filename, media_type)[:max_children]:
            node["children"].append(
                parse_recursive(cbytes, cname, None, max_depth, max_children, seen, _depth + 1))
    return node
