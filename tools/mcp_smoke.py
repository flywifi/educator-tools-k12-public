#!/usr/bin/env python3
"""One command that answers "do the TOS tools actually work on THIS machine?" — and prints an
answer you can paste back.

Why this exists: three claims in docs/MACOS.md (M1-M5) are marked UNTESTED because no Mac or
Windows box exists in the build environment, and "please try it and tell me what happened" is a
request people cannot act on precisely. This turns each of them into one command and one paste.

Stdlib only, no network, reads nothing outside the repo, writes nothing anywhere — a teacher can
run it on a school laptop. `--hosted` additionally exercises the remote leg over loopback, which
needs the optional `mcp` SDK and is skipped honestly when it is absent.

  python3 tools/mcp_smoke.py            # launchers + index + a live stdio round trip
  python3 tools/mcp_smoke.py --hosted   # the above, plus the hosted leg on 127.0.0.1
Exit: 0 all green · 1 something failed (the FAIL lines say what)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

_RESULTS: list[tuple] = []


def ck(ok: bool, name: str, detail: str = "") -> bool:
    _RESULTS.append((ok, name, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"\n       {detail}" if detail else ""))
    return ok


def check_interpreter() -> None:
    v = sys.version_info
    ck(v >= (3, 10), f"python {v.major}.{v.minor}.{v.micro} is >= 3.10 (the server's floor)",
       f"running: {sys.executable}")


def check_launchers() -> None:
    """What each shipped launcher would ACTUALLY spawn on this OS — the H-4 question."""
    import build_mcpb
    plat = "win32" if os.name == "nt" else ("darwin" if sys.platform == "darwin" else "linux")
    print(f"\n-- launchers, resolved for platform={plat} --")

    cfg = (build_mcpb._manifest("0.0.0")["server"]["mcp_config"])
    cmd = build_mcpb.launch_command(cfg, plat)
    ck(bool(shutil.which(cmd)), f".mcpb (Claude Desktop) would launch {cmd!r} — found on PATH",
       "" if shutil.which(cmd) else f"{cmd!r} is not on this PATH; the extension would not start")

    mcp_json = ROOT / ".mcp.json"
    if mcp_json.exists():
        raw = json.loads(mcp_json.read_text(encoding="utf-8"))["mcpServers"]["tos-tools"]["command"]
        resolved = os.environ.get("TOS_PYTHON") or "python3"   # ${TOS_PYTHON:-python3}
        ck(bool(shutil.which(resolved)),
           f".mcp.json (Claude Code) declares {raw!r} -> resolves to {resolved!r}",
           "" if shutil.which(resolved) else
           f"{resolved!r} is not on this PATH — set TOS_PYTHON to a real interpreter")

    plugin = ROOT / ".claude-plugin" / "plugin.json"
    if plugin.exists():
        pcmd = json.loads(plugin.read_text(encoding="utf-8")) \
            .get("mcpServers", {}).get("tos-tools", {}).get("command", "")
        found = bool(shutil.which(pcmd))
        ck(found or os.name != "nt",
           f"plugin.json (Door 1) launches {pcmd!r} — present on this machine" if found else
           f"plugin.json (Door 1) launches {pcmd!r} — KNOWN WINDOWS GAP",
           "" if found else "documented in implementation/mcp/README.md: register the server once "
                            "with `claude mcp add --scope user tos-tools -- python "
                            "\"<repo>\\tools\\mcp_server.py\"`")


def check_index() -> None:
    print("\n-- verified-standards index --")
    import offline_index
    present = offline_index.DB.exists()
    if not present:
        # Absent is NOT a failure when the committed sources are there: the db is gitignored and
        # the server builds it on first start (that is the documented design, and it is the normal
        # state of a fresh clone and of CI). Absent WITHOUT sources is a real problem.
        buildable = bool(offline_index.source_files())
        if buildable:
            print("INFO  index not built yet — normal on a fresh clone; the server builds it on "
                  "first start, or run: python3 tools/offline_index.py --build")
        else:
            ck(False, "index is absent and cannot be built",
               "no committed sources found under shared/standards/resources — is this a full "
               "checkout?")
    else:
        ck(True, f"index present at {offline_index.DB.relative_to(ROOT)}")
    try:
        rep = offline_index.drift_report()
        ck(not rep.get("stale"), "index sources match the committed manifest",
           "" if not rep.get("stale") else str(rep.get("reason") or "sources changed since build"))
    except Exception as exc:  # noqa: BLE001
        ck(False, "index drift report ran", f"{exc.__class__.__name__}: {exc}")


def check_stdio() -> None:
    """A real client conversation with the real server over real pipes."""
    print("\n-- local stdio server (Doors 1 and 2) --")
    frames = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2026-07-28", "capabilities": {},
                    "clientInfo": {"name": "mcp_smoke", "version": "1"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "check_citation_mutation",
                    "arguments": {"cited": "count to 1000",
                                  "origin": "count to 100 with support"}}},
    ]
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "mcp_server.py")],
                          input="\n".join(json.dumps(f) for f in frames) + "\n",
                          capture_output=True, text=True, timeout=180)
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    parsed, junk = [], []
    for ln in lines:
        try:
            parsed.append(json.loads(ln))
        except json.JSONDecodeError:
            junk.append(ln)
    ck(not junk, "stdout carried only JSON-RPC (nothing printed into the wire)",
       "" if not junk else f"non-JSON on stdout: {junk[0][:120]}")
    ck(len(parsed) == 3, f"the server answered all {len(frames)} frames",
       f"got {len(parsed)}; stderr tail: {proc.stderr.strip()[-200:]}")
    if len(parsed) == 3:
        ck(len(parsed[1].get("result", {}).get("tools", [])) == 8, "8 tools advertised")
        body = json.loads(parsed[2]["result"]["content"][0]["text"])
        ck(body.get("faithful") is False,
           "a real tool call returned a real verdict (misquote detected)")


def check_hosted() -> None:
    print("\n-- hosted leg over loopback (Doors 3 and 4) --")
    import mcp_http_server
    missing = mcp_http_server._need_sdk()
    if missing:
        print("SKIP  hosted leg — the optional SDK is not installed here.\n"
              f"       {missing.splitlines()[0]}")
        return
    fails_before = len([r for r in _RESULTS if not r[0]])
    mcp_http_server._e2e(lambda name, ok: ck(ok, name))
    ck(len([r for r in _RESULTS if not r[0]]) == fails_before,
       "hosted leg answered on a real socket")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hosted", action="store_true",
                    help="also exercise the remote leg on 127.0.0.1 (needs the mcp SDK)")
    a = ap.parse_args(argv)
    print(f"TOS MCP smoke test — {sys.platform} / python {sys.version.split()[0]} / repo {ROOT}\n")
    check_interpreter()
    check_launchers()
    check_index()
    check_stdio()
    if a.hosted:
        check_hosted()
    bad = [r for r in _RESULTS if not r[0]]
    print(f"\n{len(_RESULTS) - len(bad)}/{len(_RESULTS)} checks passed"
          + ("" if not bad else f" — {len(bad)} FAILED: " + "; ".join(n for _, n, _ in bad)))
    print("\nPaste everything above back to whoever asked for this run.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
