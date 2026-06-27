# MAINTAINER — output-validator

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `output-validator`. Canonical procedure:
`tools/skill-maintenance.md`. Engines: `tools/validate_outputs.py` (JSON) + `tools/validate_document.py`
(documents). Diagnostic knowledge: `references/format-error-catalog.md`.

## Non-negotiable invariants
Shared (every skill) — `CLAUDE.md` + `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) + metadata schema; emits `human_review_required: true`;
- never fabricate standards/codes; **no real student data** — placeholders only;
- resolve context first (`shared/context/`) and carry it across handoffs; nothing is "Final" until gated.

Skill-specific:
- **Stdlib-first / always runs.** The core checks must work with zero optional libraries; an absent
  checker (jsonschema, Open XML SDK, veraPDF) degrades to a labeled gap — it must NEVER turn into a false
  failure or a crash.
- **Never claim openability from a structural pass.** Report container / schema / openability as separate
  layers (the Open XML SDK "valid ≠ opens" caveat).
- **Validate, never edit.** The skill reports + routes; it does not modify the artifact (that is
  `skill-repair` for mechanical fixes, or the owning skill for judgment).
- **No fabricated diagnosis.** Every finding cites a rule or a format authority; unknowns are gaps.

## Known failure modes
- Treating a stdlib structural pass as proof the file opens in Word/Acrobat (it is not).
- Reporting a skipped check (missing library) as a failure.
- Over-flagging `555` placeholder phones as real PII (keep it a warning, not blocking).

## Fragile fallbacks that must not become defaults
- Schema check skipped because `jsonschema` is absent is acceptable **only when labeled**; never silently
  treat "skipped" as "passed".
- Document validation without LibreOffice/Open XML SDK/veraPDF is structural-only — say so every time.

## Regression cases to preserve
(each maps to an `evals/evals.json` case)
1. A governed artifact with `human_review_required: true` passes.
2. `human_review_required: false` is a blocking failure.
3. An SSN-pattern value anywhere is a blocking `no_real_pii` failure.
4. A valid `.pptx` passes the structural check; a truncated one fails (`bad_zip`).
5. A truncated `.pdf` fails (`pdf_missing_eof`).

## Approval-gated changes (do not treat as a trivial fix)
Shared: synced references (`references/method.md`, `references/quality-gates.md`), frontmatter, output
schema. Skill-specific:
- the rule catalog severities (`references/rule-catalog.md`) and the PII patterns;
- the structural checks / required-parts lists in `tools/validate_document.py`;
- the schema registry in `tools/validate_outputs.py`.

## Minority-report policy
When two readings of a finding are materially plausible (e.g. a borderline "valid but risky" file), emit
a decision record with a minority report via `shared/context/sot_resolver.py`
(`shared/context/minority-report.md`): chosen reading, alternates, why, and what would overturn it. Do
not bury disagreement in prose; escalate individual-student/legal calls to a human.

## Update checklist (run in order on any change)
1. `SKILL.md` description still specific + scoped, with the "Do NOT use for…" clause intact;
2. `python3 tools/sync_check.py` passes;
3. every reference named in `SKILL.md` exists; evals still parse; add a case for any new check;
4. core checks still run with NO optional libraries installed (the always-works guarantee);
5. format-error-catalog citations still resolve to the cited authority;
6. minority-report behavior unchanged unless explicitly approved.
