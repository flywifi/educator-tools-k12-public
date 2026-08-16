# CLAUDE.md
**For developers/contributors working in this repo** — not needed to *use* TOS (see `README.md` for that).
Conventions for working in the Teacher Operating System (TOS) repository.

## What this repo is
A hub-and-spoke ecosystem of Claude Agent Skills that generate, validate, differentiate, and govern
K-12 educational artifacts. Read `docs/ARCHITECTURE.md` for the design. Live status: `STATE.md`.

## Layout
- `skills/` — sub-grouped: `core/` (hub + governance), `educator/` (content skills), `operations/` (tools/feeds/profile), `atoms/` (single-operation sub-skills).
- `shared/` — canonical cross-cutting engines (Standards, Differentiation, Quality). **Source of truth.**
- `protocol-layer/` — the 6 governance protocols. **Source of truth.** `quality-gates.md` is authoritative.
- `canonical-sources/` — authoritative reference data: `registries/` (FL standards + OCPS registries), `schools/` (school indexes), `districts/` (district overlays), `overlays/` (context overlays), root FL district + school-type JSON.
- `tools/` — `sync_check.py` (drift guard), `new_skill.py` (scaffolder), `skill-template/`, `sync_manifest.json`.
- `implementation/` — platform packaging: `gpt/api/` (OpenAI function YAMLs), `gpt/web/` (ChatGPT web doc), `claude/`, `gemini/`.
- `docs/` — architecture, deployment, model, and benchmark docs.
- `docs/RUNBOOK-cpalms.md` — **resuming the CPALMS standards verification** (long-running, spans
  sessions): what is decided, the non-obvious constraints, and the exact commands. Read this before
  touching `tools/cpalms_verify.py` or any `*.cpalms.json` overlay. `python3
  tools/cpalms_verify.py --manifest` regenerates `ledger/cpalms-run-manifest.json`, which is
  authoritative over any standards count written in prose. Currency re-checks run via
  `.github/workflows/currency-recheck.yml` (weekly + manual dispatch; driver `tools/currency_recheck.py`).
- `security/` — security and safety policies.
- `changes/` — changelog and change management.
- `examples/` — cross-skill example library.

## Branching & git
- Develop on the feature branch (currently `claude/educator-tools-k12-plan-f49yju`). **Never push to `main`.**
- Push with `git push -u origin <branch>`; retry network failures with backoff.
- Do not open a PR unless explicitly asked.

## The two-copy / sync rule (important)
Each skill carries byte-identical **synced copies** of shared references (see
`tools/sync_manifest.json`). **Edit the canonical file in `shared/` or `protocol-layer/`, never the
per-skill copy.** After any change to `shared/` or `protocol-layer/`, run the drift guard:

```bash
python3 tools/sync_check.py     # exit 0 = clean; 1 = drift report
```

## Adding a skill
```bash
python3 tools/new_skill.py <skill-name>   # scaffolds from the template + copies synced refs
python3 tools/sync_check.py               # must pass
```
Then edit `SKILL.md` (specific, slightly "pushy", scoped description with a "Do NOT use for…"
clause) and `references/artifact-types.md`. Follow the inner loop in `skill-creator` (draft → evals
→ iterate) for capability skills.

## Local setup (macOS / cross-platform)
Full detail: `docs/DEPLOYMENT_SURFACES.md` (cross-platform notes) + `docs/MACOS.md` (mac-lint + findings
log). The essentials for working here on a Mac:
- **Python:** `/usr/bin/python3` is only the Xcode CLT stub — install a real interpreter (Homebrew /
  python.org). Use `python3 -m pip`, not a bare `pip`. Internal subprocesses must spawn `sys.executable`,
  never the bare name `python3` (enforced by `tools/mac_audit.py` = `sync_check` check 19).
- **Optional deps (PEP 668):** never `pip install` globally on Homebrew Python — install into the
  managed venv: `python3 tools/deps_preflight.py --install <capability>` (or `--install-all`). It uses
  the isolated `.harvest-venv/`, wheels-only, never system Python. `--python-path [capability]`
  prints the venv interpreter to point a Claude Desktop MCP `command`/GUI launch at.
  **One capability opts out: `mcp_server` is `"isolated": true`** (semgrep pins `mcp<2` and a shared venv silently downgraded the SDK), so it installs into `.harvest-venv-mcp_server` and its interpreter is `--python-path mcp_server`, not the bare form.
- **System bins:** `brew install libreoffice tesseract ffmpeg poppler` (LibreOffice may need
  System Settings › Privacy & Security to open on Sequoia). Homebrew prefix is `/opt/homebrew` on
  Apple Silicon, `/usr/local` on Intel — never hardcode it.
- **Encoding:** always pass `encoding="utf-8"` to text `open()`/`read_text()`/`write_text()` (mac-lint
  check 19 enforces it — a non-UTF-8 locale breaks otherwise).

## Non-negotiables (enforced by the drift guard / Quality Gates)
- Every `SKILL.md` references the pipeline (`method.md`), the metadata schema (`metadata-schema.md`),
  and emits `human_review_required`.
- No real student data anywhere — placeholders only.
- Never fabricate standards/citations/results. Nothing is "Final" until it passes the Quality Gates.

## Commit messages
Describe the change and reference the affected protocol/skill. Update `STATE.md` at phase boundaries
and after a skill ships.
