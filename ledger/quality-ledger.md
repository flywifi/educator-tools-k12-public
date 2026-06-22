# quality-ledger.md
## Repository Quality Ledger (append-only)
One row per quality decision. Full decision records live in each artifact's metadata block. Seed
entries = the worked examples bundled with the v1 skills. Immutable once written (QG §94).

| decision_id | date | artifact_id | skill | decision | composite | reference |
|---|---|---|---|---|---|---|
| qr-2026-0001 | 2026-06-20 | lp-grade3-fractions-001 | lesson-planner | Approved | 4.34 | `skills/lesson-planner/examples/grade3-fractions-lesson.md` |
| qr-2026-0002 | 2026-06-20 | ad-grade3-fractions-rubric-001 | assessment-designer | Approved | 4.2 | `skills/assessment-designer/examples/grade3-fractions-rubric.md` |
| qr-2026-0003 | 2026-06-20 | pb-grade3-fractions-slides-001 | presentation-builder | Approved | 4.2 | `skills/presentation-builder/examples/grade3-fractions-slides.md` |
| qr-2026-0004 | 2026-06-20 | ses-accommodations-001 | special-education-support | Approved | 4.1 | `skills/special-education-support/examples/example-accommodations.md` |
| qr-2026-0005 | 2026-06-20 | im-tier2-multiplication-001 | intervention-mtss | Approved | 4.2 | `skills/intervention-mtss/examples/example-tier2-plan.md` |

## Summary (seed)
- Decisions: 5 · Approved: 5 · Rejected: 0 · Approval rate: 100% (seed examples).
- Note: these are bundled gold examples; live usage will add real decisions (incl. Rejected ones,
  e.g., a fabricated-standard case → Rejected per `skills/quality-review/examples/example-evaluation.md`).
