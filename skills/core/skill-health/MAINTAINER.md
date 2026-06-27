# MAINTAINER — skill-health

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `skill-health` so a future maintainer keeps the intended
control plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`. Engine:
`shared/health/health.py`; prose: `shared/health/health-model.md`.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- Governs the **system**, not classroom artifacts — never authors lessons/assessments or scores a single
  classroom artifact (that is `quality-review`).
- **Detect + propose only.** Diagnostics and repair plans are advisory; the human edits/approves and
  nothing high-stakes is auto-applied. Mechanical fixes are applied only after approval, then
  `tools/sync_check.py` + the Quality Gates re-run.
- **Never invent a cause.** Every diagnosis cites the ledger/trace evidence it actually read; missing
  evidence is reported as a gap, not guessed.

## Known failure modes
- Treating a clean `--scan` as proof of correctness (readiness checks structure/imports, not classroom
  quality — that is `quality-review`).
- Over-reading ephemeral runtime traces as durable truth (they exist only when saved via `--traces`).
- Auto-applying a "mechanical" fix that was actually judgment (e.g. editing a synced reference).

## Fragile fallbacks that must not become defaults
- Running `--diagnose` with no `--traces` gives ledger-only findings; acceptable as a labeled partial
  view, never presented as a full diagnosis of a runtime failure.
- An empty repair plan means "no issues found by these checks", not "the ecosystem is certified".

## Regression cases to preserve
(each maps to an `evals/evals.json` case)
1. A clean repo scans to band `strong` with zero blocking issues.
2. Impact analysis for a skill missing from the ontology lists that file under `update_needed_in`.
3. `--diagnose --traces` rolls up `execution_trace` failure classes (e.g. `PERMISSION`) + minority reports.
4. A dangling routing target (route to a non-existent skill) is reported as a blocking issue.

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.
Skill-specific:
- the readiness scoring weights / band thresholds in `shared/health/health.py`;
- the `ECOSYSTEM_REFS` impact-target list (changing it changes what "drift" means);
- promoting any repair step from `judgment` to `mechanical` (safe-to-auto-apply) classification.

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
3. every reference named in `SKILL.md` still exists; evals still parse and a case was added for new behavior;
4. `python3 shared/health/health.py --summary` still runs and reports the expected bands;
5. skill-specific: readiness weights, `ECOSYSTEM_REFS`, and mechanical/judgment tags reviewed if touched;
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug fix.
