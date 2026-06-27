#!/usr/bin/env python3
"""export_chatgpt.py — generate TOS-skills.md for ChatGPT web users.

Reads all 29 skill YAML files from platforms/openai/skills/ and writes a single
plain-English reference document (platforms/chatgpt-web/TOS-skills.md) that a teacher
can drag into any ChatGPT Project or conversation window.

This script keeps TOS-skills.md in sync with the YAML source of truth automatically.
The YAML files are the source; TOS-skills.md is a generated output. Never edit
TOS-skills.md by hand — edit the YAML and re-run this script.

Usage:
  python3 tools/export_chatgpt.py              # regenerate TOS-skills.md
  python3 tools/export_chatgpt.py --check      # validate YAMLs only, no write
  python3 tools/export_chatgpt.py --out PATH   # write to a custom path

Zero new dependencies — stdlib only. PyYAML used if installed (better parsing);
stdlib fallback works for all 29 skills.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "platforms" / "openai" / "skills"
OUT_PATH = ROOT / "platforms" / "chatgpt-web" / "TOS-skills.md"

try:
    import yaml as _yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _load(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    # strip comment lines before parsing
    lines = [l for l in text.splitlines() if not l.startswith("#")]
    clean = "\n".join(lines).strip()
    try:
        if HAS_YAML:
            return _yaml.safe_load(clean)
        return json.loads(clean)  # fallback: won't work for YAML-only syntax
    except Exception:
        # manual extraction of the fields we need
        data: dict = {"type": "function", "function": {}}
        fn = data["function"]
        for line in clean.splitlines():
            s = line.strip()
            if s.startswith("name:") and "name" not in fn:
                fn["name"] = s.split(":", 1)[1].strip()
            if s.startswith("description:") and "description" not in fn:
                val = s.split(":", 1)[1].strip()
                if val and val != "|":
                    fn["description"] = val
        # grab multiline description after "description: |"
        if "description" not in fn or not fn["description"]:
            in_desc = False
            desc_lines = []
            for line in clean.splitlines():
                if re.match(r"^\s*description:\s*\|", line):
                    in_desc = True
                    continue
                if in_desc:
                    if line and not line[0].isspace():
                        break
                    desc_lines.append(line.lstrip())
            if desc_lines:
                fn["description"] = "\n".join(desc_lines).strip()
        return data if fn.get("name") else None


def _required_params(fn: dict) -> list[str]:
    return fn.get("parameters", {}).get("required", [])


def _param_descriptions(fn: dict) -> dict[str, str]:
    props = fn.get("parameters", {}).get("properties", {})
    return {k: v.get("description", "").strip() for k, v in props.items()}


def _first_sentence(text: str) -> str:
    """Return the first sentence of a description block."""
    text = text.strip().replace("\n", " ")
    # cut at first period followed by space or end
    m = re.search(r"\.(\s|$)", text)
    if m:
        return text[: m.start() + 1].strip()
    return text[:200].strip()


def _trigger_phrases(description: str) -> list[str]:
    """Extract trigger phrase examples from the description text."""
    phrases = []
    in_triggers = False
    for line in description.splitlines():
        ls = line.strip()
        if "trigger phrases" in ls.lower() or "say something like" in ls.lower():
            in_triggers = True
            continue
        if in_triggers:
            # collect quoted phrases or dash-prefixed examples
            if ls.startswith('"') or ls.startswith("'") or ls.startswith("- "):
                phrase = ls.lstrip("- \"'").rstrip("\"',.")
                if phrase:
                    phrases.append(phrase)
            elif ls and not ls.startswith("#") and len(phrases) >= 3:
                break
            elif ls.startswith("Do NOT") or ls.startswith("Output") or ls.startswith("Integrate"):
                break
    return phrases[:4]


def _do_not_use(description: str) -> list[str]:
    """Extract 'Do NOT use' lines."""
    lines = []
    for line in description.splitlines():
        ls = line.strip()
        if ls.startswith("Do NOT use"):
            lines.append(ls.removeprefix("Do NOT use").strip())
    return lines[:3]


def _build_entry(path: Path) -> str | None:
    data = _load(path)
    if not data:
        print(f"  ERROR: could not load {path.name}", file=sys.stderr)
        return None

    fn = data.get("function", {})
    name = fn.get("name", path.stem)
    description = fn.get("description", "")
    required = _required_params(fn)
    param_descs = _param_descriptions(fn)

    # human-readable title from snake_case name
    title = name.replace("_", " ").title()

    # one-liner: first sentence of description
    one_liner = _first_sentence(description)

    # trigger phrases
    phrases = _trigger_phrases(description)

    # required params as short labels
    req_labels = []
    for r in required:
        short = param_descs.get(r, "")
        short = short.split(".")[0].split("(")[0].strip()[:60]
        req_labels.append(f"{r.replace('_', ' ')} — {short}" if short else r.replace("_", " "))

    # optional params (first 5 non-required)
    optional = [k for k in param_descs if k not in required][:6]
    opt_labels = [k.replace("_", " ") for k in optional]

    # do-not-use constraints
    do_not = _do_not_use(description)

    lines = [
        f"---",
        f"",
        f"## {title}",
        f"",
        f"{one_liner}",
        f"",
    ]

    if phrases:
        lines.append("**Say something like:**")
        for p in phrases:
            lines.append(f'- "{p}"')
        lines.append("")

    if req_labels:
        lines.append(f"**Always provide:** {' · '.join(r.split(' — ')[0] for r in required)}")

    if opt_labels:
        lines.append(f"**Optional:** {' · '.join(opt_labels)}")

    if do_not:
        lines.append("")
        lines.append("**Do not use for:** " + "; ".join(do_not))

    lines.append("")

    return "\n".join(lines)


HEADER = """\
# TOS Skills — ChatGPT Reference Guide

**Teacher Operating System (TOS)** | Drag this file into a ChatGPT Project or conversation.

---

## Before you start: what works on ChatGPT

| Feature | Status |
|---|---|
| All 29 skill structures — lesson plans, IEP goals, assessments, parent comms, etc. | ✅ Works |
| Governance rules — DRAFT label, no student PII, IEP legal boundaries | ✅ Works |
| Output formats — structured artifacts matching TOS specifications | ✅ Works |
| Florida B.E.S.T. standard codes | ⚠️ ChatGPT recalls from training data, NOT a verified corpus. **Always verify every standard code on [cpalms.org](https://www.cpalms.org) before using in any formal document.** |
| Standards corpus search (6,583 FL standards) | ❌ Not available — requires the Claude TOS environment |
| Document parsing pipeline (PDFs, DOCX, scanned files) | ❌ Not available — requires the Claude TOS environment |
| Standards crawler (FLDOE/CPALMS live updates) | ❌ Not available — requires the Claude TOS environment |
| Quality Gates scoring script | ❌ Not available — ChatGPT can approximate in prose only |

**The bottom line:** ChatGPT will follow TOS skill structure and governance rules.
It cannot run code, query the verified standards corpus, or crawl live sources.
For the full TOS experience — including verified standards, document ingestion, and
quality scoring — use the Claude deployment.

---

## How to use this guide

1. **Upload this file** to a ChatGPT Project (Project → Add files) — every chat in
   that project will reference it automatically.
2. **Or paste it** into any conversation window for one-time use.
3. **Tell ChatGPT** which skill you want using the trigger phrases below.
4. **Always verify** Florida standard codes on cpalms.org before formal use.

---

## The 29 TOS Skills

"""

FOOTER = """
---

*Generated by `tools/export_chatgpt.py` from `platforms/openai/skills/*.yaml`.*
*To regenerate after editing a skill: `python3 tools/export_chatgpt.py`*
*Source of truth: the YAML files. Never edit this file by hand.*
"""

# Preferred display order (orchestrators first, then atoms)
SKILL_ORDER = [
    "teacher-core",
    "lesson-planner",
    "assessment-designer",
    "special-education-support",
    "family-communication",
    "meeting-classifier",
    "quality-review",
    "curriculum-mapping",
    "intervention-mtss",
    "presentation-builder",
    "professional-learning",
    "school-administration",
    "document-intelligence",
    "output-validator",
    "feed-curator",
    "standards-updater",
    "teacher-profile",
    "skill-health",
    "skill-repair",
    # atoms
    "atom-standards-match",
    "atom-objective-write",
    "atom-activity-generate",
    "atom-assessment-item",
    "atom-differentiate",
    "atom-quality-check",
    "atom-reading-level",
    "atom-misconception",
    "atom-parent-comm",
    "atom-iep-goal",
]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Generate TOS-skills.md for ChatGPT web users.")
    ap.add_argument("--check", action="store_true",
                    help="validate YAMLs only; do not write output")
    ap.add_argument("--out", metavar="PATH", default=str(OUT_PATH),
                    help=f"output path (default: {OUT_PATH})")
    a = ap.parse_args(argv)

    if not SKILLS_DIR.exists():
        print(f"ERROR: skills dir not found: {SKILLS_DIR}", file=sys.stderr)
        return 2

    # Build ordered file list
    all_files = {f.stem: f for f in SKILLS_DIR.glob("*.yaml")}
    ordered = [all_files[s] for s in SKILL_ORDER if s in all_files]
    remaining = [f for s, f in all_files.items() if s not in SKILL_ORDER]
    skill_files = ordered + sorted(remaining)

    errors = 0
    entries: list[str] = []

    for f in skill_files:
        entry = _build_entry(f)
        if entry is None:
            errors += 1
        else:
            entries.append(entry)
            print(f"  OK   {f.stem}")

    total = len(entries)
    print(f"\n{total} skill(s) processed, {errors} error(s).")

    if errors:
        return 1

    if a.check:
        print("--check passed. No files written.")
        return 0

    content = HEADER + "\n".join(entries) + FOOTER
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    char_count = len(content)
    print(f"Written: {out}  ({char_count:,} chars)")
    if char_count > 50_000:
        print("WARNING: file exceeds 50,000 chars — may not fit in ChatGPT context window "
              "for some models. Consider using a subset.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
