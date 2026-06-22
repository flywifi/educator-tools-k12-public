# context — teaching-context & SOP layer (canonical)

**Source of truth** for adapting the ecosystem to *where and how a teacher works*. Florida is vast and
uneven: 67 county districts, plus charter, magnet, district-run virtual, statewide FLVS, home
education, and private-scholarship contexts — each with different governance, mandates, calendars,
and standards applicability. This layer lets a teacher/admin declare (and upload SOPs for) their
context **once**, and every skill then adapts and carries that context through its handoffs.

> Architecture pattern: a **control-plane "operating reference."** Resolve the operating context
> *first*, apply the school-type **exception rule-set**, resolve **authority precedence** + logged
> **overrides**, and emit a **context contract** that downstream skills consume — they adapt to it,
> they don't re-derive it. (Adapted from an operating-reference/route-plan skill pattern.)

## Files
| File | What it is |
|---|---|
| `florida-districts.json` | **Log of all 67 FL county districts** (LEAs) — fillable stubs for rules/norms/superintendent/district-run virtual school; Orange/OCPS populated as the worked example. |
| `school-types.json` | School-type **taxonomy + exception rule-sets** (traditional/magnet/charter/district-virtual/FLVS/home-ed/private-scholarship): how each overrides the baseline. |
| `context.schema.json` | The **context contract** envelope (machine-readable). |
| `context.py` | Resolver: build/validate a context, apply school-type exceptions, resolve precedence + overrides. Stdlib. |
| `context-model.md` | The dimensions, authority-precedence, and override model. |
| `sop-model.md` | How teachers **upload/update SOP files** and how they map into the contract. |

## The context contract (what flows everywhere)
`state · district · school · school_type · program(s) · subject · grade_band · instructional_model ·
calendar · standards_applicability · mandates[] · sop_refs[] · authority_precedence[] · overrides[]`
(+ `confidence`, `human_review_required: true`). Full shape: `context.schema.json`.

## How it changes the contracts & handoffs
- **Metadata contract:** every artifact's metadata block gains a `context` envelope
  (`protocols/metadata-schema.md`) — so an artifact records the district/school-type/mandates it was
  built for, and is auditable against them.
- **Routing (teacher-core):** the hub **resolves context first** (operating-reference), then routes;
  the resolved contract is passed to capability skills and **preserved across handoffs** (a skill
  never silently changes the context; overrides are logged).
- **Generation:** skills adapt to the contract — e.g., `standards_applicability = parent_selected`
  (home ed) makes standards alignment advisory not mandatory; `school_type = charter_public` pulls in
  governance SOPs; `instructional_model = virtual_*` changes pacing/attendance assumptions.

## School-type exceptions (why one size never fits)
`traditional_public` is the baseline; every other type declares `overrides_baseline` + `sop_overrides`
in `school-types.json`. Examples: **charter** → independent board governance + sponsor reporting;
**district-virtual / FLVS** → delivery/attendance/pacing; **home education** → annual evaluation
instead of statewide assessment, standards optional; **private-scholarship** → school-defined
curriculum + scholarship accountability. A district like **Orange (OCPS)** runs its **own** virtual
school (OCVS), so a teacher there can be simultaneously district + virtual — the contract carries both.

## Status (architecture first; rules filled in later)
The **architecture is in place** and the 67-district log exists. District `rules_and_norms`,
superintendents, named district virtual schools, charter directories, and most school-type specifics
are **fillable stubs** — to be populated per district/source over time. Authoritative sources are
recorded in the JSON (FLDOE school-choice/virtual-ed/charter/scholarship pages, FAC 6A, FSBA,
superintendents directory). Nothing here is fabricated; unknowns are explicit stubs.
