"""html_util - one shared, i18n-safe HTML toolkit: decode -> DOM -> text / links / tables.

Single tiered implementation reused by the docintel HTML parser + table engine and the harvest
crawler, so "resilient HTML" lives in ONE place. Engine ladder: Scrapling/lxml (robust on messy or
restructured markup) -> stdlib (always works). Parser only - no fetching, no anti-bot evasion.

INTERNATIONALIZATION (decode_bytes): never `decode('utf-8','ignore')` (that silently DROPS foreign
characters). Instead detect the real encoding - BOM, then a declared/`<meta charset>`/XML encoding,
then charset-normalizer, then strict UTF-8, then Latin-1 as a last resort that never fails - and
NFC-normalize the result so non-Latin scripts (CJK, Arabic, Cyrillic, ...), legacy system encodings
(Windows-1252, Shift-JIS, Mac Roman, ISO-8859-*), and the full range of special characters and
language punctuation are preserved rather than mangled.
"""
from __future__ import annotations

import re
import unicodedata
import urllib.parse
from html.parser import HTMLParser
from typing import List, Optional, Tuple

_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_Para = Tuple[str, str, Optional[int]]          # (text, block_type, heading_level)
_RawRow = List[Tuple[str, int, int]]            # [(cell_text, rowspan, colspan), ...]
_RawTable = Tuple[List[_RawRow], int]           # (rows, header_row_count)

_BOMS = (
    (b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"), (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"),
)
_CHARSET_RE = re.compile(rb'charset\s*=\s*["\']?\s*([a-zA-Z0-9_\-:.]+)', re.I)
_XMLENC_RE = re.compile(rb'encoding\s*=\s*["\']([a-zA-Z0-9_\-:.]+)["\']', re.I)


def _nfc(s: str) -> str:
    if s[:1] == "﻿":          # drop a leftover byte-order mark (e.g. from UTF-16/32)
        s = s[1:]
    return unicodedata.normalize("NFC", s)


# Labels the HTML5 standard decodes AS windows-1252 (the dominant real-world Western encoding; bytes
# 0x80-0x9F are printable punctuation there, but C1 controls in ISO-8859-1).
_WIN1252_ALIASES = {"iso-8859-1", "iso8859-1", "latin-1", "latin1", "l1", "ascii", "us-ascii",
                    "cp819", "windows-1252", "cp1252", "8859-1"}


def _canon(enc: str, has_c1: bool) -> str:
    return "cp1252" if (has_c1 and enc.strip().lower() in _WIN1252_ALIASES) else enc


def _declared(data: bytes, declared: Optional[str]) -> List[str]:
    out: List[str] = []
    if declared:
        out.append(declared)
    m = _CHARSET_RE.search(data[:4096]) or _XMLENC_RE.search(data[:4096])
    if m:
        try:
            out.append(m.group(1).decode("ascii", "ignore"))
        except Exception:  # noqa: BLE001
            pass
    return out


def _detect(data: bytes) -> Optional[str]:
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            return best.encoding
    except Exception:  # noqa: BLE001
        try:
            import chardet
            return chardet.detect(data).get("encoding")
        except Exception:  # noqa: BLE001
            pass
    return None


def decode_bytes(data: bytes, declared: Optional[str] = None) -> str:
    """Best-effort, lossless-leaning decode of arbitrary document bytes to NFC-normalized text.
    Order: BOM -> declared/<meta charset> -> UTF-8 strict (self-validating) -> statistical detector
    (Western single-byte ambiguity resolved toward Windows-1252) -> Latin-1 (never fails)."""
    if not data:
        return ""
    for bom, enc in _BOMS:
        if data.startswith(bom):
            try:
                return _nfc(data.decode(enc))
            except Exception:  # noqa: BLE001
                break
    has_c1 = any(0x80 <= b <= 0x9F for b in data[:65536])
    # 1. declared / <meta charset> / <?xml encoding?> — authoritative (HTML5 latin1->win1252 mapping).
    for enc in _declared(data, declared):
        try:
            return _nfc(data.decode(_canon(enc, has_c1)))
        except (LookupError, UnicodeDecodeError):
            continue
    # 2. UTF-8 strict — self-validating, so a clean decode is almost certainly correct.
    try:
        return _nfc(data.decode("utf-8"))
    except UnicodeDecodeError:
        pass
    # 3. Western single-byte text -> Windows-1252. A high ASCII ratio means Latin script (markup +
    #    mostly-English text with occasional accents); this also corrects a detector that mis-guesses
    #    short Latin text as a non-Latin codepage. CJK/Cyrillic/Arabic are byte-dense (LOW ASCII ratio)
    #    so they skip this and keep their detected encoding below.
    sample = data[:65536]
    ascii_ratio = sum(1 for b in sample if b < 0x80) / len(sample)
    if ascii_ratio >= 0.70:
        try:
            return _nfc(data.decode("cp1252"))
        except (LookupError, UnicodeDecodeError):
            pass
    # 4. statistical detector (CJK / Cyrillic / Arabic / Thai / ...).
    guess = _detect(data)
    if guess:
        try:
            return _nfc(data.decode(guess))
        except (LookupError, UnicodeDecodeError):
            pass
    # 5. last resort — maps every byte, never raises, never drops content.
    try:
        return _nfc(data.decode("cp1252"))
    except (LookupError, UnicodeDecodeError):
        return _nfc(data.decode("latin-1", "replace"))


def scrapling_present() -> bool:
    try:
        import scrapling  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def parse_dom(text: str):
    """lxml HTML root with script/style/noscript/template removed, or None if lxml is unavailable."""
    try:
        import lxml.html as LH
    except Exception:  # noqa: BLE001
        return None
    try:
        root = LH.fromstring(text)
    except Exception:  # noqa: BLE001
        return None
    for bad in root.xpath("//script | //style | //noscript | //template"):
        bad.drop_tree()
    return root


def engine_label() -> str:
    return "scrapling_lxml" if scrapling_present() else "lxml_html"


# --------------------------------------------------------------------------- text blocks
def get_text_blocks(text: str) -> Tuple[str, List[_Para]]:
    """(engine, [(text, kind, level)]) in document order. lxml walk; stdlib HTMLParser fallback."""
    root = parse_dom(text)
    if root is not None:
        paras: List[_Para] = []
        anc = ("ancestor::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or "
               "self::h6 or self::p or self::li]")
        for el in root.iter():
            tag = el.tag if isinstance(el.tag, str) else ""
            if tag in _HEADINGS:
                kind, level = "heading", _HEADINGS[tag]
            elif tag == "li":
                kind, level = "list_item", None
            elif tag == "p":
                kind, level = "paragraph", None
            else:
                continue
            if el.xpath(anc):  # nested in another target; the outer one already covers this text
                continue
            content = " ".join(el.text_content().split())
            if content:
                paras.append((content, kind, level))
        if paras:
            return engine_label(), paras
    return "stdlib_html", _stdlib_blocks(text)


class _BlockHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)   # entities -> unicode (keeps foreign chars)
        self.blocks: List[_Para] = []
        self._cur: List[str] = []
        self._kind: Optional[str] = None
        self._level: Optional[int] = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self._skip += 1
            return
        if tag in _HEADINGS or tag in ("p", "li"):
            self._flush()
            self._kind = "heading" if tag in _HEADINGS else ("list_item" if tag == "li" else "paragraph")
            self._level = _HEADINGS.get(tag)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template"):
            self._skip = max(0, self._skip - 1)
            return
        if tag in _HEADINGS or tag in ("p", "li"):
            self._flush()

    def handle_data(self, data):
        if not self._skip and self._kind:
            self._cur.append(data)

    def _flush(self):
        if self._kind and self._cur:
            txt = " ".join("".join(self._cur).split())
            if txt:
                self.blocks.append((txt, self._kind, self._level))
        self._cur, self._kind, self._level = [], None, None


def _stdlib_blocks(text: str) -> List[_Para]:
    try:
        p = _BlockHTMLParser()
        p.feed(text)
        p._flush()
        if p.blocks:
            return p.blocks
    except Exception:  # noqa: BLE001
        pass
    stripped = " ".join(re.sub(r"<[^>]+>", " ", text).split())
    return [(stripped, "paragraph", None)] if stripped else []


# --------------------------------------------------------------------------- links
def get_links(html: str, base: str = "", include_all: bool = False) -> List[str]:
    """Absolute links from the page. Default: anchor hrefs only (crawler use); include_all also
    returns img/script/link targets. lxml iterlinks (robust) with a regex fallback."""
    root = parse_dom(html)
    out: List[str] = []
    if root is not None:
        if base:
            try:
                root.make_links_absolute(base, resolve_base_href=True)
            except Exception:  # noqa: BLE001
                pass
        for el, attr, link, _pos in root.iterlinks():
            if include_all or (el.tag == "a" and attr == "href"):
                out.append(link)
    else:
        for href in re.findall(r'href=["\']([^"\']+)["\']', html, re.I):
            out.append(urllib.parse.urljoin(base, href) if base else href)
    # de-dup, preserve order, drop non-navigational schemes
    seen, deduped = set(), []
    for u in out:
        if u.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        u = u.split("#", 1)[0]            # fragments never matter for fetching
        if u and u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


# --------------------------------------------------------------------------- tables
def get_tables(text: str) -> List[_RawTable]:
    """Raw table rows (with row/col spans + header-row count) via lxml. Empty list if lxml is absent,
    so the caller can fall back to the stdlib table engine. Cells are i18n-safe (text_content)."""
    root = parse_dom(text)
    if root is None:
        return []
    tables: List[_RawTable] = []
    for tbl in root.xpath("//table"):
        rows: List[_RawRow] = []
        header_flags: List[bool] = []
        for tr in tbl.xpath(".//tr"):
            row: _RawRow = []
            had_th = False
            for cell in tr.xpath("./td | ./th"):
                tag = cell.tag if isinstance(cell.tag, str) else ""
                had_th = had_th or tag == "th"
                txt = " ".join(cell.text_content().split())
                rs = _span(cell.get("rowspan"))
                cs = _span(cell.get("colspan"))
                row.append((txt, rs, cs))
            if row:
                rows.append(row)
                header_flags.append(had_th)
        header_rows = 0
        for is_h in header_flags:
            if is_h:
                header_rows += 1
            else:
                break
        if rows:
            tables.append((rows, header_rows))
    return tables


def _span(v: Optional[str]) -> int:
    try:
        return max(1, int(str(v).strip()))
    except (TypeError, ValueError):
        return 1
