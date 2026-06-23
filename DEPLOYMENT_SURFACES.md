# DEPLOYMENT_SURFACES.md — where the TOS runs (and how data is handled per surface)

The TOS core is **model- and surface-neutral**: Markdown policies/schemas/taxonomies + **stdlib-only**
Python helpers (`shared/connectors/connectors.py`, `shared/students/students.py`,
`skills/meeting-classifier/scripts/classify_meeting.py`, `tools/crosswalk.py`, `shared/context/context.py`)
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
