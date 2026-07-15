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
- **Python command:** internal calls use `sys.executable` (safe). But doc/command lines say
  `python3`, which many **Windows** installs don't provide — use `py -3 …` or `python …` there. The
  assistant driving the tools should pick the platform interpreter, not literally `python3`.
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
