# Independent / non-public framework registry (canonical)

Private and homeschool contexts aren't bound to B.E.S.T./NGSSS. This registry lets the ecosystem use
the framework a school/family actually follows, and **cross-map** its requirements to FL (and across
grades/subjects/domains). One JSON per framework under `frameworks/`; mappings under `crosswalks/`.
Used when `context.standards_applicability = school_defined` (and, advisory, for `parent_selected`).

## Registered frameworks (`frameworks/index.json`)
IB · AP (College Board) · Cambridge/AICE · Montessori · Classical (Trivium/CLT) · Faith-based (ACSI).
Each `frameworks/<id>.json` carries the framework's **structure** (programmes/levels, subjects, code
pattern, source) in the normalized standard shape from `standards-framework.md`
(`framework/version/code/grade/band/subject/domain/statement`).

## Status: structure now, codes later (no fabrication)
Each ships as a **stub** (`status: "stub"`, `codes_verified: false`, `standards: []`) — same pattern as
`states.json`. The full standard-by-standard enumeration is a **data task**, populated from each
framework's official source and kept current offline by `standards-updater`. **Never invent codes or
statements** — verify on the source (`protocols/standards-verification.md`).

## Cross-mapping (`crosswalks/<a>__<b>.json`)
A crosswalk maps requirements between two frameworks so coverage can be translated across standards,
grades, subjects, and domains. Each entry: `{subject, from_code, to_code[], relationship:
exact|partial|related, confidence, note/source}`. Shipped entries are **domain-level and illustrative
(`confidence: low`)** until verified on both sources. Query offline with `tools/crosswalk.py`.

## How the standards engine uses this
`standards-framework.md` branches on `standards_applicability`:
- `best_ngsss_apply` → cite + verify FL codes (public/charter/virtual).
- `school_defined` → use the school's `frameworks/<id>.json`; optionally crosswalk to FL to show coverage.
- `parent_selected` → objectives are advisory; offer optional alignment/crosswalk for the family's reference.

## Adding a framework
Add `frameworks/<id>.json` (structure + source), register it in `index.json`, optionally add
`crosswalks/<id>__fl-best.json`, and add its source to `standards-updater` so it stays current.
