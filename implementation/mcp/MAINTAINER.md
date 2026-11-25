<!-- last_reviewed: 2026-11-25 | owner: mcp-maintainer -->
# MAINTAINER — the MCP tool surface

## Purpose
One tool registry (`tools/mcp_tooldefs.py`) serving four delivery legs: plugin-shipped stdio
(zero-step), Claude Desktop `.mcpb` (one-click), hosted streamable-HTTP (claude.ai + ChatGPT
Developer mode; the Actions leg was retired 2026-09 — R5-B). Teachers get deterministic,
verified lookups instead of model recall.

## Non-negotiable invariants
- **Stdout is the wire** (stdio leg): diagnostics to stderr only; the self-test's purity twin
  guards this.
- **Read-only surface**: every tool `readOnlyHint`; the excluded list (`--build`, `--promote`,
  harvest tools, the redundant cache index) is in the registry's docstring — additions to the
  surface are approval-gated (below).
- **The `detail` strip** in `search_standards` is load-bearing (token budget); its twin proves
  a leak would be caught.
- **No student data server-side, ever**; public-standards-data only, request bodies never
  logged. (Statelessness is NOT in this list: it is the default but `TOS_MCP_STATELESS=false`
  pins one instance. The invariant is the absence of identity and student data, which no env
  var can toggle.)
- **The advertised schema is enforced, not decorative**: `_validate_args` in the registry runs on
  every leg (stdio, SDK `/mcp`, REST `/v1/*`) before any handler sees an argument. `limit` clamps;
  everything else is rejected with `invalid_arguments`.
- **The gate is middleware, never per-route**: rate limit and `TOS_MCP_TOKEN` run ahead of routing
  so they cover `/mcp`, which is a mounted sub-app a per-route check cannot reach.
- **Tool results are data, never instructions** — stated in the served instructions and every
  corpus-returning description.
- The local leg stays **stdlib** (any Python ≥3.10, no installs); the SDK lives only on the
  hosted leg (`tools/requirements-mcp.txt`), in its **own** venv — the `mcp_server` capability is
  `"isolated": true` because semgrep pins `mcp<2` and a shared venv silently downgraded the SDK.
  Point a launcher at it with `deps_preflight.py --python-path mcp_server`.

## Known failure modes
- **Spec churn**: the stdio server implements the 2026-07-28 revision
  (`PROTOCOL_VERSION` in `tools/mcp_server.py`). Before each release, re-verify the stdio
  frame set against the published spec at https://modelcontextprotocol.io/specification/versioning
  — a new mandatory RPC breaks local clients until patched.
- **Windows**: `python3` does not exist there (python.org ships `python.exe` and `py.exe`). The
  `.mcpb` carries `platform_overrides.win32 -> python`; `.mcp.json` uses `${TOS_PYTHON:-python3}`.
  **`plugin.json` cannot be fixed** — the plugin manifest format has no per-OS command and no
  default-valued substitution — so Door 1 does not start on a Windows box with a python.org
  Python. The workaround (a user-scope `claude mcp add`) lives in `implementation/mcp/README.md`,
  and `mac_audit`'s json-launcher check exempts that launcher ONLY while the workaround stays
  documented there. The hosted doors need no local Python.
- **A mounted sub-app has no lifespan**: `/mcp` returned 500 to every request from the hosted
  leg's first commit until 2026-08-16, because Starlette does not run a `Mount()`ed app's
  lifespan and that lifespan creates the session manager's task group. The in-memory `Client(mcp)`
  self-test could never see it. Any future restructuring of `build_app()` must keep
  `lifespan=sub.router.lifespan_context` — and the real-socket probe that proves it.
- **Stale index served silently**: `index_status` + the bundled index-manifest are the defense;
  the `.mcpb` must be re-staged (and re-released) after any corpus change.
- **SDK drift on the hosted leg**: CI installs the real SDK and round-trips an in-memory
  client; a red there is the SDK moving (e.g. the v1→v2 `FastMCP`→`MCPServer` rename, and the
  wire-camelCase/attr-snake_case annotations split, both already absorbed).

## Fragile fallbacks that must not become defaults
- The `--print-config` hand-edit path is the fallback for Door 2 — the `.mcpb` is the default;
  never document the hand edit first.
- LIKE-fallback search (no FTS5) is correct but slower — never treated as an error.
- `TOS_MCP_TOKEN` gates `/mcp` and `/v1/*` via middleware; `/healthz` and `/openapi.json` stay
  token-exempt (but rate-limited) because gating them breaks platform health probes and ChatGPT's
  Import-from-URL respectively. MCP **connectors** on either platform cannot send it — the
  "ChatGPT cannot send headers" rationale was retracted on 2026-08-16 in
  `security/SECURITY_REVIEW.md`; do not reintroduce it. Never document the token as "auth for the
  server".

## Regression cases to preserve
Probe COUNTS are deliberately not written here — a typed count is the drift class this repo
already eradicated everywhere else. Run the self-test; its probe list is the source of truth.

1. `mcp_tooldefs --self-test` — detail-strip leak twin, limit clamp, fabricated-code block,
   schema enforcement (a bogus enum must be rejected, not silently answered `count: 0`), and the
   survival probes: a corrupt index must return a structured error, never kill the process.
2. `mcp_server --self-test` — frame shapes, error codes, stdout-purity planted-print twin, and
   the crash guards (a non-serializable handler return, a dead stdout, `SystemExit` never
   swallowed).
3. `mcp_http_server --self-test` — SDK round-trip, `readOnlyHint` survival, rate-limit burst,
   ASGI-level token gating of `/mcp`, `public_url` resolution, `TOS_MCP_PORT` refusal,
   `schema_parity()`, **and the real-socket E2E plus its no-lifespan twin**.
4. **sync_check check 23** (22 retired with the Actions leg, R5-B): **23 holds the
   SDK-derived Claude schema to the same
   registry**. 22 alone cannot see registry-vs-SDK divergence — that is exactly how all eight
   tools once advertised different rules per platform.
5. `build_mcpb --self-test` — staged server answers stdio from inside the staging tree;
   missing-index twin; `manifest_version 0.3` and the win32 override asserted; `launch_command`
   probes cover the Windows branch no Linux runner can execute.
6. `mcp_smoke.py` — the paste-back script itself, run in CI so what we hand a teacher is tested.

Note on the packer: `mcpb validate` is schema-only. It passes a manifest with `manifest_version
0.2` and no win32 override, so it would NOT have caught H-4 or L-6. The repo-side probes are the
guard; the CLI's job is producing the artifact (`mcpb pack`, and `mcpb sign --self-signed` if the
owner decides to sign).

## Approval-gated changes (human sign-off before landing)
Any tool added/removed/renamed on the surface · any auth change on the hosted leg · deploying
(or pointing any doc at) a live endpoint · raising rate limits · shipping the `.mcpb` to a
release.

## Empirical checkpoints (unchecked until tested on real accounts)
- [ ] Claude for Teachers: plugin install + custom connector on a real teacher account
      (vendor text: free Team plan; connectors/plugins not on its disabled list — inferred).
- [x] ChatGPT web Developer mode: **Business/Enterprise/Edu only** (help 12584461, 2026-08);
      the desktop app's Settings → MCP servers (STDIO) is the individual-plan tools path —
      end-to-end UNTESTED-live.
- [ ] Real-Mac smoke: `.mcpb` install, GUI-PATH stdio spawn, CLT-stub run (docs/MACOS.md
      entries are UNTESTED until these flip).

## Minority-report policy
Platform-capability claims that cannot be verified from an official page are stated as hedged
("if you see it…") with the fallback door named — never asserted. Conflicting official sources
are recorded as conflicts (see the Plus-gating note), not resolved by preference.

## Other vendors' SDKs (developers only; tested 2026-11-25)
Teachers never need this. It records what works so a developer wiring TOS into an app does not
rediscover it.
- **OpenAI Agents SDK** (https://openai.github.io/openai-agents-python/mcp/) runs the local server
  unchanged (tested `openai-agents` 0.25.0: 9 tools listed, `verify_standard_codes` answered):

  ```python
  import sys
  from agents.mcp import MCPServerStdio
  server = MCPServerStdio(params={"command": sys.executable, "args": ["tools/mcp_server.py"]},
                          cache_tools_list=True, client_session_timeout_seconds=60)
  ```
- **Gemini API, `google-genai`**: do not hand the MCP session to the SDK's automatic tool
  conversion. In `google-genai` 3.6.1 it raises on every TOS tool, because each input schema sets
  `"additionalProperties": false`. Declare the tools yourself with `parameters_json_schema`, which
  takes full JSON Schema (https://ai.google.dev/gemini-api/docs/function-calling). Tested: 9
  declarations, and a function-call round trip returned `not_found` for a made-up code.

  ```python
  from google.genai import types
  def to_gemini_tool(mcp_tools) -> types.Tool:
      return types.Tool(function_declarations=[types.FunctionDeclaration(
          name=t.name, description=t.description or "",
          parameters_json_schema=getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)
          or {"type": "object"}) for t in mcp_tools])
  ```
- **Hosted routes all need a public server**, which this project does not run (decision: keep
  `tools/mcp_http_server.py` dormant; a school can self-host it per `deploy/mcp/README.md`).
  OpenAI's Responses API `mcp` tool takes a `server_url` or a Secure MCP Tunnel
  (https://developers.openai.com/api/docs/guides/tools-connectors-mcp,
  https://developers.openai.com/api/docs/guides/secure-mcp-tunnels). Claude's MCP connector takes
  remote servers only (https://platform.claude.com/docs/en/agents-and-tools/mcp-connector). Gemini's
  Interactions API takes Streamable HTTP servers only and no `-` in the server name (use
  `tos_tools`), and Google lists remote MCP as not yet supported on Gemini 3 models.

## Update checklist
1. Change the registry → `mcp_tooldefs --self-test` → sync_check (checks 21 and 23 green;
   23 needs the SDK installed, and CI asserts it inside `mcp_http_server --self-test`
   regardless).
2. `mcp_server --self-test` + `mcp_http_server --self-test` (venv/CI).
3. Re-stage the bundle (`build_mcpb.py`), re-verify, attach to the next release.
4. Re-verify the stdio frame set against the MCP spec page; bump `PROTOCOL_VERSION`
   deliberately, never casually.
5. Docs: this file's checkpoints; `implementation/mcp/README.md` claims; `docs/MACOS.md`
   statuses; changelog.
