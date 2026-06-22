"""Stdlib image analysis - format + pixel dimensions from file headers, no dependencies.

This is the non-OCR half of image handling: we can always identify an image and its size from its
header (PNG/JPEG/GIF/BMP), which lets the pipeline ingest images and decide whether OCR is needed -
without inventing any text. Text recovery from images is OCR's job (`ocr.py`), and only runs when an
OCR engine is installed.
"""
from __future__ import annotations

from typing import Dict, Optional


def image_info(data: bytes) -> Optional[Dict[str, object]]:
    """Return {format, width, height} parsed from the header, or None if unrecognized."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return {"format": "png",
                "width": int.from_bytes(data[16:20], "big"),
                "height": int.from_bytes(data[20:24], "big")}
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return {"format": "gif",
                "width": int.from_bytes(data[6:8], "little"),
                "height": int.from_bytes(data[8:10], "little")}
    if data[:2] == b"BM" and len(data) >= 26:
        return {"format": "bmp",
                "width": int.from_bytes(data[18:22], "little"),
                "height": int.from_bytes(data[22:26], "little")}
    if data[:2] == b"\xff\xd8":  # JPEG: scan for a Start-Of-Frame marker
        i = 2
        n = len(data)
        while i + 9 < n:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                return {"format": "jpeg",
                        "height": int.from_bytes(data[i + 5:i + 7], "big"),
                        "width": int.from_bytes(data[i + 7:i + 9], "big")}
            seg = int.from_bytes(data[i + 2:i + 4], "big")
            if seg <= 0:
                break
            i += 2 + seg
        return {"format": "jpeg", "width": None, "height": None}
    return None
