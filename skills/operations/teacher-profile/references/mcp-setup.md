<!-- last_reviewed: 2026-08-15 | owner: teacher-profile-maintainer -->
# "connect my tools" — the MCP setup flow (Claude-side script)

Trigger: the teacher says **"connect my tools"** (or asks how to get the verified
standards/lookup tools). Chat-platform sibling: the "Connect the tools" section of
`implementation/gpt/api/web-wizard.md` — keep the door list and whys aligned.

1. **Detect the door** (ask one question if unsure): TOS plugin present → Door 1, say "already
   connected" and demonstrate with a live `search_standards` call. Claude desktop app → Door 2
   (.mcpb from the GitHub Release; Settings → Extensions). claude.ai/mobile/ChatGPT → Door 3/4
   (needs the school's TOS tools address — if the teacher doesn't have one, say so honestly and
   point at `deploy/mcp/README.md` for whoever runs their tech).
2. **Say the why**: *"these tools make me look up your standards from the verified corpus
   instead of remembering them — a code I can't find gets flagged instead of invented."*
3. **File-offer ladder for Door 2's fallback config** (same ladder as the profile file): offer
   to run `python3 tools/mcp_server.py --print-config desktop` (on Windows: `py -3 tools\mcp_server.py --print-config desktop` — `python3` is not a command there) and write the file; else give
   the exact clicks (TextEdit: Format → Make Plain Text; Windows Notepad: Save as type →
   All Files), then a FULL app restart.
4. **Never oversell**: hedge the Claude-for-Teachers connector question and ChatGPT Plus
   Developer-mode question exactly as `implementation/mcp/README.md` does; Door 4 (Custom GPT)
   is the always-works ChatGPT path.
5. No student data ever goes in a tool query; the tools are read-only and keep nothing.
