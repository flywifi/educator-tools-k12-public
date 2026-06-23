# Source of Truth — the canonical resolver (canonical)

A single, auditable way to answer *"which source decides this, and what happens when sources disagree?"*
The resolver classifies the claim, picks the authoritative source, chooses one interpretation, and
emits a **decision record with a minority report** so the path to every decision is reconstructable.

Adapted from the operating-reference / control-plane pattern: decide **source roles** first (what each
source is *allowed to prove*), resolve by authority, and **make uncertainty visible** instead of hiding
it. Stdlib, fully offline.

## Pieces
- **`source-roles.json`** — for each *claim type* (standard_code, course_code, assessment_requirement,
  graduation_promotion_requirement, compliance_mandate, operating_rule, instructional_method,
  iep_504_requirement, eligibility_scholarship, accreditation_requirement): what proves it, the ranked
  authoritative sources, and **what must NOT be used to prove it**. Offline data; filled in over time.
- **`sot_resolver.py`** — `resolve(claim, claim_type, candidates, context)` → a decision record.
- **`decision.schema.json`** — the decision-record + minority-report contract.
- **`minority-report.md`** — when/how to preserve disagreement (buckets, triggers, hard rules).

## How resolution works
1. **Classify the claim** (`claim_type`) → look up its source role in `source-roles.json`.
2. **Rank each candidate** by authority:
   - an explicit *authoritative source* for this claim type wins (respecting
     `standards_applicability` — e.g., `framework_registry` only counts when `school_defined`);
   - else a claim type's *compliance ladder* (statute > state rule > FLDOE guidance > district > school
     > classroom);
   - else fall back to the context's **`authority_precedence`** by scope (the ordered
     state → district → school → grade → subject → course → course_level → classroom ranking).
3. **Choose the winner** (highest authority, verified). **Fabrication is never a source** — an invented
   code/citation is excluded and logged as residual uncertainty; it can never win.
4. **Build the minority report** — `conflicts` (meaningful disagreements), `failed_to_merge` (canon vs
   current practice / provisional update — never blended), `residual_uncertainty` (low-confidence or
   unverified).
5. **Escalate** individual-student / legal determinations (IEP/504, eligibility, graduation/promotion,
   compliance mandates) to a human — they are never auto-decided.

## Relationship to the rest of the context engine
- **`authority_precedence`** (in `context.py`) orders *scopes*; **source roles** order *sources* for a
  specific claim. The resolver uses source roles first, then precedence as the fallback — both are part
  of the auditable contract.
- **`resolve_conflict()`** is the lightweight scope-only chooser; **`sot_resolver.resolve()`** is the
  full claim-aware resolver that also produces the minority report. Use the resolver whenever a
  disagreement is material.
- **Overrides** (`apply_override`) are logged control-plane resets; an override becomes a high-rank
  candidate, and the prior interpretation is preserved in the minority report — never silently dropped.

## Governance
The decision record is recorded in artifact metadata (`protocols/metadata-schema.md`) and the conflict
procedure is canon in `protocols/conflict-protocol.md`. Quality Gates treats a *fabricated* source as a
critical failure in every context (`protocols/quality-gates.md` §37).

## Worked example
`python3 shared/context/sot_resolver.py` resolves a district pacing guide (**canon**) against a
long-standing classroom routine (**current practice**): the district guide wins, but the routine is
preserved in `conflicts` + `failed_to_merge` (canon and practice are not blended) with
`minority_report_required: true`.
