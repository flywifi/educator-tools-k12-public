#!/usr/bin/env python3
"""export_openai.py — build the combined OpenAI tools array from individual skill YAML files.

Reads every YAML file in implementation/gpt/api/skills/ and combines them into:
  - implementation/gpt/api/tools.yaml   (YAML tools array, for passing to client.chat.completions.create)
  - implementation/gpt/api/tools.json   (JSON equivalent, for direct API use)

Usage:
  python3 tools/export_openai.py                  # write tools.yaml + tools.json
  python3 tools/export_openai.py --check           # validate all skill YAMLs, print summary, no write
  python3 tools/export_openai.py --skill lesson-planner  # print one skill's tool definition
  python3 tools/export_openai.py --subset lesson-planner,assessment-designer  # export subset

Output format (YAML):
  tools:
    - type: function
      function:
        name: lesson_planner
        description: |
          ...
        parameters: {...}
    - type: function
      ...

JSON format is the raw list (no "tools:" wrapper) since the Python openai SDK takes a list:
  tools = json.load(open("implementation/gpt/api/tools.json"))
  client.chat.completions.create(model="gpt-4o", tools=tools, messages=[...])
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "implementation" / "gpt" / "api" / "skills"
OUT_YAML = ROOT / "implementation" / "gpt" / "api" / "tools.yaml"
OUT_JSON = ROOT / "implementation" / "gpt" / "api" / "tools.json"

# YAML is stdlib-free — we write it ourselves (only the structure matters).
# If PyYAML is installed, we use it for reliable round-tripping.
try:
    import yaml as _yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _load_yaml_stdlib(text: str) -> dict:
    """Minimal YAML parser for our specific skill YAML structure (no exec, no deps)."""
    # Strip comment lines
    lines = [l for l in text.splitlines() if not l.startswith("#")]
    text = "\n".join(lines).strip()
    # Delegate to PyYAML if available for correctness on complex values
    if HAS_YAML:
        return _yaml.safe_load(text)
    # Minimal fallback: parse type + function.name + function.description (first 200 chars)
    # This is a best-effort stub — install PyYAML for full fidelity
    result: dict = {}
    current_key: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            depth = indent // 2
            current_key = current_key[:depth] + [key]
            obj = result
            for k in current_key[:-1]:
                obj = obj.setdefault(k, {})
            if val and not val.startswith("|"):
                obj[current_key[-1]] = val
    return result


def load_skill(path: Path) -> dict | None:
    """Load and parse one skill YAML file. Returns the tool dict or None on failure."""
    text = path.read_text(encoding="utf-8")
    try:
        if HAS_YAML:
            data = _yaml.safe_load(text)
        else:
            data = _load_yaml_stdlib(text)
    except Exception as e:
        print(f"  ERROR parsing {path.name}: {e}", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        print(f"  ERROR {path.name}: top-level is not a mapping", file=sys.stderr)
        return None
    if data.get("type") != "function":
        print(f"  WARN {path.name}: missing 'type: function'", file=sys.stderr)
    fn = data.get("function", {})
    if not fn.get("name"):
        print(f"  ERROR {path.name}: missing function.name", file=sys.stderr)
        return None
    if not fn.get("description"):
        print(f"  WARN {path.name}: missing function.description", file=sys.stderr)
    return data


def validate_tool(tool: dict, path: Path) -> list[str]:
    """Return a list of validation issues for a tool definition."""
    issues = []
    fn = tool.get("function", {})
    name = fn.get("name", "")
    if not name:
        issues.append("missing function.name")
    if not fn.get("description"):
        issues.append("missing function.description")
    params = fn.get("parameters", {})
    if not params:
        issues.append("missing function.parameters")
    else:
        if params.get("type") != "object":
            issues.append("parameters.type must be 'object'")
        if not params.get("properties"):
            issues.append("parameters.properties is empty")
        required = params.get("required", [])
        props = params.get("properties", {})
        for req in required:
            if req not in props:
                issues.append(f"required field '{req}' not in properties")
    return issues


def _write_yaml(tools: list[dict], path: Path) -> None:
    """Write tools list to YAML. Uses PyYAML when available; hand-rolls otherwise."""
    if HAS_YAML:
        content = "# TOS — OpenAI tools array\n# Generated by tools/export_openai.py\n"
        content += _yaml.dump({"tools": tools}, allow_unicode=True, sort_keys=False,
                              default_flow_style=False)
        path.write_text(content, encoding="utf-8")
    else:
        # Write as JSON embedded in YAML (valid YAML is valid JSON) — readable fallback
        path.write_text(
            "# TOS — OpenAI tools array (JSON-in-YAML; install PyYAML for native YAML output)\n"
            "# Generated by tools/export_openai.py\n"
            "tools: " + json.dumps(tools, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build OpenAI tools array from TOS skill YAMLs.")
    ap.add_argument("--check", action="store_true",
                    help="validate only; do not write output files")
    ap.add_argument("--skill", metavar="NAME",
                    help="print a single skill's tool definition and exit")
    ap.add_argument("--subset", metavar="NAMES",
                    help="comma-separated skill names to include in export")
    ap.add_argument("--out-yaml", metavar="PATH", default=str(OUT_YAML),
                    help=f"output YAML path (default: {OUT_YAML})")
    ap.add_argument("--out-json", metavar="PATH", default=str(OUT_JSON),
                    help=f"output JSON path (default: {OUT_JSON})")
    a = ap.parse_args(argv)

    if not SKILLS_DIR.exists():
        print(f"ERROR: skills directory not found: {SKILLS_DIR}", file=sys.stderr)
        return 2

    skill_files = sorted(SKILLS_DIR.glob("*.yaml"))
    if not skill_files:
        print(f"No .yaml files found in {SKILLS_DIR}", file=sys.stderr)
        return 2

    subset = {s.strip() for s in a.subset.split(",")} if a.subset else None

    if a.skill:
        # Print single skill
        matches = [f for f in skill_files if f.stem == a.skill]
        if not matches:
            print(f"Skill '{a.skill}' not found in {SKILLS_DIR}", file=sys.stderr)
            return 1
        tool = load_skill(matches[0])
        if tool:
            print(json.dumps(tool, indent=2, ensure_ascii=False))
        return 0 if tool else 1

    tools: list[dict] = []
    errors = 0
    warnings = 0

    for f in skill_files:
        skill_name = f.stem
        if subset and skill_name not in subset:
            continue
        tool = load_skill(f)
        if tool is None:
            errors += 1
            continue
        issues = validate_tool(tool, f)
        fn_name = tool.get("function", {}).get("name", f.stem)
        if issues:
            for issue in issues:
                print(f"  WARN {skill_name}: {issue}", file=sys.stderr)
                warnings += 1
        else:
            print(f"  OK   {skill_name} → {fn_name}")
        tools.append(tool)

    print(f"\n{len(tools)} tool(s) loaded, {warnings} warning(s), {errors} error(s).")

    if not a.check:
        out_yaml = Path(a.out_yaml)
        out_json = Path(a.out_json)
        out_yaml.parent.mkdir(parents=True, exist_ok=True)
        _write_yaml(tools, out_yaml)
        out_json.write_text(json.dumps(tools, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Written: {out_yaml}")
        print(f"Written: {out_json}")
        print(f"\nUsage (Python openai SDK):")
        print(f"  import json")
        print(f"  tools = json.load(open('{out_json}'))")
        print(f"  client.chat.completions.create(model='gpt-4o', tools=tools, messages=[...])")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
