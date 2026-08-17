#!/usr/bin/env python3
"""Assert every atom's DECLARED Output block against shared/atoms/atom-io.schema.json.

Three defects motivated this, all found by reading 43 SKILL.md files by hand:
  - all 43 atoms cited `references/metadata-schema.md`, a file no atom has (their references/
    holds artifact-types.md, method.md and quality-gates.md only) — 43 dangling references
  - meeting-classify declared `"confidence": 0.95`, a float, against the schema's string enum
    ["high","medium","low"]
  - standards-crosswalk was the only atom whose frontmatter description carried no Do-NOT clause

None of these needed a model to find and none needs one to prevent. The schema already codifies
the envelope (`required: ["tool","human_review_required"]`, with human_review_required `const: true`
and `tool` matching the atom name); nothing had ever checked a SKILL.md against it.

Exit: 0 clean, 1 findings.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATOMS = ROOT / "skills" / "atoms"
SCHEMA = ROOT / "shared" / "atoms" / "atom-io.schema.json"


def declared_output(text: str):
    """The ## Output JSON fence of a SKILL.md, parsed. None when absent or not parseable."""
    m = re.search(r"##\s*Output\s*\n+```(?:json)?\n(.*?)\n```", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def check() -> list:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    # The output envelope is nested at properties.output.properties — NOT at the top level. My
    # first version read schema["properties"]["confidence"], got None, and silently skipped the
    # confidence check entirely; the twin that plants `"confidence": 0.9` went uncaught. A guard
    # that reads the wrong key is a guard that always passes.
    out_props = ((schema.get("properties", {}).get("output") or {}).get("properties") or {})
    conf_enum = (out_props.get("confidence") or {}).get("enum")
    assert conf_enum, "atom-io.schema.json no longer declares a confidence enum where expected"
    findings = []
    for d in sorted(p for p in ATOMS.iterdir() if (p / "SKILL.md").exists()):
        name, rel = d.name, f"skills/atoms/{d.name}/SKILL.md"
        text = (d / "SKILL.md").read_text(encoding="utf-8")

        # every backticked references/X.md must exist in THIS atom's references/
        for ref in re.findall(r"`references/([A-Za-z0-9._-]+)`", text):
            if not (d / "references" / ref).exists():
                findings.append(f"{rel}: cites `references/{ref}` which this atom does not have")

        out = declared_output(text)
        if out is None:
            findings.append(f"{rel}: ## Output block missing or not valid JSON")
            continue
        if out.get("tool") != name:
            findings.append(f"{rel}: declared tool={out.get('tool')!r}, expected {name!r}")
        if out.get("human_review_required") is not True:
            findings.append(f"{rel}: human_review_required must be literally true "
                            f"(declared {out.get('human_review_required')!r})")
        if conf_enum and "confidence" in out and out["confidence"] not in conf_enum:
            findings.append(f"{rel}: confidence={out['confidence']!r} violates the schema enum "
                            f"{conf_enum}")

        desc = re.search(r'description:\s*"(.*?)"\s*\n', text, re.S)
        if desc and "do not" not in desc.group(1).lower():
            findings.append(f"{rel}: frontmatter description has no 'Do NOT use' clause")
    return findings


def main(argv) -> int:
    if "--self-test" in argv:
        fails = 0
        def ck(label, cond):
            nonlocal fails
            print(f"{'PASS' if cond else 'FAIL'} {label}")
            fails += (not cond)
        ck("an Output fence parses", declared_output('## Output\n\n```json\n{"tool":"x"}\n```') ==
           {"tool": "x"})
        ck("a missing Output fence is None", declared_output("## Input\n") is None)
        ck("an unparseable fence is None", declared_output("## Output\n\n```json\n{oops\n```") is None)
        ck("the live tree is clean", not check())
        print(f"self-test: {fails} failure(s)")
        return 1 if fails else 0
    f = check()
    print("\n".join(f) if f else
          f"OK — {len(list(ATOMS.iterdir()))} atoms conform to shared/atoms/atom-io.schema.json "
          f"(tool name, human_review_required, confidence enum, live references, Do-NOT clause)")
    return 1 if f else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
