<!-- last_reviewed: 2026-07-15 | owner: teacher-profile-maintainer -->
# MAINTAINER — teacher-profile

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `teacher-profile` so a future maintainer keeps the intended
control plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- the profile is a **gitignored local store** (`*.local.json` under `shared/context/profiles/`) — never
  commit a real profile; only `teacher.example.json` (placeholders) is committed;
- **no student PII** in a profile; teacher contact is minimum-necessary and local-only;
- **teacher-stated facts outrank crawled/inferred** — never let a crawled guess override what the teacher
  said, and never store a person-specific link without teacher confirmation (person data is the gated
  `shared/staff/` workstream);
- handoffs map to **roles**, not named people, so they survive staff turnover.

## Known failure modes
- writing a real profile to a committed path (must stay `*.local.json`, gitignored);
- silently filling roles/duties from a public site as if teacher-stated (provenance must be `crawled` +
  confirmed);
- person-specific handoff data leaking in before the gated staff workstream + consent exist;
- school link drifting from `canonical-sources/schools/` (use the MSID, not a free-text school name only).
- **profile stranded on one surface:** desktop keeps `teacher.local.json`, the Claude/ChatGPT apps
  keep `my-teacher-profile.md` — a teacher moving between them must not re-do the interview. Bridge
  with `--export-md` / `--import-md`. The embedded fenced ```json``` block (marker `_MD_MARKER`) is
  the exact source of truth; the human-readable text above it is best-effort — never make `from_markdown`
  parse the prose. Import reads `utf-8-sig` so a Windows/Notepad BOM + CRLF round-trips losslessly.
- **`--demo` depends on `teacher.example.json`**, which lives in the gitignored profiles dir — so
  `--demo` fails on a fresh clone until an example exists. Use `--init <answers.json>` or `--import-md`.

## Fragile fallbacks that must not become defaults
- an **empty/partial profile** is acceptable (gaps, not guesses) but must never be silently completed
  with inferred values presented as teacher-stated;
- `--demo`/example data is for testing only and must never be written as a real teacher's profile.

## Regression cases to preserve
<numbered list; each should map to an `evals/evals.json` case>
1. `--demo` builds a valid profile and `--validate` passes.
2. A profile missing `display_name` or with zero roles fails validation (gaps, not guesses).
3. `--register` emits a classroom-scope `sop_ref` + overrides + a role_interaction_map.
4. A handoff missing `counterparty_role` is rejected by validation.
5. `--export-md` then `--import-md` (even after adding a BOM + CRLF to the file) yields a
   byte-identical profile — the desktop↔app round-trip stays lossless.

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.
Skill-specific:
- the profile schema (`shared/context/profiles/teacher.schema.json`) or the context-registration shape
  (sop_refs/overrides/role_interaction_map) — downstream context resolution depends on it;
- the gitignore rules for `*.local.json` profiles (loosening them risks committing real teacher data).

## Minority-report policy
When sources or interpretations disagree materially, emit a decision record with a minority report via
the canonical resolver (`shared/context/sot_resolver.py`; policy `shared/context/minority-report.md`).
Preserve all four:
- the **primary interpretation** selected (`decision_log.chosen_interpretation`);
- the **alternate** plausible interpretations (`conflicts`, `failed_to_merge`);
- **why the primary won** (`decision_log.why_it_won`);
- **what evidence would overturn it** later (`residual_uncertainty.what_would_resolve_it`).

Do **not** bury disagreement in prose; do not promote recurring practice to doctrine; **escalate**
individual-student/legal determinations to a human.

## Update checklist (run in order on any change)
1. `SKILL.md` description still specific + scoped, with the "Do NOT use for…" clause intact;
2. `python3 tools/sync_check.py` passes (synced refs byte-identical; frontmatter + resource integrity);
3. every reference named in `SKILL.md` still exists; evals still pass and a case was added for new behavior;
4. context adaptation still correct across school types (`shared/context/`);
5. skill-specific: profile stays gitignored; no student PII; teacher-stated outranks crawled; handoffs are
   role-based; `--validate`/`--register` still behave as the regression cases expect;
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
