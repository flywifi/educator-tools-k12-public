<!-- last_reviewed: 2026-11-25 | owner: repo-maintainer -->
# CLAUDE.md
**For developers/contributors working in this repo** — not needed to *use* TOS (see `README.md` for that).

The repository's conventions live in `AGENTS.md`, so Codex, Antigravity and other coding agents
read the same rules. Claude Code loads them through this import:

@AGENTS.md

## Claude Code notes
- Claude Code ignores a bare `AGENTS.md` whenever a `CLAUDE.md` exists, which is why the import
  above is load-bearing. Put shared rules in `AGENTS.md`; keep this file for Claude-only notes.
