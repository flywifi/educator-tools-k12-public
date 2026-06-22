# workflows.md
## Cross-skill workflows (teacher-core orchestration)
How `teacher-core` handles a request that needs **several artifacts**. The pipeline
(`method.md`) runs once per artifact; `teacher-core` sequences the skills and assembles one
coherent deliverable, each piece gated by `quality-review`.

## How to orchestrate
1. **Decompose** the request into artifacts and map each to a skill (`routing-map.md`).
2. **Order** them so outputs feed inputs (plan the lesson before its slides; design the unit before
   its assessments).
3. **Share context** across steps — the same grade band, subject, standard, and assumptions flow to
   every skill so the bundle is internally consistent (one standard set, one persona, one voice).
4. **Gate each artifact** with `quality-review`; nothing in the bundle is "Final" until each piece
   passes (or is fixed/regenerated — `protocols/failure-recovery.md`).
5. **Assemble** the bundle with a short cover summary + a combined metadata block listing every
   artifact's decision.

## Named workflows
- **Teaching bundle** — lesson + aligned exit ticket/assessment + slide deck (+ optional parent
  note). Skills: `lesson-planner` → `assessment-designer` → `presentation-builder`
  (→ `family-communication`). All share one standard/objective. See
  `examples/grade3-fractions-bundle.md`.
- **Unit launch** — unit plan + pacing slice + a summative assessment + a family newsletter. Skills:
  `curriculum-mapping` / `lesson-planner` → `assessment-designer` → `family-communication`.
- **Support bundle** — an accommodation plan + a tiered intervention + a progress-monitoring tool for
  the same area of need. Skills: `special-education-support` + `intervention-mtss` (keep MTSS vs.
  IEP/504 distinct). Placeholders only.
- **Initiative rollout** — implementation plan + walkthrough tool + a coaching/PD resource. Skills:
  `school-administration` → `professional-learning`.

## Consistency rules
- One verified standard set across the bundle (re-cite, don't re-derive differently per piece).
- One persona + grade band + reading level; consistent vocabulary.
- If two pieces conflict, apply `protocols/conflict-protocol.md`.
- Every piece keeps `human_review_required: true`; the bundle is decision support, not final.
