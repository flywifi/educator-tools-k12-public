# Skill-health & repair engine (canonical)

Keeps the ecosystem **healthy and consistent** and turns failures into **human-understandable repair
plans**. Adapts patterns that worked in the prior system: a `doctor`-style readiness sweep, an
observability-style trace summary, and a regression mindset (preserve failing cases). It **detects and
proposes**; a human edits/approves — nothing high-stakes auto-applies (`human_review_required: true`).

## Three jobs (`health.py`)
1. **Scan** — every skill (name==folder, `MAINTAINER.md`, synced `references/`, eval cases, routing
   membership) + every shared engine (importable) + routing integrity (no dangling targets) →
   **readiness score + band** (`strong ≥90 · usable_with_warnings ≥70 · partial ≥40 · not_ready`),
   blocking issues, and an operator state + release-gate recommendation.
2. **Diagnose** — read the **audit trail**: the Quality Ledger (`ledger/ledger.json` — non-approved /
   low-composite decisions) and, with `--traces <dir>`, saved decision records / observability traces
   (rolling up `execution_trace` failure classes — `PERMISSION/NOT_FOUND/DEGRADED_SUCCESS/…` — and
   `minority_report` counts). Categorized by a small trace taxonomy (retrieval/validation/error).
3. **Impact** — for a new/renamed skill, list every ecosystem file that must mention it
   (`shared/routing/routing.json`, `ROUTING_MODEL.md`, `routing-map.md`, `STATE.md`, `METRICS.md`,
   `shared/ontology/artifact-types.json`) so docs/routing/ontology never silently drift.

## Repair plan
Ordered, severity-tagged steps (`blocking/warning/info`), each marked **mechanical** (safe to apply) or
**judgment** (needs review). Emitted as JSON and as a plain-language `summary.md`. The human approves;
apply mechanical fixes, then re-run `tools/sync_check.py` + the Quality Gates.

## Use
```bash
python3 shared/health/health.py --summary             # human-readable readiness + repair plan
python3 shared/health/health.py --scan                # full JSON report
python3 shared/health/health.py --impact <skill>      # cross-file update checklist
python3 shared/health/health.py --diagnose --traces runtime/traces   # audit-trail diagnosis
```
Offline/stdlib; reuses the drift guard's invariants and the connectors/records failure taxonomy. Surfaced
through the `skill-health` skill for in-chat use.
