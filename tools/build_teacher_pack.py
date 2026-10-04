#!/usr/bin/env python3
"""Build the per-vendor teacher install packs into dist/teacher-packs/ (gitignored).

WHY THIS EXISTS (R5-D): the repo is the workshop, not the product. A teacher installs ONE
downloaded folder per platform; the canonical nested skills/ tree stays as-is and the flat,
vendor-shaped layouts exist only in build output. Contracts baked in here were verified against
vendor source/docs on 2026-09-25 (shared/platforms/platform-matrix.json carries the citations):

  chatgpt-plugin/  Agent-Plugins portable layout. openai/codex expands ${PLUGIN_ROOT} in mcp.json
                   ARGS (never ${CLAUDE_PLUGIN_ROOT}); the command must be a bare token; skills
                   live flat at skills/<name>/SKILL.md. "Desktop only"; Work mode or Codex.
  antigravity/     Skills flat + an installer that merges ~/.gemini/config/mcp_config.json with
                   ABSOLUTE paths (Google documents the global file; per-plugin config on the 2.0
                   desktop app is not documented, so we don't rely on it).
  gem-pack/        Reduced mode for browser Gemini/ChatGPT: <= 10 files (the Gem source cap).

Every pack ships the same self-contained server tree that tools/build_mcpb.py stages (its
SERVER_FILES/DATA_TREES/INDEX_FILES are imported, not duplicated).

Usage:
  python3 tools/build_teacher_pack.py               # build all packs
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
GEM_MAX_FILES = 10          # Classroom Gems: "supports up to 10 source documents"


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


def _copy_flat_skills(dest: Path) -> int:
    n = 0
    for d in _skill_dirs():
        t = dest / "skills" / d.name
        t.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(d / "SKILL.md", t / "SKILL.md")
        if (d / "references").is_dir():
            shutil.copytree(d / "references", t / "references", dirs_exist_ok=True)
        n += 1
    return n


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
    _copy_server_tree(out)
    (out / "INSTALL.md").write_text(f"""# Install TOS in the ChatGPT desktop app (best-effort build — UNTESTED-live)

Matrix row: chatgpt.desktop_workcodex_personal (shared/platforms/platform-matrix.json).
Works in **Work mode** (paid plans) and **Codex** (every plan). Never in ChatGPT web/mobile.

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
    _copy_flat_skills(out)
    _copy_server_tree(out)
    (out / "install_antigravity.py").write_text('''#!/usr/bin/env python3
"""Wire this TOS folder into Google Antigravity (personal Google account, 18+).

Copies the 62 skills to ~/.gemini/config/skills/ and merges the tos-tools stdio server into
~/.gemini/config/mcp_config.json with ABSOLUTE paths (the file Google documents for 2.0/IDE/CLI).
Run:  python3 install_antigravity.py   (Windows: py -3 install_antigravity.py)"""
import json, pathlib, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
CFG = pathlib.Path.home() / ".gemini" / "config"

def main() -> int:
    if sys.version_info < (3, 10):
        print("STOP: Python 3.10+ required."); return 1
    sk = CFG / "skills"; sk.mkdir(parents=True, exist_ok=True)
    n = 0
    for d in sorted((HERE / "skills").iterdir()):
        if (d / "SKILL.md").exists():
            shutil.copytree(d, sk / d.name, dirs_exist_ok=True); n += 1
    cfg_path = CFG / "mcp_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    cfg.setdefault("mcpServers", {})["tos-tools"] = {
        "command": sys.executable,
        "args": [str(HERE / "tools" / "mcp_server.py")]}
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\\n", encoding="utf-8")
    print(f"installed {n} skills -> {sk}\\nserver wired in {cfg_path}\\n"
          "Restart Antigravity, then Settings > Customizations > Installed MCP Servers > Refresh.\\n"
          "PRIVACY: check Settings > Account > Telemetry before any classroom use — Google may\\n"
          "review interactions and use them to improve models unless it is off.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
''', encoding="utf-8")
    (out / "INSTALL.md").write_text("""# Install TOS in Google Antigravity (best-effort build — UNTESTED-live)

Matrix row: gemini.antigravity_personal. Personal Google account, 18+ only — school accounts
are not supported by Antigravity. Free tier: weekly-refreshed quota.

1. Put this folder somewhere permanent (it is referenced by absolute path).
2. Run `python3 install_antigravity.py` (Windows: `py -3 install_antigravity.py`).
3. Restart Antigravity; test: *"Use the tos-tools verify_standard_codes tool to check
   MA.3.NSO.1.1 and MA.3.NSO.9.99."*
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
        ck("antigravity: skills flat + installer + server tree",
           len(list(ag.glob("skills/*/SKILL.md"))) == 62
           and (ag / "install_antigravity.py").exists()
           and (ag / "tools" / "mcp_server.py").exists())
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
        except ModuleNotFoundError:
            print("SKIP jsonschema not installed here — CI's SDK venv runs this validation")
        except Exception as e:
            ck(f"schema validation ({e.__class__.__name__}: {e})", False)
    print(f"build_teacher_pack self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    build_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
