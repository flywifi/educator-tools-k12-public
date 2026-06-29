# Crosswalks — translating requirements across frameworks (canonical)

Crosswalks let the ecosystem answer "what does this requirement in framework A correspond to in
framework B?" across **standards, grades, subjects, and domains** — e.g., an IB or AP school showing
B.E.S.T. coverage, or a homeschooler mapping a chosen curriculum to FL for reference. Files live in
`frameworks`' sibling dir `crosswalks/<a>__<b>.json`; query with `tools/crosswalk.py`. Companion to
`frameworks.md`.

## File shape
```json
{ "from_framework": "AP", "to_framework": "FL-BEST-Math", "status": "stub",
  "entries": [
    { "subject": "Mathematics", "from_code": "AP Calculus AB", "to_code": ["MA.912.C.*"],
      "relationship": "exact|partial|related|none",
      "coverage": "full|most|partial|minimal|none",
      "confidence": "high|medium|low",
      "note": "source / caveat" } ] }
```
`coverage` records **how much** of the from-requirement carries over. Contract:
`shared/standards/crosswalks/crosswalk.schema.json` (also covers the grade-scale crosswalk,
`kind: grade_scale_crosswalk`). To translate **grades** (what an "A" means across scales) see
`shared/standards/grade-scales.md` + `tools/crosswalk.py --grade`.

## Discipline (no false equivalence)
- Shipped entries are **domain-level and illustrative (`confidence: low`)** until verified on **both**
  source frameworks — they are starting points, not certified equivalences.
- Use `relationship` honestly: `exact` only with a verified 1:1 source mapping; otherwise `partial`/
  `related`. Record a `note`/source. Never assert an equivalence you can't cite
  (`protocols/standards-verification.md`).
- Crosswalks are **decision support**: a generated artifact still cites the school's own framework as
  primary; the crosswalk is supplementary coverage information.

## Maintenance
Offline JSON, populated and kept current by `standards-updater` (framework sources added to its
`monitoring_policy`). Add a crosswalk by dropping `crosswalks/<a>__<b>.json` and listing real,
verified entries as they're confirmed.
