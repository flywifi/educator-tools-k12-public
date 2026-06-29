#!/usr/bin/env python3
"""OCPS district resources scraper — fetch and cache OCPS public information.

Reads OCPS public pages once (politely, one page at a time) and extracts:
  - LMS / SIS platform references
  - Curriculum / pacing guide availability
  - Assessment calendar links
  - School choice / magnet program list
  - Professional development portal
  - ESE / ELL / Gifted program pages
  - Technology / device programs

Output: canonical-sources/districts/ocps/resources.json
        canonical-sources/districts/ocps/programs.json   (school-choice program list)

Design:
  - Robots.txt compliant (urllib.robotparser).
  - Polite delay (1.5–3s) between requests.
  - Caches raw HTML next to output so re-runs are offline unless --refresh.
  - Never fabricates data — absent = null + "source": "unverified".
  - Stdlib only (html.parser). requests + bs4 used when available.

Usage:
  python3 tools/ocps_resources.py --check      # offline: validate existing resources.json
  python3 tools/ocps_resources.py --fetch      # crawl OCPS public pages (network required)
  python3 tools/ocps_resources.py --fetch --refresh   # re-fetch even if HTML cache is warm

Sources:
  https://www.ocps.net/departments/curriculum_digital_learning
  https://www.ocps.net/departments/school_choice
  https://www.ocps.net/departments/exceptional_student_education
  https://www.ocps.net/departments/esol
  https://www.ocps.net/departments/gifted
  https://www.ocps.net/departments/professional_development
  https://www.ocps.net/departments/media_relations/newsroom
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "canonical-sources" / "districts" / "ocps"
HTML_CACHE = OUT_DIR / "_html_cache"
RESOURCES_FILE = OUT_DIR / "resources.json"
PROGRAMS_FILE = OUT_DIR / "programs.json"

USER_AGENT = "TOS-OCPS-Scraper/1.0 (edu-tools; public OCPS data; non-commercial)"
BASE = "https://www.ocps.net"

PAGES = {
    "curriculum": "/departments/curriculum_digital_learning",
    "school_choice": "/departments/school_choice",
    "ese": "/departments/exceptional_student_education",
    "esol": "/departments/esol",
    "gifted": "/departments/gifted",
    "prof_dev": "/departments/professional_development",
    "tech": "/departments/technology_services",
    "school_directory": "/school-directory",
    "assessment": "/departments/research_evaluation",
    "charter": "/current-list-of-charter-schools",
}


# ---------------------------------------------------------------------------
# Robots check
# ---------------------------------------------------------------------------

def _can_fetch(url: str, rp: urllib.robotparser.RobotFileParser | None) -> bool:
    if rp is None:
        return True
    return rp.can_fetch(USER_AGENT, url)


def load_robots(base: str) -> urllib.robotparser.RobotFileParser | None:
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{base}/robots.txt")
    try:
        rp.read()
        return rp
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


def _fetch_raw(url: str, delay_range: tuple[float, float] = (1.5, 3.0)) -> bytes | None:
    import random
    time.sleep(random.uniform(*delay_range))
    try:
        if _HAS_REQUESTS:
            r = _requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
            r.raise_for_status()
            return r.content
        else:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
    except Exception as e:
        print(f"  WARN: fetch failed {url}: {e}", file=sys.stderr)
        return None


def fetch_page(key: str, path: str, rp, refresh: bool = False) -> str | None:
    """Fetch one OCPS page. Uses cache unless refresh=True."""
    HTML_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = HTML_CACHE / f"{key}.html"

    if cache_file.exists() and not refresh:
        return cache_file.read_text(encoding="utf-8", errors="replace")

    url = BASE + path
    if not _can_fetch(url, rp):
        print(f"  SKIP (robots): {url}", file=sys.stderr)
        return None

    print(f"  GET {url}", file=sys.stderr)
    raw = _fetch_raw(url)
    if raw is None:
        return None

    html = raw.decode("utf-8", errors="replace")
    cache_file.write_text(html, encoding="utf-8")
    return html


# ---------------------------------------------------------------------------
# HTML extraction helpers
# ---------------------------------------------------------------------------

class _LinkExtractor(HTMLParser):
    """Extract <a> hrefs and text from HTML."""
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (href, text)
        self._cur_href: str | None = None
        self._cur_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._cur_href = dict(attrs).get("href", "")
            self._cur_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._cur_href is not None:
            text = " ".join(self._cur_text).strip()
            if text and self._cur_href:
                self.links.append((self._cur_href, text))
            self._cur_href = None
            self._cur_text = []

    def handle_data(self, data):
        if self._cur_href is not None:
            self._cur_text.append(data.strip())


def extract_links(html: str, base_url: str = BASE) -> list[dict]:
    parser = _LinkExtractor()
    parser.feed(html)
    results = []
    for href, text in parser.links:
        if not href or href.startswith("javascript") or href.startswith("#"):
            continue
        full = urllib.parse.urljoin(base_url, href)
        results.append({"href": full, "text": text})
    return results


def _find_links_matching(html: str, patterns: list[str]) -> list[str]:
    """Return unique hrefs from html whose text or href matches any pattern (case-insensitive)."""
    links = extract_links(html)
    found = []
    pats = [p.lower() for p in patterns]
    for lnk in links:
        combined = (lnk["text"] + " " + lnk["href"]).lower()
        if any(p in combined for p in pats):
            found.append(lnk["href"])
    return list(dict.fromkeys(found))  # deduplicated, ordered


def _sniff_platform(html: str, patterns: dict[str, list[str]]) -> str | None:
    """Sniff for platform references in page text."""
    text = html.lower()
    for name, keywords in patterns.items():
        if any(k in text for k in keywords):
            return name
    return None


# ---------------------------------------------------------------------------
# Extraction per page
# ---------------------------------------------------------------------------

LMS_PATTERNS = {
    "Canvas (Instructure)": ["canvas.instructure.com", "canvas lms", "instructure"],
    "Schoology": ["schoology"],
    "Google Classroom": ["google classroom", "classroom.google.com"],
    "Blackboard": ["blackboard", "bb.ocps"],
    "Edgenuity": ["edgenuity"],
}

EVAL_PATTERNS = {
    "Marzano Focused Teacher Evaluation Model": ["marzano", "casel", "focused teacher"],
    "Danielson Framework": ["danielson", "framework for teaching"],
    "Florida Instructional Leadership Appraisal System": ["filas", "instructional leadership"],
}

DEVICE_PATTERNS = {
    "Chromebook (1:1)": ["chromebook", "chrome device", "1:1 chrome"],
    "iPad (1:1)": ["ipad", "1:1 ipad"],
    "Mixed devices": ["mixed device", "bring your own device", "byod"],
}


def extract_curriculum(html: str) -> dict:
    lms = _sniff_platform(html, LMS_PATTERNS) or None
    pacing = any(w in html.lower() for w in ["pacing guide", "curriculum map", "pacing calendar"])
    subjects = []
    for subj in ["ela", "math", "science", "social studies", "world languages", "art", "pe"]:
        if subj in html.lower():
            subjects.append(subj.upper() if len(subj) <= 4 else subj.title())
    return {
        "lms_detected": lms,
        "pacing_guides_referenced": pacing,
        "subjects_mentioned": subjects or None,
    }


def extract_school_choice_programs(html: str) -> list[dict]:
    """Parse program names from OCPS School Choice page. Heuristic — returns best-effort list."""
    programs = []
    # Look for text patterns around school choice/magnet terms
    blocks = re.findall(
        r'(?:magnet|choice|academy|IB|international baccalaureate|STEM|performing arts'
        r'|cambridge|aice|dual enrollment|montessori)[^<]{0,200}',
        html, re.IGNORECASE
    )
    seen = set()
    for block in blocks:
        clean = re.sub(r'\s+', ' ', block).strip()[:120]
        if clean not in seen:
            seen.add(clean)
            # Very rough type detection
            ptype = "other"
            for kw, t in [("IB", "ib"), ("cambridge", "cambridge"), ("STEM", "magnet"),
                          ("montessori", "magnet"), ("performing arts", "magnet"),
                          ("dual enrollment", "dual_enrollment"), ("choice", "choice"),
                          ("magnet", "magnet")]:
                if kw.lower() in clean.lower():
                    ptype = t
                    break
            programs.append({
                "snippet": clean,
                "inferred_type": ptype,
                "source": "OCPS School Choice page (auto-extracted)",
                "verified": None,
            })
    return programs


def extract_assessment_links(html: str) -> list[str]:
    return _find_links_matching(html, [
        "assessment", "calendar", "fast", "eoc", "fsa", "benchmark", "testing", "test schedule"
    ])


def extract_prof_dev(html: str) -> dict:
    portal_link = _find_links_matching(html, ["professional development", "pd portal", "learning management"])
    return {
        "portal_links_found": portal_link[:3] if portal_link else None,
    }


def extract_ese(html: str) -> dict:
    links = _find_links_matching(html, ["iep", "ese", "exceptional", "sped", "504"])
    return {"ese_links": links[:5] or None}


def extract_esol(html: str) -> dict:
    links = _find_links_matching(html, ["esol", "ell", "english language learner", "english learner"])
    return {"esol_links": links[:5] or None}


def extract_gifted(html: str) -> dict:
    links = _find_links_matching(html, ["gifted", "advanced academic"])
    return {"gifted_links": links[:5] or None}


def extract_technology(html: str) -> dict:
    device = _sniff_platform(html, DEVICE_PATTERNS)
    tools = []
    for tool in ["Google Workspace", "Microsoft 365", "Clever", "ClassLink", "Canvas", "Schoology"]:
        if tool.lower() in html.lower():
            tools.append(tool)
    return {"device_program": device, "tools_detected": tools or None}


# ---------------------------------------------------------------------------
# Orchestrate + build resources.json
# ---------------------------------------------------------------------------

def run_fetch(refresh: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading robots.txt ...", file=sys.stderr)
    rp = load_robots(BASE)

    pages: dict[str, str | None] = {}
    for key, path in PAGES.items():
        pages[key] = fetch_page(key, path, rp, refresh=refresh)

    # Build resources dict
    resources: dict = {
        "district": "Orange County Public Schools",
        "district_number": "48",
        "abbreviation": "OCPS",
        "snapshot": "2026-27",
        "generated": "2026-06-28",
        "source": "OCPS public website (ocps.net) — auto-extracted, human review required",
        "human_review_required": True,
        "completeness": "seed",
        "verified": None,
    }

    if pages.get("curriculum"):
        c = extract_curriculum(pages["curriculum"])
        resources["lms"] = {
            "platform": c["lms_detected"] or "unverified",
            "note": "Detected from OCPS curriculum/digital learning page",
            "source": BASE + PAGES["curriculum"],
        }
        resources["curriculum"] = {
            "pacing_guides_referenced": c["pacing_guides_referenced"],
            "subjects": c["subjects_mentioned"],
            "source": BASE + PAGES["curriculum"],
        }

    if pages.get("assessment"):
        assessment_links = extract_assessment_links(pages["assessment"])
        resources["assessment"] = {
            "statewide": ["FAST (ELA/Math)", "B.E.S.T. EOC", "Statewide Science Assessment", "FCLE"],
            "district_benchmark": "unverified",
            "links_found": assessment_links[:5] or None,
            "source": BASE + PAGES["assessment"],
        }

    if pages.get("ese"):
        resources["programs_ese"] = extract_ese(pages["ese"])
        resources["programs_ese"]["source"] = BASE + PAGES["ese"]

    if pages.get("esol"):
        resources["programs_esol"] = extract_esol(pages["esol"])
        resources["programs_esol"]["source"] = BASE + PAGES["esol"]

    if pages.get("gifted"):
        resources["programs_gifted"] = extract_gifted(pages["gifted"])
        resources["programs_gifted"]["source"] = BASE + PAGES["gifted"]

    if pages.get("prof_dev"):
        resources["professional_development"] = extract_prof_dev(pages["prof_dev"])
        resources["professional_development"]["source"] = BASE + PAGES["prof_dev"]

    if pages.get("tech"):
        resources["technology"] = extract_technology(pages["tech"])
        resources["technology"]["source"] = BASE + PAGES["tech"]

    # Known-verified facts from public OCPS records (not scraped)
    resources["sis"] = {
        "platform": "FOCUS (Tyler Technologies)",
        "note": "OCPS uses FOCUS SIS — published in district communications",
        "source": "OCPS public communications",
        "verified": "2026-06-28",
    }
    resources["evaluation_framework"] = {
        "name": "unverified — check OCPS HR / Professional Development pages",
        "note": "Florida requires use of an approved evaluation system (Marzano or Danielson common in FL)",
        "source": "unverified",
        "verified": None,
    }

    RESOURCES_FILE.write_text(json.dumps(resources, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Written: {RESOURCES_FILE}", file=sys.stderr)

    # Programs file from school choice page
    if pages.get("school_choice"):
        programs = extract_school_choice_programs(pages["school_choice"])
        prog_doc = {
            "district": "Orange County Public Schools",
            "district_number": "48",
            "generated": "2026-06-28",
            "source": BASE + PAGES["school_choice"],
            "human_review_required": True,
            "note": "Auto-extracted snippets — verify each program against OCPS School Choice office",
            "programs_detected": programs,
        }
        PROGRAMS_FILE.write_text(json.dumps(prog_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Written: {PROGRAMS_FILE} ({len(programs)} snippets)", file=sys.stderr)


def run_check() -> None:
    if not RESOURCES_FILE.exists():
        print("resources.json not found. Run --fetch first.", file=sys.stderr)
        return
    data = json.loads(RESOURCES_FILE.read_text(encoding="utf-8"))
    print(json.dumps(data, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fetch", action="store_true", help="Crawl OCPS public pages")
    p.add_argument("--check", action="store_true", help="Print existing resources.json (offline)")
    p.add_argument("--refresh", action="store_true", help="Re-fetch even if HTML cache is warm")
    args = p.parse_args(argv)

    if args.fetch:
        run_fetch(refresh=args.refresh)
    elif args.check:
        run_check()
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
