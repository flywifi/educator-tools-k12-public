"""IcsParser - iCalendar (.ics) reader, stdlib only.

Reads RFC-5545 calendar invites/events (the file a teacher drops when they get a meeting invite) and
normalizes each VEVENT into UDOM text blocks plus a structured `events` list in the recovery
diagnostics, so a consumer (e.g. skills/meeting-classifier) can use calendar evidence without retyping
it. Nothing is fabricated: a file that is not iCalendar yields an empty, zero-confidence result.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from ..governance import Confidence, Provenance, new_id
from ..orchestration import Parser, RecoveryResult
from ..udom import Block, Source

ICS_TYPE = "text/calendar"


def _unfold(text: str) -> List[str]:
    """RFC-5545 line unfolding: a line starting with a space/tab continues the previous one."""
    out: List[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and out:
            out[-1] += raw[1:]
        else:
            out.append(raw)
    return out


def _split_line(line: str) -> Tuple[str, Dict[str, str], str]:
    """Split `NAME;PARAM=VALUE;...:VALUE` into (name, params, value), honoring quoted params."""
    in_quote = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quote = not in_quote
        elif ch == ":" and not in_quote:
            head, value = line[:i], line[i + 1:]
            break
    else:
        return "", {}, ""
    parts: List[str] = []
    buf, in_quote = "", False
    for ch in head:
        if ch == '"':
            in_quote = not in_quote
        if ch == ";" and not in_quote:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    name = parts[0].strip()
    params: Dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip().upper()] = v.strip().strip('"')
    return name, params, value


def _unescape(value: str) -> str:
    """Reverse RFC-5545 TEXT escaping (\\n \\, \\; \\\\)."""
    out, i = [], 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append("\n" if nxt in ("n", "N") else nxt)
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _fmt_dt(value: str, tzid: Optional[str]) -> str:
    """Lightly format a basic-format ICS date-time for readability; leave anything else as-is."""
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z)?)?$", value.strip())
    if not m:
        return value.strip()
    y, mo, d, hh, mm, _ss, z = m.groups()
    out = f"{y}-{mo}-{d}"
    if hh is not None:
        out += f" {hh}:{mm}"
        if z:
            out += " UTC"
        elif tzid:
            out += f" ({tzid})"
    return out


def _email_name(value: str, params: Dict[str, str]) -> str:
    return params.get("CN") or re.sub(r"(?i)^mailto:", "", value).strip()


class IcsParser(Parser):
    name = "ics"
    version = "0.1.0"
    capabilities = {"text", "reading_order"}

    def supports(self, media_type: str) -> bool:
        return media_type == ICS_TYPE

    def parse(self, data: bytes, media_type: str, source: Source) -> RecoveryResult:
        text = data.decode("utf-8", "ignore")
        if "BEGIN:VEVENT" not in text.upper():
            return RecoveryResult(blocks=[], extraction_method="native", confidence=0.0,
                                  diagnostics={"format": "ics", "status": "not_icalendar"})
        events = self._events(_unfold(text))
        blocks: List[Block] = []
        for page, ev in enumerate(events, start=1):
            blocks.extend(self._event_blocks(ev, page, source))
        return RecoveryResult(blocks=blocks, extraction_method="native",
                              confidence=0.9 if blocks else 0.0,
                              diagnostics={"format": "ics", "events": events})

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _events(lines: List[str]) -> List[Dict]:
        events: List[Dict] = []
        cur: Optional[Dict] = None
        for line in lines:
            name, params, value = _split_line(line)
            if not name:
                continue
            u = name.upper()
            if u == "BEGIN" and value.upper() == "VEVENT":
                cur = {"attendees": []}
            elif u == "END" and value.upper() == "VEVENT":
                if cur is not None:
                    events.append(cur)
                cur = None
            elif cur is None:
                continue
            elif u == "SUMMARY":
                cur["summary"] = _unescape(value)
            elif u == "DTSTART":
                cur["start"] = _fmt_dt(value, params.get("TZID"))
            elif u == "DTEND":
                cur["end"] = _fmt_dt(value, params.get("TZID"))
            elif u == "LOCATION":
                cur["location"] = _unescape(value)
            elif u == "DESCRIPTION":
                cur["description"] = _unescape(value)
            elif u == "UID":
                cur["uid"] = value.strip()
            elif u == "RRULE":
                cur["rrule"] = value.strip()
            elif u == "ORGANIZER":
                cur["organizer"] = _email_name(value, params)
            elif u == "ATTENDEE":
                cur["attendees"].append(_email_name(value, params))
        return events

    def _event_blocks(self, ev: Dict, page: int, source: Source) -> List[Block]:
        prov = Provenance(source_id=source.filename, parser=self.name, parser_version=self.version,
                          extraction_method="native", page_number=page)

        def blk(kind: str, text: str, level: Optional[int] = None) -> Block:
            return Block(block_id=new_id("b"), type=kind, page_number=page, provenance=prov,
                         confidence=Confidence(value=0.9, level="text", method=f"ics:{kind}"),
                         text=text, level=level)

        out: List[Block] = [blk("heading", f"Calendar event: {ev.get('summary', '(untitled)')}", 1)]
        when = " - ".join(x for x in (ev.get("start"), ev.get("end")) if x)
        rows = [("When", when), ("Location", ev.get("location")),
                ("Organizer", ev.get("organizer")),
                ("Attendees", ", ".join(ev.get("attendees") or [])),
                ("Recurs", ev.get("rrule")), ("Description", ev.get("description"))]
        out.extend(blk("paragraph", f"{label}: {val}") for label, val in rows if val)
        return out
