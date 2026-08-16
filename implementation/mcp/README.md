<!-- last_reviewed: 2026-08-16 | owner: mcp-maintainer -->
# Connect the TOS tools — verified lookups inside your AI chat

Two minutes of setup gives your AI real, callable tools: search the **verified Florida
standards** (6,574 codes checked one-by-one against CPALMS), verify that a cited code is real
before it goes in a lesson plan, catch a standard that got misquoted, and check an artifact
against the TOS quality rules. The AI stops recalling standards from memory and starts
**looking them up**.

> Always true, whichever door you use: everything is a **draft for your review** · verified
> data is **Florida** · never type real student names — the tools neither need nor keep them.

Say **"connect my tools"** to your assistant and it will walk you through the right door below.

## Which door is mine?

| You use… | Your door | Time |
|---|---|---|
| Claude Code, or the Claude desktop app **with the TOS plugin** | **Door 1 — already connected** | 0 min |
| The Claude desktop app, no plugin | **Door 2 — one-click extension** | ~2 min |
| claude.ai in the browser / Claude mobile | **Door 3 — paste your school's tools address** | ~1 min |
| ChatGPT | **Door 3** (if you see Developer mode) or **Door 4 — a Custom GPT** | ~5 min |

## Door 1 — TOS plugin users: nothing to do

The plugin ships the tool server. If you installed TOS with the two `/plugin` commands, the
`tos-tools` server starts automatically — ask *"search the verified standards for grade 3
fractions"* and watch it call the tool.

**Known gap — Windows.** The plugin manifest launches the server with `python3`, and on Windows
that command usually does not exist: python.org's installer provides `python.exe` and `py.exe`,
never `python3.exe`. The plugin manifest format has no per-OS command and no default-value
substitution, so this cannot be fixed from inside the plugin. Until it can, Windows teachers
register the server once by hand — a user-scope entry outranks the plugin's:

```
claude mcp add --scope user tos-tools -- python "<path-to-repo>\tools\mcp_server.py"
```

(macOS and Linux are unaffected. Doors 2, 3 and 4 don't use this launcher at all.)

**Don't install two copies.** If you use the plugin *and* the Desktop extension, pick one per
app: Claude Code namespaces plugin tools so it stays clear, but adding the `.mcpb` extension
*and* a hand-written `claude_desktop_config.json` entry in Claude Desktop gives you two servers
with the same name and the same tools. Remove one.

## Door 2 — Claude desktop app: one-click extension

1. Download **`tos-tools.mcpb`** from the newest release on the GitHub Releases page
   (`https://github.com/flywifi/educator-tools-k12-public/releases`).
2. Claude Desktop → **Settings → Extensions → Advanced settings → Install Extension…** → pick
   the file. Done — everything runs on your computer, offline.

If your desktop app doesn't offer extension installs, run
`python3 tools/mcp_server.py --print-config desktop` from a repo download and your assistant
will help you place the config file (it needs a full app restart afterwards).

## Door 3 — claude.ai, Claude mobile, or ChatGPT Developer mode: paste an address

These need your school's **TOS tools address** — a web address someone at your school or
district sets up once (ask whoever set TOS up; the recipe is `deploy/mcp/README.md`). Then:

- **claude.ai / Claude apps:** Settings → **Connectors** → *Add custom connector* → paste the
  address ending in `/mcp`. (On a Team/Enterprise workspace an admin adds it for everyone.
  **Claude for Teachers:** we haven't yet confirmed whether custom connectors appear on that
  plan — try Settings → Connectors; if it's not there, Door 2 always works.)
- **ChatGPT:** Settings → **Security** → turn on **Developer mode** (if you see it — confirmed
  on Business/Enterprise/Edu, where an admin may need to enable it; on Plus, check and see) →
  add the same `/mcp` address.

## Door 4 — ChatGPT without Developer mode: a Custom GPT (works on Plus)

1. ChatGPT → Explore GPTs → **Create**. Name it "TOS Tools".
2. In **Configure → Actions → Import from URL**, paste your school's tools address ending in
   `/openapi.json`. No authentication.
3. Save (just for yourself is fine). Chat with that GPT when you want the verified tools.

## What the tools can and cannot do

- ✅ Verified Florida standards search (benchmarks + access points) · course-code lookup ·
  school/program lookup · CPALMS resources per standard · code verification (a made-up code is
  flagged as **blocking**; a code Florida withdrew shows as `retired`, never "fabricated") ·
  misquote detection · artifact rule checks · an honesty tool that reports how fresh the data is.
- ❌ They don't write lessons (the TOS skills do that), don't browse the live web, don't make
  eligibility determinations, and never store anything about you or your students.
- Using Claude for Teachers? Its built-in Learning Commons connector covers standards for all
  50 states. TOS tools are different: **code-level CPALMS-verified Florida data plus
  verification, misquote detection, and validators** — use both.

*Technical readers: the tool surface is `implementation/mcp/tool-surface.json` (generated,
CI-gated); the servers are `tools/mcp_server.py` (local, stdlib) and `tools/mcp_http_server.py`
(hosted); maintainer notes in `implementation/mcp/MAINTAINER.md`.*
