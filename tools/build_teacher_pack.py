#!/usr/bin/env python3
"""Build the per-vendor teacher install packs into dist/teacher-packs/ (gitignored).

WHY THIS EXISTS (R5-D): the repo is the workshop, not the product. A teacher installs ONE
downloaded folder per platform; the canonical nested skills/ tree stays as-is and the flat,
vendor-shaped layouts exist only in build output. Contracts baked in here were verified against
vendor source/docs on 2026-09-25 (shared/platforms/platform-matrix.json carries the citations):

  chatgpt-plugin/  Agent-Plugins portable layout. openai/codex expands ${PLUGIN_ROOT} in mcp.json
                   ARGS (never ${CLAUDE_PLUGIN_ROOT}); the command must be a bare token; skills
                   live flat at skills/<name>/SKILL.md. "Desktop only"; Work mode or Codex.
  antigravity/     A native Antigravity plugin (plugin.json, flat skills/, mcp_config.json with
                   ${PLUGIN_ROOT} in args, and a model_decision governance rule). Google documents
                   per-plugin MCP config and ${PLUGIN_ROOT} since the plugin system shipped; the old
                   installer script that edited ~/.gemini/config/mcp_config.json is retired.
  gem-pack/        Reduced mode for browser Gemini/ChatGPT: <= 10 files (the Gem source cap).

Every pack ships the same self-contained server tree that tools/build_mcpb.py stages (its
SERVER_FILES/DATA_TREES/INDEX_FILES are imported, not duplicated), each skill's WHOLE folder
(scripts, templates, examples — SKILL.md and references point at them) and the shared/ engines
the skill scripts import. Only git-tracked files are copied, so a maintainer's gitignored local
data (students.local.json, teacher.local.json) can never ride along into a published pack.

Usage:
  python3 tools/build_teacher_pack.py               # build all packs
  python3 tools/build_teacher_pack.py --zip         # also write <pack>.zip release assets
  python3 tools/build_teacher_pack.py --self-test   # offline probes incl. a real stdio handshake
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_mcpb  # noqa: E402  (SERVER_FILES / DATA_TREES / INDEX_FILES — single source)

DIST = ROOT / "dist" / "teacher-packs"
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
AG_PLUGIN_SCHEMA = "https://antigravity.google/schemas/v1/plugin.json"
GEM_MAX_FILES = 10          # Classroom Gems: "supports up to 10 source documents"
SKILL_SKIP = ("evals", "MAINTAINER.md", "__pycache__")   # contributor-only, never shipped
LOCAL_DATA = ("*.local.*",)                               # gitignored real data, never shipped


def _version() -> str:
    return json.loads((ROOT / "versions.json").read_text(encoding="utf-8"))["ecosystem"]


def _skill_dirs() -> list[Path]:
    return sorted((p.parent for p in ROOT.glob("skills/*/*/SKILL.md")), key=lambda p: p.name)


def _copy_server_tree(dest: Path) -> None:
    for rel in [*build_mcpb.SERVER_FILES, *build_mcpb.INDEX_FILES, "VERSION"]:
        src = ROOT / rel
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest / rel)
    for rel in build_mcpb.DATA_TREES:
        shutil.copytree(ROOT / rel, dest / rel, dirs_exist_ok=True)


def _tracked(prefix: str) -> set[str] | None:
    """Repo-relative paths git tracks under prefix, or None outside a git checkout (an export or
    a tarball holds only tracked files anyway)."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", prefix],
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {p for p in out.decode("utf-8").split("\0") if p} or None


def _copy_tree(src_rel: str, dest: Path, skip_names=(), skip_rel=()) -> None:
    """Copy ROOT/src_rel to dest, tracked files only, minus contributor files and local data."""
    tracked = _tracked(src_rel)
    src = ROOT / src_rel
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        parts = p.relative_to(src).parts
        if any(n in parts for n in skip_names) or any(rel.startswith(s) for s in skip_rel):
            continue
        if any(p.match(g) for g in LOCAL_DATA) or (tracked is not None and rel not in tracked):
            continue
        t = dest / p.relative_to(src)
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, t)


def _copy_flat_skills(dest: Path) -> int:
    """Each skill's whole folder, flattened to skills/<name>/. The first version copied only
    SKILL.md + references/, and 41 files those two point at (scoring scripts, templates,
    examples) were missing from every pack."""
    n = 0
    for d in _skill_dirs():
        _copy_tree(d.relative_to(ROOT).as_posix(), dest / "skills" / d.name, skip_names=SKILL_SKIP)
        n += 1
    return n


def _copy_shared_code(dest: Path) -> None:
    """The shared/ engines the skill scripts import (connectors, students, docintel, routing,
    records, office, ...). shared/standards is left out: its corpora are build inputs (108 MB),
    and the server's data tree is copied by _copy_server_tree."""
    _copy_tree("shared", dest / "shared", skip_names=("__pycache__",),
               skip_rel=("shared/standards/",))


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_chatgpt(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "plugin.json", {
        "$schema": PLUGIN_SCHEMA,
        "name": "teacher-operating-system",
        "version": _version(),
        "description": "Teacher Operating System: 62 governed K-12 teacher skills plus the "
                       "tos-tools local server (9 read-only verified-standards tools; offline; "
                       "human_review_required on every artifact).",
    })
    # ${PLUGIN_ROOT} in ARGS is the expansion openai/codex actually performs; the command must be
    # a bare token (python3). ${CLAUDE_PLUGIN_ROOT} would be passed through literally and fail.
    _write_json(out / "mcp.json", {
        "$schema": MCP_SCHEMA,
        "mcpServers": {"tos-tools": {"type": "stdio", "command": "python3",
                                     "args": ["${PLUGIN_ROOT}/tools/mcp_server.py"]}},
    })
    _copy_flat_skills(out)
    _copy_shared_code(out)
    _copy_server_tree(out)
    (out / "INSTALL.md").write_text(f"""# Install TOS in the ChatGPT desktop app (best-effort build — UNTESTED-live)

Matrix row: chatgpt.desktop_workcodex_personal (shared/platforms/platform-matrix.json).
The tools server is local, so this plugin is **Desktop only** (Work mode or Codex). Its skills
also work in ChatGPT web/mobile once installed, where your plan allows plugins.

**One step (recommended):** in Codex CLI run
`codex plugin marketplace add flywifi/educator-tools-k12-public`, or add that repository as a
marketplace in the ChatGPT desktop app, then install **Teacher Operating System**.

**From this download instead:**

1. Copy this whole folder to `~/.codex/plugins/teacher-operating-system`.
2. Create or edit `~/.agents/plugins/marketplace.json`:

```json
{{"name": "tos-local", "plugins": [{{"name": "teacher-operating-system",
  "source": {{"path": "~/.codex/plugins/teacher-operating-system"}}}}]}}
```

3. Fully restart the ChatGPT desktop app, open the Plugins Directory, choose **tos-local**,
   install, then test: *"Use the tos-tools verify_standard_codes tool to check MA.3.NSO.1.1 and
   MA.3.NSO.9.99."* (PASS = first resolves, second flagged as not a real code.)

Needs Python 3.10+ on this computer. **Windows:** `python3` is usually not a command — if the
tools don't start, add the server by hand instead: Settings -> **MCP servers** -> Add server ->
STDIO -> command `python` (or full path to python.exe), argument = the full path to
`tools/mcp_server.py` inside this folder.

Privacy: personal ChatGPT plans may train on conversations by default — Settings -> Data
controls -> turn off "Improve the model for everyone".
""", encoding="utf-8")


def build_antigravity(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "plugin.json", {
        "$schema": AG_PLUGIN_SCHEMA,
        "name": "teacher-operating-system",
        "displayName": "Teacher Operating System",
        "version": _version(),
        "description": "62 governed K-12 teacher skills plus the tos-tools local server "
                       "(verified Florida standards lookups; fabricated codes flagged). Drafts "
                       "for teacher review — human_review_required on every artifact.",
        "license": "MIT",
        "repository": "https://github.com/flywifi/educator-tools-k12-public",
        "keywords": ["education", "k-12", "teaching", "lesson-planning", "standards"],
        "suggestedPrompts": [
            "Write a 3rd grade fractions lesson plan aligned to a verified Florida standard",
            "Is MA.3.NSO.9.99 a real Florida standard? Check it with the TOS tools",
            "Turn this lesson into a differentiated version for English learners"],
    })
    # ${PLUGIN_ROOT} is expanded in args/cwd/env (never in command), as Google documents.
    _write_json(out / "mcp_config.json", {
        "mcpServers": {"tos-tools": {"command": "python3",
                                     "args": ["${PLUGIN_ROOT}/tools/mcp_server.py"]}},
    })
    rule = (ROOT / "implementation/gpt/api/system-prompt.md").read_text(encoding="utf-8")
    (out / "rules").mkdir(exist_ok=True)
    (out / "rules" / "tos-governance.md").write_text(
        "---\ntrigger: model_decision\n"
        'description: "Apply whenever doing K-12 teacher work with the Teacher Operating System '
        '(lesson plans, assessments, IEP/MTSS supports, family communication, standards)."\n'
        "---\n\n" + rule, encoding="utf-8")
    _copy_flat_skills(out)
    _copy_shared_code(out)
    _copy_server_tree(out)
    (out / "INSTALL.md").write_text("""# Install TOS in Google Antigravity (best-effort build — UNTESTED-live)

Matrix row: gemini.antigravity_personal. Personal Google account, 18+ only. Google Workspace
(school) accounts don't include Antigravity plans.

1. Unzip this folder somewhere permanent.
2. **Antigravity App:** type `/plugin`, open **Installed**, choose *install from a local
   directory*, and pick this folder. **Antigravity CLI:** `agy plugin install <this folder>`.
3. Test: *"Use the tos-tools verify_standard_codes tool to check MA.3.NSO.1.1 and
   MA.3.NSO.9.99."* (PASS = the first resolves, the second is flagged as not a real code.)

Needs Python 3.10+ (`python3` on PATH). Privacy: check Settings > Account > Telemetry before any
classroom use — Google may review interactions unless it is off.
""", encoding="utf-8")


def build_gem(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    one = ROOT / "implementation/gpt/web/reference-pack/tos-reference-pack-onefile.json"
    shutil.copyfile(one, out / "tos-reference-pack-onefile.json")
    prompt = (ROOT / "implementation/gpt/api/system-prompt.md").read_text(encoding="utf-8")
    (out / "gem-instructions.md").write_text(
        "<!-- Paste this file's contents into the Gem's Instructions box; attach the other two\n"
        "     files as the Gem's knowledge. REDUCED MODE: no tools run here — every standards\n"
        "     code must be checked against tos-reference-pack-onefile.json, and a code that is\n"
        "     not in that file is treated as unverified, never asserted. -->\n\n" + prompt,
        encoding="utf-8")
    (out / "README.md").write_text("""# TOS Gem / Project pack (reduced mode — no tools)

For browser Gemini (a Gem, or a Classroom-assigned Gem: 10-source cap) and browser ChatGPT
(a Project: 25 files on Plus). Attach `tos-reference-pack-onefile.json` as knowledge and paste
`gem-instructions.md` into the instructions box. Verified lookups and fabrication BLOCKING need
full mode (a desktop app + the local server) — this pack only instructs the model to check
codes against the attached corpus. Personal-account privacy: Gemini "Keep Activity" is on by
default (human review + training); ChatGPT personal plans may train by default.
""", encoding="utf-8")
    files = list(out.iterdir())
    if len(files) > GEM_MAX_FILES:
        raise SystemExit(f"gem-pack has {len(files)} files > Gem cap {GEM_MAX_FILES}")


def build_all(dist: Path = DIST) -> None:
    # A fresh checkout (CI, a new clone) has no offline.db — it is gitignored and built from the
    # committed sources. Same self-heal as mcp_server._ensure_index: build once, never assume.
    # W3 (R5.1): the first version copied it blind and died on the runner with FileNotFoundError.
    import offline_index
    if not (ROOT / "canonical-sources" / "index" / "offline.db").exists():
        offline_index.build()
    if dist.exists():
        shutil.rmtree(dist)
    build_chatgpt(dist / "chatgpt-plugin")
    build_antigravity(dist / "antigravity")
    build_gem(dist / "gem-pack")
    print(f"built 3 packs under {dist} (v{_version()})")


def zip_packs(dist: Path = DIST) -> list[Path]:
    """<pack>.zip next to each pack folder — the release assets (folder at the zip root)."""
    out = []
    for name in ("chatgpt-plugin", "antigravity", "gem-pack"):
        z = shutil.make_archive(str(dist / f"tos-{name}"), "zip", root_dir=dist, base_dir=name)
        out.append(Path(z))
    return out


def self_test() -> int:
    import tempfile
    fails = 0
    def ck(name, ok):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1
    with tempfile.TemporaryDirectory(prefix="tp-") as td:
        dist = Path(td) / "packs"
        build_all(dist)
        cg = dist / "chatgpt-plugin"
        ck("chatgpt: 62 flat skills, ./-independent one-level layout",
           len(list(cg.glob("skills/*/SKILL.md"))) == 62)
        man = json.loads((cg / "mcp.json").read_text(encoding="utf-8"))
        srv = man["mcpServers"]["tos-tools"]
        ck("chatgpt: stdio + bare command + ${PLUGIN_ROOT} args (the expansion codex performs; "
           "${CLAUDE_PLUGIN_ROOT} is passed through literally and MUST NOT appear)",
           srv["type"] == "stdio" and srv["command"] == "python3"
           and srv["args"] == ["${PLUGIN_ROOT}/tools/mcp_server.py"]
           and "CLAUDE_PLUGIN_ROOT" not in json.dumps(man))
        # the packed tree must be a WORKING server: real initialize over real pipes
        frame = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                                       "clientInfo": {"name": "pack-probe", "version": "0"}}})
        r = subprocess.run([sys.executable, str(cg / "tools" / "mcp_server.py")],
                           input=frame + "\n", capture_output=True, text=True, timeout=120)
        line = (r.stdout.splitlines() or [""])[0]
        ok = False
        try:
            ok = json.loads(line)["result"]["protocolVersion"] == "2025-11-25"
        except Exception:
            pass
        ck("chatgpt: the PACKED server tree answers initialize (tree is self-contained)", ok)
        ag = dist / "antigravity"
        agm = json.loads((ag / "mcp_config.json").read_text(encoding="utf-8"))["mcpServers"]["tos-tools"]
        ck("antigravity: native plugin — plugin.json + 62 flat skills + server tree, no installer",
           (ag / "plugin.json").exists() and len(list(ag.glob("skills/*/SKILL.md"))) == 62
           and (ag / "tools" / "mcp_server.py").exists() and not (ag / "install_antigravity.py").exists())
        ck("antigravity: mcp_config bare command + ${PLUGIN_ROOT} in args (expanded there, never in command)",
           agm["command"] == "python3" and agm["args"] == ["${PLUGIN_ROOT}/tools/mcp_server.py"])
        rule = (ag / "rules" / "tos-governance.md").read_text(encoding="utf-8")
        ck("antigravity: governance rule is model_decision with a description (not always_on)",
           rule.startswith("---\ntrigger: model_decision\ndescription: "))
        r2 = subprocess.run([sys.executable, agm["args"][0].replace("${PLUGIN_ROOT}", str(ag))],
                            input=frame + "\n", capture_output=True, text=True, timeout=120)
        ok2 = False
        try:
            ok2 = json.loads((r2.stdout.splitlines() or [""])[0])["result"]["protocolVersion"] == "2025-11-25"
        except Exception:
            pass
        ck("antigravity: the server answers initialize at the ${PLUGIN_ROOT}-expanded path", ok2)
        import re as _re
        missing = []
        for pack in (cg, ag):
            for sk in pack.glob("skills/*/SKILL.md"):
                d = sk.parent
                for t in [sk, *d.glob("references/*.md")]:
                    for m in _re.finditer(r"(?<![\w/.-])((?:scripts|assets|examples)/[\w./-]+\.\w+)",
                                          t.read_text(encoding="utf-8")):
                        src = next(iter((ROOT / "skills").glob(f"*/{d.name}/{m.group(1)}")), None)
                        if src is not None and not (d / m.group(1)).exists():
                            missing.append(f"{pack.name}:{d.name}/{m.group(1)}")
        ck(f"both packs: every scripts/assets/examples file a SKILL.md or reference names is packed "
           f"({len(missing)} missing)", not missing)
        leaked = [p for p in dist.rglob("*") if p.is_file() and p.match("*.local.*")
                  and p.name != "offline.db"]
        ck("no gitignored local data (*.local.*) inside any pack", not leaked)
        bad = []
        probes = {"score.py": ['{"integrity":5,"safety":5,"governance":4,"accuracy":4,"alignment":4,'
                               '"educational_quality":4,"accessibility":4,"professional_quality":4,'
                               '"user_intent":5}']}       # score.py takes scores, not --help
        for sc in sorted(cg.glob("skills/*/scripts/*.py")):
            rr = subprocess.run([sys.executable, str(sc), *probes.get(sc.name, ["--help"])],
                                capture_output=True, text=True, timeout=120, cwd=td)
            if rr.returncode != 0:
                bad.append(f"{sc.parent.parent.name}/{sc.name}: {(rr.stderr or rr.stdout).strip()[-160:]}")
        ck(f"chatgpt: every packed skill script runs from the pack (exit 0){': ' + '; '.join(bad) if bad else ''}",
           not bad)
        gem = dist / "gem-pack"
        ck(f"gem: <= {GEM_MAX_FILES} files (Classroom Gem source cap)",
           0 < len(list(gem.iterdir())) <= GEM_MAX_FILES)
        # idempotency: a second build renders byte-identical text artifacts
        before = {p.relative_to(dist): p.read_bytes()
                  for p in dist.rglob("*") if p.suffix in (".json", ".md", ".py")}
        build_all(dist)
        after = {p.relative_to(dist): p.read_bytes()
                 for p in dist.rglob("*") if p.suffix in (".json", ".md", ".py")}
        ck("idempotent: second build is a byte no-op for every text artifact", before == after)
        try:
            import jsonschema
            for name, url in (("plugin.json", "plugin.schema.json"), ("mcp.json", "mcp.schema.json")):
                sp = ROOT / "shared" / "platforms" / url
                jsonschema.validate(json.loads((cg / name).read_text(encoding="utf-8")),
                                    json.loads(sp.read_text(encoding="utf-8")))
            ck("chatgpt: plugin.json + mcp.json validate against the vendored "
               "agent-plugins 1.0.0 schemas", True)
            jsonschema.validate(json.loads((ag / "plugin.json").read_text(encoding="utf-8")),
                                json.loads((ROOT / "shared/platforms/antigravity-plugin.schema.json")
                                           .read_text(encoding="utf-8")))
            ck("antigravity: plugin.json validates against the vendored Antigravity v1 schema", True)
        except ModuleNotFoundError:
            print("SKIP jsonschema not installed here — CI's SDK venv runs this validation")
        except Exception as e:
            ck(f"schema validation ({e.__class__.__name__}: {e})", False)
    print(f"build_teacher_pack self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--zip", action="store_true", help="also write tos-<pack>.zip release assets")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    build_all()
    if a.zip:
        for z in zip_packs():
            print(f"zipped {z.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
