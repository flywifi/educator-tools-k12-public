# Context model (canonical)

The dimensions of a teaching context, how they're resolved, and how conflicts are settled.

## Dimensions
- **state** — FL (only populated state; others extensible via the same pattern).
- **district** — one of the 67 county LEAs (`florida-districts.json`); carries rules/norms (stubs).
- **school** + **school_type** — the school and its type (`school-types.json`), which selects the
  **exception rule-set**.
- **program(s)** — general · ese · ell · gifted · cte · ap · ib · aice · dual_enrollment · title_i ·
  acceleration · intervention_mtss (a context can hold several).
- **subject** · **grade** (individual K,1…12 — always carried) · **grade_band** (K-2/3-5/6-8/9-12,
  derived from grade). 8th-grade standards/testing differ from 6th/7th, so the individual grade is kept.
- **course** (specific CPALMS / FLDOE Course Code Directory number) · **course_level** (remedial ·
  standard · advanced · gifted · honors · ap · ib · aice · dual_enrollment).
- **instructional_model** — traditional · blended · hybrid · virtual_synchronous ·
  virtual_asynchronous · self_paced.
- **calendar** — semester · quarter · trimester · year_round · block.
- **standards_applicability** — derived from school_type: `best_ngsss_apply` (public/charter/virtual),
  `parent_selected` (home ed), `school_defined` (private scholarship).
- **mandates[]** — administrative mandates in force, each scoped (state/district/school/classroom).
- **sop_refs[]** — uploaded SOP files (see `sop-model.md`), each scoped.

## Authority precedence (conflict resolution)
Conflicts are settled by an ordered `authority_precedence`. Two common orderings:
- **Compliance/mandates (default):**
  `state → district → school → grade → subject → course (CPALMS #) → course_level → classroom/teacher`
  — higher authority wins (e.g., a state graduation rule overrides a school preference), then
  more-specific scopes break ties. `county` sits with `district`; `grade_band` is a convenience just
  below the individual `grade`; `framework` applies where a school adopts one; `national` is the
  baseline. The full default order is in `context.DEFAULT_PRECEDENCE` / `SCOPE_RANK`.
- **Instructional style:** may invert toward `classroom → school → district` — a teacher's
  research-based instructional choices are theirs within policy. Callers pass a custom order when the
  decision is pedagogical rather than compliance-bound.

`context.resolve_conflict(context, candidates)` picks the winner by the active precedence. The
precedence itself is part of the contract, so the choice is explicit and auditable.

## Overrides (control-plane resets)
An explicit instruction to prefer/avoid a rule or source is logged in `overrides[]`
(`context.apply_override`) — never applied silently. An override is a reset, not a soft preference:
downstream skills must honor the latest override and record it. Prior evidence/provenance is kept.

## School-type exceptions
`school_type_rules(type)` returns `overrides_baseline` (what changes vs. traditional public) and
`sop_overrides` (which SOP categories this type replaces). This is how the same request yields
different governed behavior in a charter vs. a district-virtual vs. a home-ed context.

## Overlays (composable scoped rules)
Beyond the single resolved contract, rules can be layered as **overlays** at any scope (state, county,
district, school, framework, grade, subject, program, classroom). `context.resolve(selectors)` stacks
all matching overlays by precedence — `sets` (defaults) + `adds` (accumulate mandates/notes/SOPs) +
`overrides` (state/compliance wins) — and records `overlays_applied`. This is how the system stays
adaptable/translatable: new school-/county-/framework-/grade-/subject-specific rules are added **as
data** (`overlays/<scope>/<id>.json`) without code or skill changes. Full model: `overlays.md`.

## Invariants
1. Context is resolved **first** and travels with the work (into metadata + handoffs).
2. Unknown dimensions are explicit nulls/stubs — never guessed.
3. `human_review_required` is always true (decision support, not a compliance ruling).
4. Overrides are logged; authority precedence is explicit.
5. Standards applicability follows school type — home-ed/private contexts do **not** silently inherit
   the B.E.S.T./NGSSS mandate.
