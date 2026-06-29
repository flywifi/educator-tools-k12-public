# MAINTAINER — standards-updater

## Purpose of this maintainer file
`SKILL.md` is the runtime contract; **this file** preserves the non-negotiable behavior, failure
boundaries, and regression expectations for `standards-updater` so a future maintainer keeps the intended control
plane instead of patching symptoms. Canonical procedure: `tools/skill-maintenance.md`.

`standards-updater` is keep the stored Florida (and any-state) corpus current by politely crawling official sources and reporting NEW/CHANGED documents vs stored hashes.

## Non-negotiable invariants
Shared (every skill) — see `CLAUDE.md` "Non-negotiables" and `shared/quality/quality-gates.md`:
- references the pipeline (`references/method.md`) and metadata schema, and emits
  `human_review_required: true`;
- never fabricate standards/codes/citations; **no real student data** — placeholders only;
- resolve the teaching **context first** (`shared/context/`) and carry it across handoffs;
- nothing is "Final" until it passes the Quality Gates.

Skill-specific:
- a POLITE, ROBOTS-RESPECTING, COMPLIANT crawler — NEVER an evasion tool: it respects robots.txt/ai.txt, does NOT rotate/impersonate user agents, does NOT bypass CAPTCHA or rate limits, and backs off rather than bypassing protections
- crawls only public official sources; verifies every candidate change on CPALMS/the source before asserting it
- keeps the offline framework/standard registries updated regularly via `sources.json` monitoring policy

## Known failure modes
- being repurposed into an evasive scraper (a hard NO)
- asserting a standards change from a hash diff without source verification
- ignoring robots.txt or backoff signals

## Fragile fallbacks that must not become defaults
- a content-hash change is a SIGNAL to verify, never a confirmed standards change
- a stale source must not be misread as an outage (or vice-versa)

## Regression cases to preserve
1. a robots-disallowed path is skipped, not crawled
2. a detected change is reported as a candidate pending CPALMS verification
3. the crawler backs off on HTTP 429 / rate limiting

## Approval-gated changes (do not treat as a trivial fix)
Shared: editing a synced reference (`references/method.md`, `references/quality-gates.md` — edit the
canonical source and re-sync), frontmatter keys, or any output schema downstream skills depend on.

Skill-specific:
- the crawler politeness/compliance policy (NEVER weaken)
- `sources.json` coverage and `monitoring_policy`

## Minority-report policy
When sources or interpretations disagree materially, emit a decision record with a minority report via
the canonical resolver (`shared/context/sot_resolver.py`; policy `shared/context/minority-report.md`).
Preserve all four: the **primary interpretation** (`decision_log.chosen_interpretation`), the
**alternates** (`conflicts`, `failed_to_merge`), **why the primary won** (`decision_log.why_it_won`),
and **what evidence would overturn it** (`residual_uncertainty.what_would_resolve_it`). Do not bury
disagreement in prose; do not promote recurring practice to doctrine; **escalate** individual-student/
legal determinations to a human.

## Update checklist (run in order on any change)
1. `SKILL.md` description still specific + scoped, with the "Do NOT use for…" clause intact;
2. `python3 tools/sync_check.py` passes (synced refs byte-identical; frontmatter + resource integrity);
3. every reference named in `SKILL.md` still exists; evals still pass and a case was added for new behavior;
4. context adaptation still correct across school types (`shared/context/`);
5. skill-specific:
   - robots/ai.txt compliance is intact
   - candidate changes are verified on source
   - framework + scholarship + private-school sources are current
6. minority-report behavior unchanged unless explicitly approved; add a regression case for any bug
   that required a behavior change.
