#!/usr/bin/env python3
"""TOS local MCP server — stdlib-only JSON-RPC over stdio, for Claude Code + Claude Desktop.

WHY STDLIB AND NOT THE SDK: the official `mcp` package drags pydantic/starlette/uvicorn —
compiled, platform-specific wheels — which would force a pip install (or per-platform bundles)
on every teacher before first use. This server implements the small stdio subset the protocol
needs (newline-delimited JSON-RPC: initialize, notifications/initialized, ping, tools/list,
tools/call, server/discover) in pure stdlib, so it runs on ANY Python >= 3.10 — including the
macOS Xcode CLT stub — with nothing installed. The hosted HTTP leg (tools/mcp_http_server.py)
uses the real SDK, where a container already exists and session management earns it.

SPEC-CHURN CONTRACT: the implemented protocol revision is the PROTOCOL_VERSION constant below;
the self-test pins the frame shapes; MAINTAINER.md requires re-verifying against the published
spec (modelcontextprotocol.io) before each release. A client offering an unknown newer version
gets ours back and decides — per-request version negotiation is the client's job in the
2026-07-28 revision.

STDOUT IS THE WIRE. Every diagnostic goes to stderr; a stray print() corrupts the protocol
stream. The self-test asserts output purity (exactly one JSON-RPC frame per request, nothing
else) and proves the assertion can fail with a planted-print twin.

Tools come from tools/mcp_tooldefs.py — the single registry every transport shares.

Startup index handling: offline.db present -> serve; absent but canonical sources present
(repo clone) -> build once at startup (stderr progress; building is NEVER a callable tool —
it is destructive and non-atomic); absent with no sources (stripped install) -> serve anyway,
lookups return a structured `index_unavailable` error naming the fix.

Usage:
  python3 tools/mcp_server.py                        # serve stdio (a client launches this)
  python3 tools/mcp_server.py --print-config desktop # exact claude_desktop_config.json fragment
  python3 tools/mcp_server.py --print-config code    # exact .mcp.json fragment (Claude Code)
  python3 tools/mcp_server.py --self-test            # offline frame-level probes (CI)
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcp_tooldefs  # noqa: E402

PROTOCOL_VERSION = "2026-07-28"
# Versions we can speak. `initialize` echoes the CLIENT's version when it is one of these
# (per-request negotiation is the client's job in 2026-07-28), ours otherwise — silently
# answering with a different version than the client asked for invites a mid-session mismatch.
SUPPORTED_PROTOCOL_VERSIONS = (PROTOCOL_VERSION, "2025-06-18", "2025-03-26")


def _server_version() -> str:
    vf = ROOT / "VERSION"
    return vf.read_text(encoding="utf-8").strip() if vf.exists() else "0.0.0"


def _server_info() -> dict:
    return {"name": "tos-tools", "title": "TOS verified teacher tools",
            "version": _server_version()}


def _ensure_index() -> None:
    """Build the offline index once at startup if it's absent but buildable. Stderr only."""
    import offline_index
    if offline_index.DB.exists():
        return
    try:
        if offline_index.source_files():
            print("[tos-tools] offline index absent — building once from committed sources…",
                  file=sys.stderr)
            offline_index.build()
            print("[tos-tools] index built.", file=sys.stderr)
    except Exception as exc:  # startup must never kill the transport — tools degrade honestly
        print(f"[tos-tools] index build failed ({exc.__class__.__name__}: {exc}); lookups "
              f"will return index_unavailable with the fix command.", file=sys.stderr)


# ---------------------------------------------------------------------------------- frame layer
def _result(id_, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle_frame(line: str) -> dict | None:
    """One request line -> one response dict, or None for notifications. Pure; no I/O."""
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return _error(None, -32700, "parse error: request is not valid JSON")
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        return _error(msg.get("id") if isinstance(msg, dict) else None,
                      -32600, "invalid request: expected a JSON-RPC 2.0 method call")
    method, id_, params = msg["method"], msg.get("id"), msg.get("params") or {}
    if id_ is None:  # notification — never answered
        return None
    try:
        return _dispatch(method, id_, params)
    except Exception as exc:
        # Layer 2. NOT redundant with call_tool's guard: json.dumps() below raises TypeError on
        # any non-serializable value a handler returns (sqlite3.Row, Decimal, Path) — that raise
        # happens OUTSIDE call_tool, and this is the only thing that catches it.
        print(f"[tos-tools] frame handling failed: {traceback.format_exc()}", file=sys.stderr)
        return _error(id_, -32603, f"internal error: {exc.__class__.__name__}")


def _dispatch(method: str, id_, params: dict) -> dict:
    if method == "initialize":
        want = params.get("protocolVersion")
        return _result(id_, {"protocolVersion": (want if want in SUPPORTED_PROTOCOL_VERSIONS
                                                 else PROTOCOL_VERSION),
                             "capabilities": {"tools": {"listChanged": False}},
                             "serverInfo": _server_info(),
                             "instructions": mcp_tooldefs.server_instructions()})
    if method == "ping":
        return _result(id_, {})
    if method == "server/discover":  # mandatory in the 2026-07-28 revision
        return _result(id_, {"protocolVersion": PROTOCOL_VERSION,
                             "capabilities": {"tools": {"listChanged": False}},
                             "serverInfo": _server_info()})
    if method == "tools/list":
        return _result(id_, {"tools": mcp_tooldefs.list_tools()})
    if method == "tools/call":
        name = params.get("name", "")
        out = mcp_tooldefs.call_tool(name, params.get("arguments") or {})
        return _result(id_, {"content": [{"type": "text",
                                          "text": json.dumps(out, ensure_ascii=False)}],
                             "isError": "error" in out})
    return _error(id_, -32601, f"method not found: {method}")


def serve(stdin=None, stdout=None) -> int:
    """The stdio loop. Streams are injectable for the self-test; stdout carries ONLY frames."""
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    _ensure_index()
    print(f"[tos-tools] serving {len(mcp_tooldefs.TOOLS)} read-only tools "
          f"(protocol {PROTOCOL_VERSION}, v{_server_version()})", file=sys.stderr)
    # readline(), not `for line in stdin`: iteration read-ahead buffers on a pipe and can delay a
    # response indefinitely, and per-line structure is what makes the guards below legal.
    while True:
        try:
            line = stdin.readline()
        except KeyboardInterrupt:
            return 0                       # the client's shutdown signal, not an error
        if not line:                       # EOF — the client closed the pipe
            return 0
        line = line.strip()
        if not line:
            continue
        try:
            resp = handle_frame(line)
        except Exception:                  # layer 3: nothing gets past the loop
            print(f"[tos-tools] unhandled: {traceback.format_exc()}", file=sys.stderr)
            resp = _error(_recover_id(line), -32603, "internal error")
        if resp is None:
            continue
        try:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()
        except (BrokenPipeError, OSError, ValueError):
            # Client vanished mid-write (on Windows the same condition arrives as OSError/
            # EINVAL). A traceback into a dead pipe is noise; leave quietly.
            print("[tos-tools] client closed the connection", file=sys.stderr)
            return 0


def _recover_id(raw: str):
    """Best-effort id from a raw line so an internal error can still be addressed to its call."""
    try:
        return json.loads(raw).get("id")
    except Exception:
        return None


# --------------------------------------------------------------------------------- setup output
def print_config(kind: str) -> int:
    """Emit an exact, absolute-path config fragment. The GUI has no shell PATH (the E2
    finding), so `command` is THIS interpreter's absolute path and PATH is set explicitly."""
    server = str((ROOT / "tools" / "mcp_server.py").resolve())
    entry = {"command": sys.executable, "args": [server],
             "env": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}}
    if kind == "desktop":
        print(json.dumps({"mcpServers": {"tos-tools": entry}}, indent=2))
        print("\nMerge into claude_desktop_config.json "
              "(macOS: ~/Library/Application Support/Claude/ · Windows: %APPDATA%\\Claude\\),\n"
              "via Claude Desktop: Settings > Developer > Edit Config, then FULLY quit and "
              "relaunch.", file=sys.stderr)
    else:
        print(json.dumps({"mcpServers": {"tos-tools": {
            "type": "stdio", **entry}}}, indent=2))
        print("\nMerge into .mcp.json at the repo root (Claude Code project scope).",
              file=sys.stderr)
    return 0


# ------------------------------------------------------------------------------------ self-test
def self_test() -> int:
    """Frame-level probes, offline. Includes the stdout-purity twin."""
    import io
    fails = 0

    def ck(name: str, ok: bool) -> None:
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    def rpc(method, id_=1, params=None):
        return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method,
                           "params": params or {}})

    r = handle_frame(rpc("initialize", params={"protocolVersion": "2026-07-28"}))
    ck("initialize: protocol version + serverInfo + governance instructions",
       r["result"]["protocolVersion"] == PROTOCOL_VERSION
       and r["result"]["serverInfo"]["name"] == "tos-tools"
       and "fabricate" in r["result"]["instructions"])
    ck("notifications/initialized: a notification gets NO response",
       handle_frame(json.dumps({"jsonrpc": "2.0",
                                "method": "notifications/initialized"})) is None)
    ck("ping answers", handle_frame(rpc("ping"))["result"] == {})
    r = handle_frame(rpc("server/discover"))
    ck("server/discover (2026-07-28 mandatory) answers with server info",
       r["result"]["serverInfo"]["name"] == "tos-tools")
    r = handle_frame(rpc("tools/list"))
    ck("tools/list: 8 tools, readOnlyHint intact on the wire",
       len(r["result"]["tools"]) == 8
       and all(t["annotations"]["readOnlyHint"] for t in r["result"]["tools"]))
    r = handle_frame(rpc("tools/call", params={"name": "check_citation_mutation",
                                               "arguments": {"cited": "count to 1000",
                                                             "origin": "count to 100"}}))
    body = json.loads(r["result"]["content"][0]["text"])
    ck("tools/call: dispatches through the registry, text-content envelope",
       body["faithful"] is False and r["result"]["isError"] is False)
    r = handle_frame(rpc("tools/call", params={"name": "no_such_tool"}))
    ck("tools/call: unknown tool -> isError true, structured body",
       r["result"]["isError"] is True)
    ck("malformed JSON -> -32700", handle_frame("{nope")["error"]["code"] == -32700)
    ck("unknown method -> -32601", handle_frame(rpc("frobnicate"))["error"]["code"] == -32601)
    ck("non-JSON-RPC object -> -32600",
       handle_frame(json.dumps({"hello": 1}))["error"]["code"] == -32600)

    # stdout purity: the loop writes exactly one frame per request and nothing else.
    fin = io.StringIO(rpc("ping", 1) + "\n" + rpc("tools/list", 2) + "\n")
    fout = io.StringIO()
    real_ensure = globals()["_ensure_index"]
    globals()["_ensure_index"] = lambda: None  # keep the purity probe offline/fast
    try:
        serve(stdin=fin, stdout=fout)
    finally:
        globals()["_ensure_index"] = real_ensure

    def pure(text: str) -> bool:
        lines = [ln for ln in text.splitlines() if ln]
        try:
            return all(json.loads(ln).get("jsonrpc") == "2.0" for ln in lines)
        except json.JSONDecodeError:
            return False
    ck("stdout purity: every output line is a JSON-RPC frame",
       pure(fout.getvalue()) and len(fout.getvalue().splitlines()) == 2)
    ck("twin: a planted stray print corrupts the stream and the purity check CATCHES it",
       not pure("[tos-tools] oops, a diagnostic on stdout\n" + fout.getvalue()))

    # --- survival probes (C-1 layers 2+3, C-3) --------------------------------------------
    r = handle_frame(rpc("initialize", params={"protocolVersion": "2025-06-18"}))
    ck("initialize: a SUPPORTED client version is echoed back, not silently replaced",
       r["result"]["protocolVersion"] == "2025-06-18")
    r = handle_frame(rpc("initialize", params={"protocolVersion": "1999-01-01"}))
    ck("initialize: an unsupported version falls back to ours",
       r["result"]["protocolVersion"] == PROTOCOL_VERSION)

    real_call = mcp_tooldefs.call_tool
    mcp_tooldefs.call_tool = lambda n, a: {"leak": object()}   # non-JSON-serializable
    try:
        r = handle_frame(rpc("tools/call", params={"name": "search_standards",
                                                   "arguments": {"query": "x"}}))
        ck("C-3: a non-serializable handler result becomes -32603, not a raise",
           r.get("error", {}).get("code") == -32603)
        raised = False
        try:
            json.dumps({"leak": object()})
        except TypeError:
            raised = True
        ck("twin: json.dumps on that value DOES raise — the hole layer 2 exists to plug", raised)
    finally:
        mcp_tooldefs.call_tool = real_call

    # THE headline regression: the audit's exact reproduction (corrupt db, tools/call, ping).
    import sqlite3 as _sq
    import tempfile as _tf
    import offline_index as _oi
    bad = Path(_tf.mkdtemp()) / "corrupt.db"
    bad.write_bytes(b"not a database")
    real_db, _oi.DB = _oi.DB, bad
    real_ensure = globals()["_ensure_index"]
    globals()["_ensure_index"] = lambda: None
    try:
        fin2 = io.StringIO(rpc("tools/call", 1, {"name": "search_standards",
                                                 "arguments": {"query": "x"}}) + "\n"
                           + rpc("ping", 2) + "\n")
        fout2 = io.StringIO()
        crashed = False
        try:
            serve(stdin=fin2, stdout=fout2)
        except Exception:
            crashed = True
        frames = [ln for ln in fout2.getvalue().splitlines() if ln]
        ck("REGRESSION (audit repro): corrupt db -> 2 frames written, ping ANSWERED, no crash",
           not crashed and len(frames) == 2 and json.loads(frames[1])["id"] == 2)
    finally:
        _oi.DB = real_db
        globals()["_ensure_index"] = real_ensure
    del _sq

    class _DeadPipe(io.StringIO):
        def write(self, _s):
            raise BrokenPipeError(32, "Broken pipe")
    globals()["_ensure_index"] = lambda: None
    try:
        rc = serve(stdin=io.StringIO(rpc("ping", 1) + "\n"), stdout=_DeadPipe())
        ck("a client that vanishes mid-write ends the loop cleanly (rc 0, no traceback)", rc == 0)
    finally:
        globals()["_ensure_index"] = real_ensure

    cfg_out = io.StringIO()
    real = sys.stdout
    sys.stdout = cfg_out
    try:
        print_config("desktop")
    finally:
        sys.stdout = real
    cfg = json.loads(cfg_out.getvalue())
    ck("--print-config desktop: absolute command + explicit PATH env (the E2 rule)",
       Path(cfg["mcpServers"]["tos-tools"]["command"]).is_absolute()
       and cfg["mcpServers"]["tos-tools"]["env"]["PATH"].startswith("/opt/homebrew/bin"))

    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--print-config", choices=["desktop", "code"],
                    help="emit an exact config fragment instead of serving")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.print_config:
        return print_config(a.print_config)
    return serve()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
