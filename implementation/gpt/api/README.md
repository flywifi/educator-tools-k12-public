<!-- last_reviewed: 2026-09-25 | owner: api-maintainer -->
# TOS on the OpenAI API — RETIRED (2026-09, R5-B)

This folder held OpenAI **Chat Completions** function schemas for 29 TOS skills
(`tools.json`/`tools.yaml`/`skills/*.yaml`) and the Custom GPT **Actions** OpenAPI
(`actions-openapi.json`). All were removed:

- **Custom GPTs retire 2026-12-11** platform-wide (Enterprise deferrals 2027-02-11); personal
  plans lost GPT creation in 2026, and custom Actions do not survive OpenAI's migration.
- The Chat Completions export targeted an API style OpenAI no longer recommends for tools
  (the newest models require the Responses API for tool calling or restrict it), had never had
  an executor, and cost ~40k tokens of schema per conversation.

**What replaced them** (see the loss record in `changes/CHANGELOG.md` under v1.7.0):
- Teachers in the browser: the Reference-Pack Project — `implementation/gpt/web/`.
- Teachers on the ChatGPT desktop app: the LOCAL tos-tools server (Settings → MCP servers →
  STDIO, or a plugin) — `implementation/mcp/README.md` Door 3.
- Developers: the MCP surface (`tools/mcp_tooldefs.py` registry; `tools/mcp_server.py` stdio;
  the dormant hosted `/mcp` leg) — usable from the OpenAI Responses API's `mcp` tool type.

`system-prompt.md` (the governance prompt) and `web-wizard.md` (the ChatGPT setup wizard)
remain in this folder because the web Project path still uses them.
