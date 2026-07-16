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
        # a file that can't be parsed can't run either, but say so instead of silently skipping —
        # its findings are otherwise invisible.
        print(f"[note] mac-lint: skipped unparseable {rel} ({e.__class__.__name__})", file=sys.stderr)
        return []
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


def scan() -> list[dict]:
    findings: list[dict] = []
    for p in sorted(_iter_py()):
        findings.extend(_check_file(p))
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
