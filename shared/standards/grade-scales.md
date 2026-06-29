# Grade scales — translating "what an A means" across contexts (canonical)

Different schools and frameworks grade differently: a 10-point letter scale, a tighter 7-point scale,
standards-based 4-3-2-1, GPA points, IB 1-7, AP exam 1-5. This registry lets the ecosystem **translate
a grade/score from one scale to another** — e.g., a transfer student, a private-to-public move, or an
IB/AP transcript — without pretending the conversions are universal. Files live in
`shared/standards/grade-scales/<id>.json` (registry) and `shared/standards/crosswalks/grade-scales.json`
(the cross-mapping); query with `tools/crosswalk.py --grade`. Companion to `crosswalks.md`.

## The honest part (no false equivalence)
**Most cross-scale conversions are institution-dependent and are NOT 1:1.** An "A" is 90-100 on a
10-point scale but only 90-92 would be a "B" on a 7-point scale; IB-to-letter and SBG-to-letter tables
are set by each school/college; an AP exam score is *not* a course letter grade at all. So every
mapping carries:
- **`relationship`** — `exact | partial | related | none`;
- **`coverage`** — how much carries over: `full | most | partial | minimal | none`;
- **`confidence`** — `high | medium | low`;
- **`institution_dependent`** — when true, the conversion must be confirmed on the school/district
  policy before it is relied on (this is exactly the kind of "operationally clear but formally
  underdefined" claim that triggers the minority-report discipline — `shared/context/minority-report.md`).

Never assert a conversion you cannot cite (`protocols/standards-verification.md`); offer it as the
institution's stated table, flagged.

## Scale file shape
```json
{ "id": "traditional-10pt", "type": "letter|points|exam|sbg|gpa",
  "bands": [ {"grade":"A","min":90,"max":100,"meaning":"excellent"} ],
  "institution_dependent": true, "source": ["…"], "status": "seed", "note": "…" }
```
(SBG/points/exam scales use `levels`; GPA uses `points`.)

## Translating a grade
```bash
python3 tools/crosswalk.py --grade-scales                       # list scales
python3 tools/crosswalk.py --grade A --from traditional-10pt --to gpa-4pt
```
The tool prints the mapping with its relationship/coverage/confidence and a reminder that the result is
institution-dependent.

## Maintenance
Offline JSON, kept current by `standards-updater` (grade-scale + framework + scholarship sources are in
its `monitoring_policy`). Add a scale by dropping `grade-scales/<id>.json` and listing it in
`index.json`; add a conversion as a verified entry in `crosswalks/grade-scales.json`.
