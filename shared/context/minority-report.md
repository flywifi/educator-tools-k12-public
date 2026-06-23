# Minority Report Policy (canonical)

The ecosystem must **preserve disagreement in a structured way** whenever ambiguity materially affects
what an artifact says or does. A minority report is **not optional** when disagreement changes which
standard/rule applies, who is responsible, what scope is in force, or how a policy is interpreted. It
lives in the decision record (`decision.schema.json`), emitted by the source-of-truth resolver
(`sot_resolver.py`) — never buried in prose caveats.

## Required buckets (decision record)

### `decision_log` — the chosen interpretation and why it won
`chosen_interpretation` · `why_it_won` · `winning_scope` · `winning_source` · `supporting_claim_ids` ·
`supporting_source_ids` · `confidence`.

### `conflicts` — direct disagreements between meaningful sources
`source_a` · `source_b` · `conflict_summary` · `materiality` (high/medium/low) · `affected_claim_ids`.

### `failed_to_merge` — plausible interpretations that must NOT be blended
`interpretation_a` · `interpretation_b` · `why_not_mergeable` · `affected_claim_ids`.
(Canonical example: district/school **canon** vs. observed **current practice**, or **older canon** vs.
a **provisional teacher-/admin-directed update**.)

### `residual_uncertainty` — open ambiguity that doesn't block the answer but still matters
`statement` · `what_would_resolve_it` · `impact_if_wrong`.

## Trigger conditions (emit a minority report when ANY is true)
- canonical SOP/policy and current-practice evidence diverge;
- a user-directed **provisional** update conflicts with older canon;
- multiple strong sources disagree (e.g., district pacing vs. school SOP);
- a term is operationally clear but formally underdefined (e.g., "mastery", "on pace");
- authority matters but the **scope** of that authority isn't confirmed (who may set this rule?);
- ownership/responsibility/workflow can plausibly be read more than one way (e.g., who administers an
  assessment, who signs an accommodation).

### Usually triggers in K-12
- a district pacing guide conflicts with a long-standing classroom routine;
- a B.E.S.T./NGSSS alignment is defensible two ways with different downstream tasks;
- a private school's framework obligation is read against an assumed public-school rule;
- a home-ed family's stated objective is mapped (optionally) to a state code that isn't mandated;
- a provisional "we're piloting this" change is used before the SOP is rewritten.

## Hard rules
- **Do not** use the minority-report structure to silently rewrite canon.
- **Do not** hide material disagreements in prose-only caveats.
- **Do not** promote repeated practice into doctrine just because it keeps appearing.
- **Fabrication is never a source.** An invented standard/code/citation is excluded from candidates and
  noted as residual uncertainty — it can never win (Quality Gates §37; always a critical failure).
- When the main answer chooses one interpretation, **preserve the meaningful alternative** if it would
  change downstream work, and **escalate** individual-student/legal determinations (IEP/504,
  eligibility, graduation/promotion, compliance mandates) to a human — never auto-decide them.

## How it's produced
`sot_resolver.resolve(claim, claim_type, candidates, context)` ranks candidates by
`source-roles.json` (what each source may prove) then by the context's `authority_precedence`, writes
`decision_log`, and fills `conflicts` / `failed_to_merge` / `residual_uncertainty`. The result is
recorded in artifact metadata (`protocols/metadata-schema.md`) and governed by
`protocols/conflict-protocol.md`.
