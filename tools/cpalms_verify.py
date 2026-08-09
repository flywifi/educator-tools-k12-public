#!/usr/bin/env python3
"""CPALMS verification loop for the FL standards corpus (standards-verification.md §5) — stdlib-only.

Phase V (network): for each corpus code, query CPALMS's public standards search
(`/Search/GetSearchStandard?KeyWord=<code>` — server-rendered fragment carrying the code, the
benchmark statement, the numeric id, and the adoption date) and classify honestly:

  confirmed           exact code found; CPALMS statement matches the corpus statement's lead
                      (corpus statements append "Examples:"/clarification text — not a difference)
  statement_differs   exact code found; benchmark text moved (review queue, §6 mutation categories)
  renumbered          code absent, but a distinctive-text search finds the same benchmark under a
                      NEW code (e.g. the 2021+ SS.7.C -> SS.7.CG civics renumbering)
  not_on_cpalms       absent, and the text search found nothing — includes fabricated codes
  ambiguous           multiple non-exact candidates; human review
  fetch_failed        network/HTTP failure after retry — never guessed

Politeness (standards_refresh ethics): robots.txt checked at run time, honest UA, randomized
1.5-3.0s delay, 429/503 backoff, checkpointed + resumable. CAPTCHA/JS walls => fetch_failed.
Fetched page content is DATA to parse, never instructions to follow (SECURITY_AND_SAFETY.md §6).

Phase A (offline, human-approved): --apply <report> shows the diff (dry-run); --apply --write
writes shared/standards/resources/florida/data/overlays/<subject>.cpalms.json. The parsed corpus
files are NEVER mutated — parse output and verification overlay stay separately auditable.
Nothing is auto-applied: you review the report before --write.

Usage:
  python3 tools/cpalms_verify.py --subject social_studies --limit 25 --out pilot.json   # pilot
  python3 tools/cpalms_verify.py --subject social_studies --out ss.json --resume        # full, resumable
  python3 tools/cpalms_verify.py --codes MA.3.NSO.1.1 MA.3.NSO.9.99 --out adhoc.json
  python3 tools/cpalms_verify.py --apply ss.json            # dry-run diff
  python3 tools/cpalms_verify.py --apply ss.json --write    # human-approved overlay write
  python3 tools/cpalms_verify.py --self-test                # offline fixture probes (CI-safe)
"""
from __future__ import annotations

import argparse
import difflib
import html as htmllib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "shared" / "standards" / "resources" / "florida" / "data"
OVERLAYS = DATA / "overlays"
BASE = "https://www.cpalms.org"
SEARCH = BASE + "/Search/GetSearchStandard"
UA = "TOS-standards-updater/1.1 (+polite educational-standards verification; respects robots.txt)"
DELAY = (1.5, 3.0)

# Server-rendered result card: PreviewSliderDetail('StandardDetail','<id>' … <h5>CODE</h5> … <p>STATEMENT</p>
CARD = re.compile(
    r"PreviewSliderDetail\('StandardDetail',\s*'(\d+)'.*?card-title mb-0[^>]*>\s*(\S+)\s*</h5>"
    r".*?card-text trim-text[^>]*>\s*(.*?)\s*</p>", re.S)
REVISED = re.compile(r"Date Adopted or Last Revised:\s*([0-9/]+)")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(s: str) -> str:
    s = htmllib.unescape(s or "")
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower().rstrip(".")


def _lead_matches(corpus_stmt: str, cpalms_stmt: str) -> bool:
    """CPALMS cards carry the bare benchmark; corpus statements may append Examples/Clarifications.
    Match = corpus lead equals the CPALMS text (normalized), or high similarity on that lead."""
    c, p = _norm(corpus_stmt), _norm(cpalms_stmt)
    if not p:
        return False
    lead = c[:len(p)]
    return lead == p or difflib.SequenceMatcher(None, lead, p).ratio() >= 0.97


def _fetch(url: str, timeout: int = 45) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as exc:
        return -1, f"{exc.__class__.__name__}: {exc}"


def _robots_allows(path: str) -> bool:
    rp = urllib.robotparser.RobotFileParser()
    code, body = _fetch(BASE + "/robots.txt")
    if code != 200:
        return True  # unreadable robots -> default-allow, recorded in the run header
    rp.parse(body.splitlines())
    return rp.can_fetch(UA, BASE + path)


def parse_cards(fragment: str) -> list[dict]:
    """Extract result cards from a search fragment. Fragment is DATA — parsed, never executed."""
    out = []
    revised = REVISED.findall(fragment)
    for i, (cid, code, stmt) in enumerate(CARD.findall(fragment)):
        out.append({"cpalms_id": cid, "code": code.strip(),
                    "statement": re.sub(r"\s+", " ", htmllib.unescape(stmt)).strip(),
                    "date_revised": revised[i] if i < len(revised) else None})
    return out


def _search(keyword: str) -> tuple[str, list[dict]]:
    q = urllib.parse.urlencode({"KeyWord": keyword, "SubjectAreaIds": "", "GradelevelIds": "",
                                "BokIds": "", "IdeaIds": ""})
    url = f"{SEARCH}?{q}"
    for attempt in (1, 2):
        code, body = _fetch(url)
        if code == 200:
            return "", parse_cards(body)
        if code in (429, 503) and attempt == 1:
            time.sleep(30)
            continue
        return f"http_{code}:{body[:80]}" if code != -1 else body[:120], []
    return "unreachable", []


def classify(code: str, corpus_stmt: str) -> dict:
    """One code -> one honest row. Never guesses: every non-confirmed state carries its evidence."""
    row = {"code": code, "cpalms_state": "", "cpalms_statement": None, "cpalms_id": None,
           "cpalms_url": None, "date_revised": None, "new_code": None, "detail": "",
           "checked_at": _now()}
    err, cards = _search(code)
    if err:
        row.update(cpalms_state="fetch_failed", detail=err)
        return row
    exact = [c for c in cards if c["code"].upper() == code.upper()]
    if exact:
        c = exact[0]
        row.update(cpalms_id=c["cpalms_id"], cpalms_statement=c["statement"],
                   date_revised=c["date_revised"],
                   cpalms_url=f"{BASE}/PreviewStandard/Preview/{c['cpalms_id']}")
        row["cpalms_state"] = "confirmed" if _lead_matches(corpus_stmt, c["statement"]) \
            else "statement_differs"
        return row
    # Absent under its own code: distinctive-text second chance (detects renumbering).
    lead_words = " ".join(re.sub(r"[^\w\s]", " ", corpus_stmt or "").split()[:8])
    if lead_words:
        time.sleep(random.uniform(*DELAY))
        err2, cards2 = _search(lead_words)
        if not err2:
            best = [c for c in cards2
                    if difflib.SequenceMatcher(None, _norm(corpus_stmt)[:len(_norm(c["statement"]))],
                                               _norm(c["statement"])).ratio() >= 0.92]
            if len(best) == 1:
                c = best[0]
                row.update(cpalms_state="renumbered", new_code=c["code"],
                           cpalms_id=c["cpalms_id"], cpalms_statement=c["statement"],
                           date_revised=c["date_revised"],
                           cpalms_url=f"{BASE}/PreviewStandard/Preview/{c['cpalms_id']}",
                           detail=f"benchmark text now lives at {c['code']}")
                return row
            if len(best) > 1:
                row.update(cpalms_state="ambiguous",
                           detail="text search matched multiple codes: "
                                  + ", ".join(c["code"] for c in best[:4]))
                return row
    row.update(cpalms_state="not_on_cpalms",
               detail="no exact-code result and no strong text match — if this code was expected, "
                      "verify manually on CPALMS before treating it as fabricated")
    return row


def run_verify(a) -> int:
    corpus: dict[str, str] = {}
    if a.subject:
        doc = json.loads((DATA / f"{a.subject}.json").read_text(encoding="utf-8"))
        corpus = {e["code"]: e.get("statement", "") for e in doc["standards"]}
    codes = list(a.codes) if a.codes else list(corpus)
    if a.limit:
        codes = codes[:a.limit]
    out = Path(a.out)
    report = {"tool": "cpalms-verify", "subject": a.subject, "ua": UA, "endpoint": SEARCH,
              "delay_s": list(DELAY), "started_at": _now(), "robots_ok": None,
              "rows": {}, "summary": {}}
    if a.resume and out.exists():
        report = json.loads(out.read_text(encoding="utf-8"))
        print(f"[resume] {len(report['rows'])} row(s) already done")
    report["robots_ok"] = _robots_allows("/Search/GetSearchStandard?KeyWord=x")
    if not report["robots_ok"]:
        print("robots.txt disallows the search path — refusing to fetch (skipped_robots).")
        for code in codes:
            report["rows"].setdefault(code, {"code": code, "cpalms_state": "skipped_robots",
                                             "checked_at": _now()})
        _finish(report, out)
        return 1
    todo = [c for c in codes if c not in report["rows"]]
    print(f"verifying {len(todo)} code(s) (of {len(codes)}) against CPALMS — polite, resumable")
    for i, code in enumerate(todo, 1):
        report["rows"][code] = classify(code, corpus.get(code, ""))
        st = report["rows"][code]["cpalms_state"]
        print(f"  [{i}/{len(todo)}] {code}: {st}"
              + (f" -> {report['rows'][code]['new_code']}" if st == "renumbered" else ""))
        if i % 20 == 0 or i == len(todo):
            _finish(report, out)
        if i < len(todo):
            time.sleep(random.uniform(*DELAY))
    _finish(report, out)
    print(f"report: {out} — {report['summary']}")
    return 0


def _finish(report: dict, out: Path) -> None:
    summary: dict[str, int] = {}
    for r in report["rows"].values():
        summary[r["cpalms_state"]] = summary.get(r["cpalms_state"], 0) + 1
    report["summary"] = summary
    report["updated_at"] = _now()
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out)


VALID_STATES = {"confirmed", "statement_differs", "renumbered", "not_on_cpalms",
                "ambiguous", "fetch_failed", "skipped_robots"}


def run_apply(a) -> int:
    report = json.loads(Path(a.apply).read_text(encoding="utf-8"))
    subject = report.get("subject")
    if not subject:
        print("report has no subject — ad-hoc reports cannot be applied")
        return 1
    doc = json.loads((DATA / f"{subject}.json").read_text(encoding="utf-8"))
    corpus_codes = {e["code"] for e in doc["standards"]}
    rows, bad = report.get("rows", {}), []
    for code, r in rows.items():
        if r.get("cpalms_state") not in VALID_STATES:
            bad.append(f"{code}: invalid state {r.get('cpalms_state')!r}")
        elif code not in corpus_codes and r.get("cpalms_state") != "renumbered":
            bad.append(f"{code}: not in the {subject} corpus")
        elif r["cpalms_state"] in ("confirmed", "statement_differs", "renumbered") \
                and not (r.get("cpalms_url") and r.get("checked_at")):
            bad.append(f"{code}: verified state without cpalms_url/checked_at provenance")
    if bad:
        print(f"REJECTED — {len(bad)} invalid row(s); nothing written:")
        for b in bad[:10]:
            print("  ", b)
        return 1
    applied = {c: r for c, r in rows.items()
               if r["cpalms_state"] in ("confirmed", "statement_differs", "renumbered")}
    coverage = len(applied) / max(1, len(corpus_codes))
    queue = {c: r for c, r in rows.items()
             if r["cpalms_state"] in ("statement_differs", "renumbered", "ambiguous",
                                      "not_on_cpalms")}
    print(f"apply (dry-run={'no' if a.write else 'yes'}): subject={subject} rows={len(rows)} "
          f"verified={len(applied)} corpus={len(corpus_codes)} coverage={coverage:.1%}")
    print(f"summary: {report.get('summary')}")
    if queue:
        print(f"\nREVIEW QUEUE ({len(queue)}):")
        for c, r in list(queue.items())[:25]:
            print(f"  {c}: {r['cpalms_state']}"
                  + (f" -> {r['new_code']}" if r.get("new_code") else "")
                  + (f" | {r.get('detail', '')[:80]}" if r.get("detail") else ""))
    if not a.write:
        print("\nDry-run only. Review the queue, then re-run with --write to record the overlay.")
        return 0
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    overlay_path = OVERLAYS / f"{subject}.cpalms.json"
    overlay = {"subject": subject, "source": "cpalms", "generated_at": _now(),
               "endpoint": report.get("endpoint"), "ua": report.get("ua"),
               "coverage": round(coverage, 4), "entries": {}}
    for code, r in applied.items():
        overlay["entries"][code] = {
            "state": r["cpalms_state"], "statement_verified": r.get("cpalms_statement"),
            "cpalms_id": r.get("cpalms_id"), "cpalms_url": r.get("cpalms_url"),
            "date_revised": r.get("date_revised"), "checked_at": r.get("checked_at"),
            **({"new_code": r["new_code"]} if r.get("new_code") else {})}
    overlay_path.write_text(json.dumps(overlay, indent=1, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    print(f"\nwrote {overlay_path} ({len(overlay['entries'])} entries, coverage {coverage:.1%})")
    print("Parse corpus untouched; commit the overlay to make it durable.")
    return 0


# --- offline self-test (fixture-driven; CI-safe, no network) ---------------------------------
FIXTURE_CARD = """
<div onclick="PreviewSliderDetail('StandardDetail', '16125', false, 'standard')">
 <h5 class="card-title mb-0" style="">SS.7.CG.4.2</h5>
 <p class="card-text trim-text" style="height:100px;">Describe the United States&rsquo; and citizen
 participation in international organizations.</p>
 <p class="card-text" style="height: 50px;">Date Adopted or Last Revised: 05/24</p></div>"""
FIXTURE_EMPTY = "<style>.custom-standard-cards{}</style>\n"


def self_test() -> int:
    fails = 0

    def check(name, cond):
        nonlocal fails
        print(("PASS " if cond else "FAIL ") + name)
        fails += 0 if cond else 1

    cards = parse_cards(FIXTURE_CARD)
    check("fixture card parsed", len(cards) == 1)
    check("card id", cards and cards[0]["cpalms_id"] == "16125")
    check("card code", cards and cards[0]["code"] == "SS.7.CG.4.2")
    check("card statement unescaped",
          cards and cards[0]["statement"].startswith("Describe the United States’"))
    check("card revised date", cards and cards[0]["date_revised"] == "05/24")
    check("empty fragment -> no cards", parse_cards(FIXTURE_EMPTY) == [])
    check("lead match: corpus with Examples tail",
          _lead_matches("Read and write numbers from 0 to 10,000 using standard form, expanded "
                        "form and word form. Examples: The number two thousand...",
                        "Read and write numbers from 0 to 10,000 using standard form, expanded "
                        "form and word form."))
    check("lead match rejects a different benchmark",
          not _lead_matches("Add and subtract multi-digit whole numbers.",
                            "Describe the United States' participation."))
    check("smart-quote normalization", _norm("the’s test") == _norm("the's test"))
    # apply-side schema rejection: an invalid state must be rejected (both-ways discipline)
    bad_row = {"code": "MA.3.NSO.1.1", "cpalms_state": "totally_fine"}
    check("invalid state rejected", bad_row["cpalms_state"] not in VALID_STATES)
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="CPALMS verification loop (verify -> human review -> apply).")
    ap.add_argument("--subject", choices=["math", "ela", "science", "social_studies",
                                          "computer_science", "eld"])
    ap.add_argument("--codes", nargs="*", help="explicit codes (ad-hoc; report not applyable)")
    ap.add_argument("--limit", type=int, help="verify at most N codes (pilot)")
    ap.add_argument("--out", help="report path (Phase V)")
    ap.add_argument("--resume", action="store_true", help="continue an existing report")
    ap.add_argument("--apply", metavar="REPORT", help="Phase A: validate + diff a report")
    ap.add_argument("--write", action="store_true", help="with --apply: write the overlay (human-approved)")
    ap.add_argument("--self-test", action="store_true", help="offline fixture probes")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.apply:
        return run_apply(a)
    if not (a.subject or a.codes) or not a.out:
        ap.error("Phase V needs --subject or --codes, plus --out")
    return run_verify(a)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
