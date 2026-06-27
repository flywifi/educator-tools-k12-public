# MAINTAINER — feed-curator

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `feed-curator` so a future maintainer keeps the intended
control plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- **Only mechanically-safe repairs auto-apply** (remove a confirmed 404/410, follow a verified
  301/302). New feeds, removals beyond dead links, and relabels are human-approved proposals.
- **Every** catalog change — auto or approved — is appended to `ledger/feeds-change-log.json` with
  before/after and is reversible via `--revert`. Never edit the catalog without logging.
- Only `tier: canonical` / `authority: primary` confirms a change; secondary/news is discovery-only;
  the `product_updates` layer stays OFF unless a teacher enables it.
- Never fabricate a feed URL or a `verified: true` status; a feed you cannot reach stays
  `verified: false`. Report egress/policy-blocked hosts; do not route around them.

## Known failure modes
- Treating a `news_teacher_student` (secondary) item as a canonical change — must route to "verify on
  the primary source".
- Auto-removing a feed that is merely **unreachable** (transient/egress) rather than a confirmed
  404/410 — only `removed_404` is a safe removal; `unreachable` is not.
- Following a redirect chain to an off-domain or unrelated host — the redirect probe records the target
  for human sanity-check; do not blindly trust a 30x `Location`.
- Adding a discovered candidate without classifying its `authority`/`tier`/`purpose`.

## Fragile fallbacks that must not become defaults
- Offline / egress-blocked runs degrade to age-only triage and `unreachable`/`uncertain`; that is a
  clearly-labeled fallback, never a substitute for a real validation, and must not silently auto-apply
  anything.
- The stdlib ElementTree parser is a fallback for `feedparser`; acceptable, but format-ambiguous feeds
  should be flagged `uncertain` for the curator, not silently dropped.

## Regression cases to preserve
<numbered list; each should map to an `evals/evals.json` case>
1. A confirmed `removed_404` feed auto-applies a `remove`, logs it `mode: auto`, and `--revert` restores it.
2. An `unreachable` feed does NOT auto-remove (only `removed_404` is safe).
3. A mislabeled feed (bad `authority`, missing `purpose`) is flagged but only relabeled on approval.
4. Discovery from an authoritative page surfaces candidates as proposals (never auto-added); a
   policy-blocked host is reported, not bypassed.

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.
Skill-specific:
- Changing what counts as a `safe_repair` (the auto-apply set) — widening it is a control-plane change.
- Changing the audit-log schema (`ledger/feeds-change-log.json`) or the catalog tier vocabulary.
- Enabling the `product_updates` layer by default.

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
5. skill-specific: `seed_curator.py --validate/--propose/--apply/--revert` still behave; the audit log
   records every change; only `removed_404`/verified-redirect auto-apply; egress-blocked hosts reported;
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
