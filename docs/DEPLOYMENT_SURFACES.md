# DEPLOYMENT_SURFACES.md — where the TOS runs (and how data is handled per surface)

> Teacher-friendly version of this: [`implementation/claude/README.md`](../implementation/claude/README.md).

The TOS core is **model- and surface-neutral**: Markdown policies/schemas/taxonomies + **stdlib-only**
Python helpers (`shared/connectors/connectors.py`, `shared/students/students.py`,
`skills/operations/meeting-classifier/scripts/classify_meeting.py`, `tools/crosswalk.py`, `shared/context/context.py`)
with no network dependency. The Claude **Skill** packaging is a convenience layer, not a requirement.
Three surfaces are supported; the difference is mostly **where student data lives** (the storage adapter
— `shared/students/student-data-policy.md`) and **which connectors** are available
(`shared/connectors/connectors.md`).

## 1. Claude Code / desktop (filesystem + repo) — full experience
- Scripts run locally; `git` push.
- Student storage adapter = **`local_gitignored`**: real profiles in `shared/students/students.local.json`
  (gitignored) — never committed. Placeholders only in tracked files.
- Connectors: enable whatever the deployment has via a `feature-flags.*.json`.

## 2. claude.ai web chat (no local filesystem)
- No gitignored store. Storage adapter falls back to **`session_ephemeral`** (the teacher pastes the
  profile each session; nothing persisted by the tool) or **`uploaded_file`** (a profile file uploaded
  per session, read via `shared/docintel/`), or the platform's **Project knowledge** (teacher-managed).
- Connectors (Google Workspace/Classroom, SIS, …) supply data when connected; otherwise rely on pasted
  / uploaded clues. The same skills, policies, and taxonomies apply as loaded context.
- The tool persists nothing itself; the teacher controls data through the chat platform.

## 3. Another AI model entirely
- Use the Markdown references/policies as system-prompt / project context, and run the **stdlib Python**
  helpers standalone (no Claude/network dependency). Classification, connector degradation/convergence,
  the grade/standards crosswalks, and the student-data policy all work unchanged.
- A full model-agnostic **export bundle** is an optional follow-up, not built yet.

## Invariants across every surface
- **SIS-first** precedence + **SIS↔local conflict** escalation hold everywhere
  (`shared/students/student-data-policy.md`).
- **Real student PII/ePHI is never committed to git** on any surface (placeholders only in tracked
  files). ePHI is **surfaced from the source on file (attributed; signature not required), never generated**.
- Connectors that are off/blocked are never presented as active; degraded paths lower confidence.
- Identification mode (`name` default, `id`-only available) applies to saved/shared records on all
  surfaces.

## Cross-platform notes (Windows / macOS desktop ↔ the Claude/ChatGPT app)
The offline tools run on a teacher's desktop; the app runs on Windows or Mac. Things that bite at
that boundary (found by adversarial audit, mitigations in place):
- **Python command:** internal calls use `sys.executable` (safe — never spawn a child by the bare
  name `python3`/`python`, or a macOS venv can silently launch the wrong interpreter). Doc/command
  lines say `python3`: on **Windows** many installs don't provide it — use `py -3 …` or `python …`.
  On **macOS**, `/usr/bin/python3` is only an Xcode Command-Line-Tools *stub* (older/incomplete;
  first use triggers the CLT install prompt); install a real interpreter via Homebrew or python.org,
  and use `python3 -m pip` (a bare `pip` is often absent). The assistant should pick the platform
  interpreter, not literally `python3`.
- **macOS Python packaging (PEP 668):** Homebrew/system Python are *externally managed* — a bare
  `pip install -r tools/requirements-*.txt` fails with `error: externally-managed-environment`.
  **Preferred: install into the repo's managed venv** — `python3 tools/deps_preflight.py --install
  <capability>` (e.g. `office_authoring`) or `--install tools/requirements-<name>.txt`. It builds/uses
  the isolated, gitignored `.harvest-venv/`, installs **wheels-only**, and **never touches system
  Python** — so PEP 668 never triggers. `python3 tools/deps_preflight.py --python-path` prints that
  venv's interpreter (the exact Python to point a Claude Desktop MCP `command`/a GUI launch at). A
  manual venv works too: `python3 -m venv .venv && source .venv/bin/activate` then `pip install -r …`
  (`--break-system-packages` exists but is risky; pipx suits standalone CLI tools). Homebrew's prefix
  differs by chip — **`/opt/homebrew` on Apple Silicon**, `/usr/local` on Intel — so never hardcode
  `/usr/local/bin/<tool>`; arm64 Python also needs arm64/universal2 wheels.
- **macOS Gatekeeper (installing LibreOffice/tesseract/ffmpeg):** a browser-downloaded, un-notarized
  app is blocked ("developer cannot be verified"). On **macOS Sequoia 15 the old Control-click →
  Open trick is gone** — allow it under **System Settings › Privacy & Security › Open Anyway**. A
  `curl`/`tar` download sets no quarantine; `xattr -d com.apple.quarantine <app>` clears it.
- **macOS Claude Desktop MCP (GUI has no shell PATH):** a stdio MCP server receives only its `env`
  block, not your shell `PATH`, so `command: "python3"` (or any bare `soffice`/`node`) is "not
  found". Use an **absolute interpreter path** (e.g. `/opt/homebrew/bin/python3`) and set
  `env.PATH` to include `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`. (Config lives at
  `~/Library/Application Support/Claude/claude_desktop_config.json`.)
- **Line endings:** the content-hash guards (`offline_index.py`, `registry_currency.py`) normalize
  CRLF→LF before hashing, and `.gitattributes` pins `*.json/*.py/*.md/*.yaml` to `eol=lf`, so a
  Windows `autocrlf` checkout does **not** false-trip the freshness gate. Don't remove either.
- **LibreOffice (PDF/PNG render + legacy `.doc` parse):** not on PATH by default on Win/Mac;
  `shared/office/office_authoring.py` now also checks the standard install locations
  (`C:\Program Files\LibreOffice\…`, `/Applications/LibreOffice.app/…`). If it's not installed the
  document is still produced — only the PDF/PNG render is skipped, with an honest note.
- **Profile portability:** move the teacher profile between the desktop store
  (`teacher.local.json`) and the app file (`my-teacher-profile.md`) with
  `profile_wizard.py --export-md` / `--import-md` (lossless; tolerates a Notepad BOM + CRLF) — no
  re-doing the interview per surface.
- **Notepad trap:** saving `my-teacher-profile.md` in Windows Notepad appends `.txt` unless
  "Save as type" is set to **All Files**.

## MCP tool surface (2026-08-15)

The registry `tools/mcp_tooldefs.py` serves 8 read-only tools on four legs: plugin-shipped
stdio (zero-step; `plugin.json` `mcpServers`), the `.mcpb` Claude Desktop extension
(one-click; `tools/build_mcpb.py`), the hosted streamable-HTTP leg (`tools/mcp_http_server.py`
— claude.ai connectors + ChatGPT; dormant until a human deploys `deploy/mcp/`), and the
generated Custom GPT Actions schema (`tools/export_actions_schema.py`, sync_check check 22).
Data handling: nothing student-related ever transits any leg — queries are standards
codes/topics over a public, CPALMS-verified corpus; the hosted leg is stateless with no
request-body logging. The local stdio leg is deliberately stdlib (runs on the CLT stub with
zero installs); the platform truth that shaped all of this: ChatGPT and claude.ai remote
connectors are brokered from vendor clouds, so localhost serves only Claude Desktop/Code stdio.

**Launcher interpreters (updated 2026-08-16).** All three JSON launchers originally spawned the
stdio server as `python3`, which is exactly the E2 defect in a file the Python lint could not
see: on Windows that command does not exist (python.org ships `python.exe`/`py.exe`), and under a
macOS GUI PATH it may not resolve. Now: `.mcp.json` uses `${TOS_PYTHON:-python3}` with
`${CLAUDE_PROJECT_DIR:-.}` for the script path (also fixing a cwd-relative argument), and the
`.mcpb` manifest declares `platform_overrides.win32 → python`. `plugin.json` **cannot** be fixed —
its schema has neither per-OS commands nor default-valued substitution, and an unresolved
`${VAR}` would be passed through literally — so Door 1 on Windows stays broken by platform
design, with a user-scope `claude mcp add` workaround documented in `implementation/mcp/README.md`.
`tools/mac_audit.py` now lints these JSON launchers (check `json-launcher`, consumed by sync_check
check 19) so a fourth recurrence fails locally and in CI.
