# Context adaptation (canonical)

How a skill's **Generation** adapts to the resolved context contract (`context.schema.json`). Baseline
= traditional-public Florida with B.E.S.T./NGSSS; every deviation comes from the school-type
**exception rule-set** (`school-types.json`), the other context dimensions, and uploaded **SOPs**
(`sop-model.md`). Where an SOP is silent, the baseline applies. SOPs/mandates never override state law
(authority precedence); conflicts surface, they don't get hidden.

## By context dimension
- **school_type** — apply `overrides_baseline` + `sop_overrides`. charter → independent-board
  governance + sponsor reporting; district-virtual / FLVS → delivery/attendance/pacing; home-education
  → annual evaluation instead of statewide assessment, standards advisory; private-scholarship →
  school-defined curriculum + scholarship accountability.
- **standards_applicability** — `best_ngsss_apply` (cite + verify codes) · `parent_selected`
  (alignment advisory; offer, don't mandate) · `school_defined` (use the school's framework).
- **instructional_model** — traditional vs blended/hybrid vs virtual_synchronous/asynchronous vs
  self_paced changes pacing, attendance/engagement assumptions, synchronous-time expectations, and
  proctoring notes.
- **calendar** — semester/quarter/trimester/year_round/block changes unit length + pacing math.
- **program(s)** — ese → IEP/accommodations lens; ell → WIDA/ELD supports; cte → framework + industry
  cert; ap/ib/aice → exam alignment; dual_enrollment → postsecondary articulation; title_i / mtss →
  intervention emphasis.
- **mandates / SOPs** — apply district/school mandates and SOP-driven templates, grading policy,
  communication rules, pacing guides; record which SOP shaped the output (provenance).

## By skill family
- **lesson-planner / assessment-designer / presentation-builder** — adapt pacing + delivery to
  instructional_model + calendar; standards applicability per school_type; use SOP templates/grading.
- **curriculum-mapping / pacing** — anchor to the district pacing SOP + calendar; flag where a
  school-type override (charter/virtual) changes sequence.
- **special-education-support / intervention-mtss** — drive off program (ese/ell/mtss) + the school's
  IEP/MTSS SOPs; keep team/legal review and placeholders-only.
- **family-communication** — follow the school's communication-policy SOP (channels, languages,
  cadence); privacy first.
- **school-administration** — governance model by school_type (charter independent board + governance
  training vs district board); accountability (school grades) per context.
- **standards-updater** — which standards/assessments apply depends on school_type (home-ed/private
  are not bound to B.E.S.T./NGSSS).

## Invariants
1. Resolve context first; adapt, don't re-derive.
2. School type governs standards applicability — never silently force B.E.S.T./NGSSS onto home-ed/private.
3. SOPs configure behavior but cannot override state law/rule (precedence) or the Quality Gates.
4. Record the context envelope + which SOP/mandate shaped the artifact; `human_review_required: true`.
