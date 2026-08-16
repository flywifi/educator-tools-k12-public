#!/usr/bin/env python3
"""mac-lint — static cross-platform-safety checks for first-party Python (macOS-focused).

Two AST checks that codify the macOS defects fixed in the cross-platform pass, so they can't silently
regress (a Mac user is the one who pays for a regression, and CI runs on Linux where these pass):

  1. bare-interpreter subprocess — a child process spawned by the *name* "python3"/"python" instead
     of `sys.executable`. On a macOS venv/pyenv the bare name can resolve to a DIFFERENT interpreter
     (often the Xcode CLT stub `/usr/bin/python3`, which lacks the venv's deps) → a split-brain
     failure mid-workflow; under a no-shell-PATH GUI/MCP launch it's simply "not found".
  2. encoding-less text open — `open(...)` in text mode, or `.read_text()/.write_text()` with no
     `encoding=`. The default is `locale.getpreferredencoding()`, so under a non-UTF-8 locale
     (LC_ALL=C, some cron/SSH/login setups) a non-ASCII byte (a curly quote in a standard, an accented
     name) raises Unicode(De|En)codeError or writes mojibake.

Escape hatch: put `# mac-audit: ignore` on the offending line for an intentional case.

CLI:
  python3 tools/mac_audit.py            # report; exit 1 on findings
  python3 tools/mac_audit.py --json
Also importable: `scan()` returns the findings list (used by tools/sync_check.py).
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRST_PARTY = ("tools", "shared", "skills")
SKIP_PARTS = {".harvest-venv", "node_modules", "__pycache__", "skill-template"}
_SPAWN_FUNCS = {"run", "Popen", "call", "check_call", "check_output", "_run", "_run_json"}
_BARE_INTERPRETERS = {"python3", "python"}
_BINARY_MODES = {"rb", "wb", "ab", "xb", "br", "bw", "ba", "rb+", "wb+", "ab+", "r+b", "w+b", "a+b"}


def _iter_py():
    for base in FIRST_PARTY:
        for p in (ROOT / base).rglob("*.py"):
            if not SKIP_PARTS.intersection(p.relative_to(ROOT).parts):
                yield p


def _ignored(lines: list[str], node: ast.AST) -> bool:
    # The pragma counts on ANY line of the (possibly multi-line) call — end-of-call placement is the
    # natural spot and previously silently failed to suppress.
    start = getattr(node, "lineno", 0)
    if not start:
        return False
    end = getattr(node, "end_lineno", start) or start
    return any("# mac-audit: ignore" in lines[i - 1] for i in range(start, min(end, len(lines)) + 1))


def _func_name(call: ast.Call) -> str:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


def _check_file(p: Path) -> list[dict]:
    rel = p.relative_to(ROOT).as_posix()
    try:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception as e:
        # A file that cannot be parsed cannot run either — and its findings are invisible, so a
        # note plus a green exit is the worst of both. This printed a note and returned clean until
        # a real SyntaxError slipped past it during this very round; same disarm pattern as the
        # nine sync_check guards, one level down. It is now a finding.
        return [{"file": rel, "line": getattr(e, "lineno", 1) or 1, "check": "unparseable",
                 "issue": f"{e.__class__.__name__}: {e} — this file cannot run, and mac-lint "
                          f"cannot inspect it; fix the syntax"}]
    lines = src.splitlines()
    # Names bound anywhere in this file to a literal argv starting with a bare interpreter — a spawn
    # via such a variable is the same defect one hop away (a plain literal-only check missed it).
    bare_vars: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.Tuple)) and n.value.elts:
            head = n.value.elts[0]
            if (isinstance(head, ast.Constant) and isinstance(head.value, str)
                    and head.value in _BARE_INTERPRETERS):
                bare_vars.update(t.id for t in n.targets if isinstance(t, ast.Name))
    out: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _func_name(node)
        # 1) bare-interpreter subprocess (literal argv, or a file-local variable holding one)
        if name in _SPAWN_FUNCS and node.args:
            first = node.args[0]
            if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
                head = first.elts[0]
                if (isinstance(head, ast.Constant) and isinstance(head.value, str)
                        and head.value in _BARE_INTERPRETERS and not _ignored(lines, node)):
                    out.append({"file": rel, "line": node.lineno, "check": "bare-interpreter",
                                "issue": f"subprocess spawned by bare '{head.value}' — use sys.executable"})
            elif (isinstance(first, ast.Name) and first.id in bare_vars
                    and not _ignored(lines, node)):
                out.append({"file": rel, "line": node.lineno, "check": "bare-interpreter",
                            "issue": f"subprocess spawned via variable '{first.id}' holding a bare-"
                                     f"interpreter argv — use sys.executable"})
        # 2) encoding-less text open / read_text / write_text. `io.open` is the same function as
        # builtin open — treat it identically. (Path.open() receivers are not statically typeable —
        # documented limitation, kept out to preserve zero false positives on a hard gate.)
        is_io_open = (name == "open" and isinstance(node.func, ast.Attribute)
                      and isinstance(node.func.value, ast.Name) and node.func.value.id == "io")
        if (name == "open" and isinstance(node.func, ast.Name)) or is_io_open:
            mode = _literal_mode(node)
            has_enc = _has_kw(node, "encoding")
            if mode not in _BINARY_MODES and mode is not None and not has_enc and not _ignored(lines, node):
                out.append({"file": rel, "line": node.lineno, "check": "encoding",
                            "issue": "open() in text mode without encoding= (add encoding='utf-8')"})
        elif name in ("read_text", "write_text") and isinstance(node.func, ast.Attribute):
            if not _has_kw(node, "encoding") and not _ignored(lines, node):
                out.append({"file": rel, "line": node.lineno, "check": "encoding",
                            "issue": f".{name}() without encoding= (add encoding='utf-8')"})
    return out


def _has_kw(call: ast.Call, name: str) -> bool:
    return any(k.arg == name for k in call.keywords)


def _literal_mode(call: ast.Call):
    """Return the mode string for an open() call: '' (default text) if omitted, the literal if a
    positional/kw string, or None if the mode is a non-literal expression (then we can't judge — skip)."""
    if len(call.args) >= 2:
        m = call.args[1]
        return m.value if isinstance(m, ast.Constant) and isinstance(m.value, str) else None
    for k in call.keywords:
        if k.arg == "mode":
            return k.value.value if isinstance(k.value, ast.Constant) and isinstance(k.value, str) else None
    return ""  # no mode → text read


# --- check 3: JSON launchers ------------------------------------------------------------------
# The same bare-interpreter defect the AST check has caught in Python since the cross-platform
# pass shipped unnoticed THREE TIMES in JSON, because JSON is not Python and nothing looked at it:
# .mcp.json, .claude-plugin/plugin.json and the .mcpb manifest all launched the stdio server with
# command "python3" — absent on Windows (python.org ships python.exe/py.exe, never python3.exe)
# and absent from a macOS GUI app's PATH (the repo's own OPEN finding E2). A launcher command must
# therefore be an absolute path, an ${...} expansion the client resolves, or carry a win32
# platform override.
JSON_LAUNCHERS = (".mcp.json", ".claude-plugin/plugin.json")

# The one launcher that cannot be fixed from this repo, exempted BY NAME and only while the gap
# stays documented. The plugin manifest schema has no ${VAR:-default} form and no per-OS command;
# an unset ${VAR} would be passed through as literal text, which fails worse than "python3". So
# Door 1 on a Windows box whose Python is python.org's does not start, and the honest response is
# a documented workaround, not a silent pass. The exemption is conditional: if the workaround text
# disappears from the doc, this reverts to a finding.
LAUNCHER_GAP_EXEMPT = {
    (".claude-plugin/plugin.json", "tos-tools"):
        ("implementation/mcp/README.md", "claude mcp add --scope user"),
}


def _launcher_ok(cfg: dict) -> str:
    cmd = cfg.get("command")
    if not isinstance(cmd, str) or not cmd:
        return ""                                   # nothing to judge
    if cmd.startswith("${") or cmd.startswith("/") or (len(cmd) > 2 and cmd[1] == ":"):
        return ""                                   # expansion or absolute path
    if (cfg.get("platform_overrides") or {}).get("win32", {}).get("command"):
        return ""                                   # per-OS command declared
    if cmd in _BARE_INTERPRETERS:
        return (f"launcher command {cmd!r} is a bare interpreter name — absent on Windows "
                f"(python.org ships python.exe/py.exe) and outside a macOS GUI app's PATH; use "
                f"an ${{VAR}} expansion, an absolute path, or a win32 platform override")
    return ""


def _check_json_launchers() -> list[dict]:
    out: list[dict] = []
    for rel in JSON_LAUNCHERS:
        p = ROOT / rel
        if not p.exists():
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        for name, cfg in (doc.get("mcpServers") or {}).items():
            issue = _launcher_ok(cfg if isinstance(cfg, dict) else {})
            if not issue:
                continue
            exempt = LAUNCHER_GAP_EXEMPT.get((rel, name))
            if exempt:
                doc_rel, marker = exempt
                doc_path = ROOT / doc_rel
                if doc_path.exists() and marker in doc_path.read_text(encoding="utf-8"):
                    continue                        # platform gap, documented with a workaround
                out.append({"file": rel, "line": 1, "check": "json-launcher",
                            "issue": f"mcpServers.{name}: {issue} — this launcher is exempted "
                                     f"ONLY while {doc_rel} documents the workaround "
                                     f"({marker!r}); that text is now missing"})
                continue
            out.append({"file": rel, "line": 1, "check": "json-launcher",
                        "issue": f"mcpServers.{name}: {issue}"})
    try:                                            # the .mcpb manifest is generated, not stored
        sys.path.insert(0, str(ROOT / "tools"))
        import build_mcpb
        cfg = (build_mcpb._manifest("0.0.0").get("server") or {}).get("mcp_config") or {}
        issue = _launcher_ok(cfg)
        if issue:
            out.append({"file": "tools/build_mcpb.py", "line": 1, "check": "json-launcher",
                        "issue": f"the generated .mcpb manifest: {issue}"})
    except Exception as exc:                        # a broken generator is itself a finding
        out.append({"file": "tools/build_mcpb.py", "line": 1, "check": "json-launcher",
                    "issue": f"could not render the .mcpb manifest to check it: "
                             f"{exc.__class__.__name__}: {exc}"})
    return out


def scan() -> list[dict]:
    findings: list[dict] = []
    for p in sorted(_iter_py()):
        findings.extend(_check_file(p))
    findings.extend(_check_json_launchers())
    return findings


def main(argv: list[str]) -> int:
    findings = scan()
    if "--json" in argv:
        print(json.dumps(findings, indent=2))
    else:
        print("mac-lint — cross-platform safety (macOS)\n")
        if not findings:
            print("OK — no bare-interpreter spawns, no encoding-less text opens in first-party code.")
        else:
            for f in findings:
                print(f"  x {f['file']}:{f['line']} [{f['check']}] {f['issue']}")
            print(f"\n{len(findings)} finding(s). Fix, or add '# mac-audit: ignore' for an intentional case.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
