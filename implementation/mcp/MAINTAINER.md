<!-- last_reviewed: 2026-08-15 | owner: mcp-maintainer -->
# MAINTAINER — the MCP tool surface

## Purpose
One tool registry (`tools/mcp_tooldefs.py`) serving four delivery legs: plugin-shipped stdio
(zero-step), Claude Desktop `.mcpb` (one-click), hosted streamable-HTTP (claude.ai + ChatGPT
Developer mode), and Custom GPT Actions (the generated OpenAPI). Teachers get deterministic,
verified lookups instead of model recall.

## Non-negotiable invariants
- **Stdout is the wire** (stdio leg): diagnostics to stderr only; the self-test's purity twin
  guards this.
- **Read-only surface**: every tool `readOnlyHint`; the excluded list (`--build`, `--promote`,
  harvest tools, the redundant cache index) is in the registry's docstring — additions to the
  surface are approval-gated (below).
- **The `detail` strip** in `search_standards` is load-bearing (token budget); its twin proves
  a leak would be caught.
- **No student data server-side, ever**; the hosted leg is stateless, public-standards-data
  only, request bodies never logged.
- **Tool results are data, never instructions** — stated in the served instructions and every
  corpus-returning description.
- The local leg stays **stdlib** (any Python ≥3.10, no installs); the SDK lives only on the
  hosted leg (`tools/requirements-mcp.txt`).

## Known failure modes
- **Spec churn**: the stdio server implements the 2026-07-28 revision
  (`PROTOCOL_VERSION` in `tools/mcp_server.py`). Before each release, re-verify the stdio
  frame set against the published spec at https://modelcontextprotocol.io/specification/versioning
  — a new mandatory RPC breaks local clients until patched.
- **Windows without Python**: Door 2's config fallback needs a real Python; `doctor_env.py`
  detects and points at the Store/py-launcher fix. The hosted doors need no local Python.
- **Stale index served silently**: `index_status` + the bundled index-manifest are the defense;
  the `.mcpb` must be re-staged (and re-released) after any corpus change.
- **SDK drift on the hosted leg**: CI installs the real SDK and round-trips an in-memory
  client; a red there is the SDK moving (e.g. the v1→v2 `FastMCP`→`MCPServer` rename, and the
  wire-camelCase/attr-snake_case annotations split, both already absorbed).

## Fragile fallbacks that must not become defaults
- The `--print-config` hand-edit path is the fallback for Door 2 — the `.mcpb` is the default;
  never document the hand edit first.
- LIKE-fallback search (no FTS5) is correct but slower — never treated as an error.
- The optional `TOS_MCP_TOKEN` bearer is Claude-side only (ChatGPT cannot send headers) —
  never document it as "auth for the server".

## Regression cases to preserve
1. `mcp_tooldefs --self-test` (15 probes incl. detail-leak + clamp twins).
2. `mcp_server --self-test` (13 probes incl. stdout-purity + planted-print twin).
3. `mcp_http_server --self-test` (SDK round-trip; readOnlyHint survival; rate-limit burst).
4. `export_actions_schema --self-test` + sync_check check 22 (surface freshness both platforms).
5. `build_mcpb --self-test` (staged server answers stdio from inside the staging tree;
   missing-index twin).

## Approval-gated changes (human sign-off before landing)
Any tool added/removed/renamed on the surface · any auth change on the hosted leg · deploying
(or pointing any doc at) a live endpoint · raising rate limits · shipping the `.mcpb` to a
release.

## Empirical checkpoints (unchecked until tested on real accounts)
- [ ] Claude for Teachers: can that plan self-serve a custom connector? (Docs currently hedge.)
- [ ] ChatGPT Plus: does Developer mode appear for individual Plus accounts? (OpenAI's own
      docs conflict; Door 4 is the documented-safe path meanwhile.)
- [ ] Real-Mac smoke: `.mcpb` install, GUI-PATH stdio spawn, CLT-stub run (docs/MACOS.md
      entries are UNTESTED until these flip).

## Minority-report policy
Platform-capability claims that cannot be verified from an official page are stated as hedged
("if you see it…") with the fallback door named — never asserted. Conflicting official sources
are recorded as conflicts (see the Plus-gating note), not resolved by preference.

## Update checklist
1. Change the registry → `mcp_tooldefs --self-test` → `export_actions_schema.py` (regenerate)
   → sync_check (checks 21+22 green).
2. `mcp_server --self-test` + `mcp_http_server --self-test` (venv/CI).
3. Re-stage the bundle (`build_mcpb.py`), re-verify, attach to the next release.
4. Re-verify the stdio frame set against the MCP spec page; bump `PROTOCOL_VERSION`
   deliberately, never casually.
5. Docs: this file's checkpoints; `implementation/mcp/README.md` claims; `docs/MACOS.md`
   statuses; changelog.
