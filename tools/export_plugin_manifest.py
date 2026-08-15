#!/usr/bin/env python3
"""Generate the plugin/marketplace metadata from live repo facts — counts computed, never typed.

The `.claude-plugin/` manifests are what a claude.ai plugin install sees. Their descriptions were
hand-typed on 2026-06-23 and never touched again: the marketplace listing still said "15 governed
K-12 teacher skills" while 62 existed on disk — the same failure class the METRICS dashboard once
had (sat at 29 skills), fixed the same way: a generator plus a freshness gate, so the committed
artifact must equal a fresh render or CI goes red (tools/sync_check.py check 21).

What this tool OWNS (regenerates):
  .claude-plugin/plugin.json        -> `version` + `description` only
  .claude-plugin/marketplace.json   -> `metadata.version`, `plugins[0].version`,
                                       `plugins[0].description` only
  skills/README.md                  -> the marker-delimited skills catalog block only

Everything else in those files is IDENTITY, passed through untouched: plugin
name/autoUpdate/author/keywords/license, marketplace name/owner/metadata.description/
source/category. None of them encode counts, so none of them can drift; folding them into the
template would make this tool the sole editor of identity for no benefit.

Facts and their single sources of truth:
  version              versions.json `ecosystem` (this tool only COPIES it — tools/version.py
                       --bump/--release is the only writer, so the two tools never fight)
  skill counts         skills/**/SKILL.md on disk (the discovery idiom every tool uses)
  engine count         versions.json `engines` — the CURATED roster. shared/ top-level dirs are
                       NOT all engines (7 are reference/data dirs; 2 roster engines live outside
                       shared/), so nothing here may count or enumerate shared/ as "engines"
  verified standards   ledger/cpalms-run-manifest.json `totals.verified` (self-declared
                       authoritative; changes only on human-approved verification runs)

Prose edits happen in the *_DESC templates below, never in the JSON — a hand edit to the JSON is
reverted by the next regeneration and flagged by the gate either way.

Usage:
  python3 tools/export_plugin_manifest.py              # regenerate all three targets
  python3 tools/export_plugin_manifest.py --check      # freshness: exit 1 + issues if stale
  python3 tools/export_plugin_manifest.py --self-test  # offline fixture probes (CI)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PLUGIN_DESC = (
    "Teacher Operating System (TOS): a hub-and-spoke ecosystem of {skills_total} governed K-12 "
    "teacher skills ({core} core hub+governance, {educator} educator, {operations} operations, "
    "{atoms} atom sub-skills) over {engines_count} shared engines (roster: versions.json), with "
    "{verified_standards} Florida standards verified code-by-code against CPALMS. Skills under "
    "skills/ are auto-discovered, and the tos-tools MCP server (8 read-only verified-lookup/"
    "validator tools) starts with the plugin. Offline/stdlib; decision-support with "
    "human_review_required; "
    "placeholders only in the repo."
)

MARKETPLACE_DESC = (
    "The full TOS suite: {skills_total} governed K-12 teacher skills ({core} core "
    "hub+governance, {educator} educator, {operations} operations, {atoms} atom sub-skills) "
    "over {engines_count} shared engines; {verified_standards} FL standards verified "
    "code-by-code against CPALMS. Install to add lesson/assessment/presentation generation, "
    "curriculum mapping, special-ed/MTSS support, family communication, professional learning, "
    "school administration, standards currency, document intelligence, meeting classification, "
    "and skill-health/repair — plus the tos-tools MCP server: verified standards search, "
    "fabrication-blocking code verification, citation-mutation checks, and artifact validation "
    "as callable tools."
)

CATALOG_BEGIN = "<!-- BEGIN GENERATED: skills-catalog -->"
CATALOG_END = "<!-- END GENERATED: skills-catalog -->"


def _paths(root: Path) -> dict[str, Path]:
    return {"plugin": root / ".claude-plugin" / "plugin.json",
            "marketplace": root / ".claude-plugin" / "marketplace.json",
            "catalog": root / "skills" / "README.md",
            "versions": root / "versions.json",
            "manifest": root / "ledger" / "cpalms-run-manifest.json",
            "skills": root / "skills"}


def facts(root: Path | None = None) -> dict:
    """Live facts from their single sources of truth. Raises on a missing source — a generator
    that guesses a fact would re-introduce the typed-count failure it exists to kill."""
    p = _paths(root or ROOT)
    versions = json.loads(p["versions"].read_text(encoding="utf-8"))
    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))
    by_group: dict[str, int] = {}
    for sk in p["skills"].rglob("SKILL.md"):
        group = sk.parent.relative_to(p["skills"]).parts[0]
        by_group[group] = by_group.get(group, 0) + 1
    return {"version": versions["ecosystem"],
            "skills_total": sum(by_group.values()),
            "skills_by_group": by_group,
            "engines_count": len(versions.get("engines", {})),
            "verified_standards": manifest["totals"]["verified"]}


def _fill(template: str, f: dict) -> str:
    g = f["skills_by_group"]
    return template.format(skills_total=f["skills_total"], core=g.get("core", 0),
                           educator=g.get("educator", 0), operations=g.get("operations", 0),
                           atoms=g.get("atoms", 0), engines_count=f["engines_count"],
                           verified_standards=f"{f['verified_standards']:,}")


def render_plugin(f: dict, current: dict) -> dict:
    """Only `version` and `description` are generated; every other key passes through."""
    out = dict(current)
    out["version"] = f["version"]
    out["description"] = _fill(PLUGIN_DESC, f)
    return out


def render_marketplace(f: dict, current: dict) -> dict:
    out = json.loads(json.dumps(current))  # deep copy; nested dicts must not alias the input
    out.setdefault("metadata", {})["version"] = f["version"]
    plugins = out.get("plugins", [])
    for entry in plugins:  # every listed plugin gets the same treatment; one exists today
        entry["version"] = f["version"]
        entry["description"] = _fill(MARKETPLACE_DESC, f)
    return out


def _frontmatter(skill_md: Path) -> tuple[str, str]:
    """(name, first sentence of description) from a SKILL.md frontmatter block."""
    name, desc = skill_md.parent.name, ""
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip('"')
    m = re.match(r"(.+?\.)(?:\s|$)", desc)
    sentence = (m.group(1) if m else desc).replace("|", "\\|")
    return name, sentence


def render_skills_catalog(f: dict, root: Path | None = None) -> str:
    """The full catalog table (every skill on disk), for the marker-delimited README block."""
    p = _paths(root or ROOT)
    rows = []
    for sk in sorted(p["skills"].rglob("SKILL.md"),
                     key=lambda s: (s.parent.relative_to(p["skills"]).parts[0], s.parent.name)):
        group = sk.parent.relative_to(p["skills"]).parts[0]
        name, sentence = _frontmatter(sk)
        rows.append(f"| `{name}` | {group} | {sentence} |")
    g = f["skills_by_group"]
    head = (f"All **{f['skills_total']}** skills on disk — core {g.get('core', 0)} · educator "
            f"{g.get('educator', 0)} · operations {g.get('operations', 0)} · atoms "
            f"{g.get('atoms', 0)}. Generated by `tools/export_plugin_manifest.py`; do not "
            f"hand-edit between the markers (sync_check check 21 compares this block to a fresh "
            f"render).")
    return "\n".join([head, "", "| Skill | Group | What it does |", "|---|---|---|"] + rows)


def _catalog_bounds(text: str) -> tuple[int, int] | None:
    a, b = text.find(CATALOG_BEGIN), text.find(CATALOG_END)
    if a < 0 or b < 0 or b < a:
        return None
    return a + len(CATALOG_BEGIN), b


def check(root: Path | None = None) -> list[str]:
    """Freshness issues, [] when everything committed equals a fresh render. JSON compared at
    object level (indent/key-order immune); the catalog block as stripped text."""
    r = root or ROOT
    p = _paths(r)
    f = facts(r)
    issues = []
    for key, renderer in (("plugin", render_plugin), ("marketplace", render_marketplace)):
        committed = json.loads(p[key].read_text(encoding="utf-8"))
        if committed != renderer(f, committed):
            issues.append(f"  x .claude-plugin/{p[key].name} is stale vs live facts "
                          f"(skills/engines/CPALMS/version) — run: python3 "
                          f"tools/export_plugin_manifest.py && commit .claude-plugin/")
    readme = p["catalog"].read_text(encoding="utf-8")
    bounds = _catalog_bounds(readme)
    if bounds is None:
        issues.append("  x skills/README.md lacks the generated skills-catalog markers — run: "
                      "python3 tools/export_plugin_manifest.py && commit skills/README.md")
    elif readme[bounds[0]:bounds[1]].strip() != render_skills_catalog(f, r).strip():
        issues.append("  x skills/README.md skills-catalog block is stale vs the skills on disk "
                      "— run: python3 tools/export_plugin_manifest.py && commit "
                      "skills/README.md")
    return issues


def write(root: Path | None = None) -> dict:
    """Regenerate all three targets. Idempotent: a second run is a byte no-op."""
    r = root or ROOT
    p = _paths(r)
    f = facts(r)
    for key, renderer in (("plugin", render_plugin), ("marketplace", render_marketplace)):
        committed = json.loads(p[key].read_text(encoding="utf-8"))
        p[key].write_text(json.dumps(renderer(f, committed), indent=2) + "\n", encoding="utf-8")
    readme = p["catalog"].read_text(encoding="utf-8")
    bounds = _catalog_bounds(readme)
    if bounds is None:
        raise SystemExit("skills/README.md lacks the skills-catalog markers; add\n"
                         f"  {CATALOG_BEGIN}\n  {CATALOG_END}\nwhere the catalog belongs "
                         "(one-time setup), then re-run.")
    p["catalog"].write_text(readme[:bounds[0]] + "\n" + render_skills_catalog(f, r) + "\n"
                            + readme[bounds[1]:], encoding="utf-8")
    return f


# --------------------------------------------------------------------------------------- self-test
def self_test() -> int:
    """Fixture probes; the broken-twin rule applies — every check is shown able to fail."""
    import shutil
    import tempfile
    fails = 0

    def ck(name: str, ok: bool) -> None:
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    tmp = Path(tempfile.mkdtemp(prefix="epm-st-"))
    (tmp / ".claude-plugin").mkdir()
    (tmp / "ledger").mkdir()
    for grp, names in (("core", ["hub"]), ("atoms", ["one", "two"])):
        for n in names:
            d = tmp / "skills" / grp / n
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f'---\nname: {n}\ndescription: "Does {n} things. Ignore the rest."\n---\n',
                encoding="utf-8")
    (tmp / "versions.json").write_text(json.dumps(
        {"ecosystem": "9.9.9", "engines": {"a": "0.1.0", "b": "0.1.0"}}), encoding="utf-8")
    (tmp / "ledger" / "cpalms-run-manifest.json").write_text(
        json.dumps({"totals": {"verified": 1234}}), encoding="utf-8")
    (tmp / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "x", "version": "0.0.0", "autoUpdate": True, "description": "old",
         "keywords": ["k1"]}), encoding="utf-8")
    (tmp / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
        {"name": "m", "metadata": {"version": "0.0.0"},
         "plugins": [{"name": "x", "source": "./", "version": "0.0.0",
                      "description": "old", "category": "education"}]}), encoding="utf-8")
    (tmp / "skills" / "README.md").write_text(
        f"# cat\n{CATALOG_BEGIN}\n{CATALOG_END}\n", encoding="utf-8")

    f = facts(tmp)
    ck("facts: counts computed (3 skills: core 1 + atoms 2; 2 engines; 1234 verified; 9.9.9)",
       f == {"version": "9.9.9", "skills_total": 3,
             "skills_by_group": {"core": 1, "atoms": 2},
             "engines_count": 2, "verified_standards": 1234})

    ck("check: stale fixture starts dirty (all three targets flagged)", len(check(tmp)) == 3)
    write(tmp)
    ck("check: clean after write()", check(tmp) == [])

    before = {k: _paths(tmp)[k].read_bytes() for k in ("plugin", "marketplace", "catalog")}
    write(tmp)
    ck("write: idempotent (second run is a byte no-op)",
       all(_paths(tmp)[k].read_bytes() == before[k]
           for k in ("plugin", "marketplace", "catalog")))

    plug = json.loads(_paths(tmp)["plugin"].read_text(encoding="utf-8"))
    ck("pass-through: identity keys survive regeneration untouched",
       plug["name"] == "x" and plug["autoUpdate"] is True and plug["keywords"] == ["k1"])
    plug["keywords"] = ["MUTATED"]
    _paths(tmp)["plugin"].write_text(json.dumps(plug), encoding="utf-8")
    write(tmp)
    plug2 = json.loads(_paths(tmp)["plugin"].read_text(encoding="utf-8"))
    ck("pass-through: a hand edit to an identity key is NOT reverted by write()",
       plug2["keywords"] == ["MUTATED"])

    # Broken twins: each freshness check must be able to fail.
    plug2["description"] = "hand-typed lies"
    _paths(tmp)["plugin"].write_text(json.dumps(plug2), encoding="utf-8")
    ck("twin: a mutated description is caught", any("plugin.json" in i for i in check(tmp)))
    write(tmp)
    mk = json.loads(_paths(tmp)["marketplace"].read_text(encoding="utf-8"))
    mk["plugins"][0]["version"] = "0.0.1"
    _paths(tmp)["marketplace"].write_text(json.dumps(mk), encoding="utf-8")
    ck("twin: a mutated marketplace version is caught",
       any("marketplace.json" in i for i in check(tmp)))
    write(tmp)
    readme = _paths(tmp)["catalog"].read_text(encoding="utf-8")
    _paths(tmp)["catalog"].write_text(readme.replace("Does one things.", "Does NOTHING."),
                                      encoding="utf-8")
    ck("twin: a mutated catalog row is caught", any("catalog" in i for i in check(tmp)))
    _paths(tmp)["catalog"].write_text("# no markers\n", encoding="utf-8")
    ck("twin: missing markers are caught (never silently skipped)",
       any("markers" in i for i in check(tmp)))

    (tmp / "versions.json").write_text(json.dumps(
        {"ecosystem": "9.9.10", "engines": {"a": "0.1.0", "b": "0.1.0"}}), encoding="utf-8")
    _paths(tmp)["catalog"].write_text(f"# cat\n{CATALOG_BEGIN}\n{CATALOG_END}\n",
                                      encoding="utf-8")
    ck("twin: a registry version bump makes committed manifests stale until regenerated",
       any("plugin.json" in i for i in check(tmp)))
    try:
        facts(tmp / "nowhere")
        ck("facts: a missing source raises (never guesses)", False)
    except (OSError, SystemExit):
        ck("facts: a missing source raises (never guesses)", True)

    shutil.rmtree(tmp)
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="freshness check; exit 1 if stale")
    ap.add_argument("--self-test", action="store_true", help="offline fixture probes")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.check:
        issues = check()
        for i in issues:
            print(i)
        if not issues:
            print("plugin metadata fresh — manifests + catalog equal a fresh render")
        return 1 if issues else 0
    f = write()
    print(f"regenerated .claude-plugin/plugin.json + marketplace.json + skills/README.md "
          f"catalog — {f['skills_total']} skills, {f['engines_count']} engines, "
          f"{f['verified_standards']:,} verified standards, v{f['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
