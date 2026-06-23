# Overlays — composable, scoped context rules (canonical)

The overlay system generalizes the context contract into **stackable, scoped rule-sets** so the
ecosystem is adaptable, repeatable, and translatable: state, county, district, school, framework,
grade, subject, program, classroom rules can each be added **as data** and composed at resolve time —
without changing code or skills. Implemented in `context.py` (`resolve`, `load_overlays`); shape in
`overlay.schema.json`; registry in `overlays/`.

## What an overlay is
```json
{ "scope": "district", "id": "orange", "match": {"district": "Orange"},
  "sets": {…}, "adds": {"notes": [...], "mandates": [...]}, "overrides": {…},
  "source": [...], "status": "seed|stub|populated" }
```
- **scope** — `national · state · framework · county · district · school · program · grade · grade_band ·
  subject · course · course_level · classroom`. Sets the default merge precedence (`SCOPE_RANK`);
  state/compliance ranks highest, then more-specific scopes
  (`state → district → school → grade → subject → course → course_level → classroom`). `grade` is the
  individual grade level and ranks above `grade_band`.
- **match** — selector predicate; the overlay activates when every key equals the `resolve()` selector
  (case-insensitive). `{}` = always applies.
- **sets** — default field values, applied only if the field is still empty (weak).
- **adds** — list contributions that **accumulate and are never lost** (mandates, sop_refs, notes,
  exceptions, frameworks).
- **overrides** — forced field values; the highest-precedence overlay wins on conflict (strong).

## How resolution works (`context.resolve(selectors)`)
1. Build the base context (`build_context`) from school_type + district + the other selectors.
2. Load every overlay under `overlays/`, keep those whose `match` ⊆ selectors, sort by precedence
   (ascending; higher wins on `overrides`).
3. Merge each: `sets` (fill-if-empty) → `adds` (extend lists) → `overrides` (set).
4. Record `overlays_applied[]` (id, scope, precedence) — the resolution is explicit and auditable.

Example: `resolve(school_type="charter_public", district="Orange", framework="IB", subject="Mathematics",
grade="8")` stacks the IB (framework), Mathematics (subject), grade-8 (grade), Orange (district), and
FL (state) overlays — the band `6-8` is derived from grade `8`, the IB overlay flips
`standards_applicability` to `school_defined`, the grade-8 overlay adds the 8th-grade testing notes
(distinct from 6/7), and notes accumulate from all of them.

## Precedence — compliance vs instructional style
Default `SCOPE_RANK` makes **state/law win** on conflicting `overrides` (compliance). The contract's
`authority_precedence` (used by `resolve_conflict`) governs case-by-case decisions and can be inverted
toward `classroom` for **instructional-style** choices (teacher discretion within policy). `adds`
(mandates, SOPs) accumulate regardless of precedence — a mandate is never dropped.

## Adding overlays (fill-in over time)
Drop a JSON in `overlays/<scope>/<id>.json` and set `match`. The seeds cover state/framework/grade/
subject/district; `county/`, `school/`, `program/`, `classroom/` and most `district/` are intentionally
empty — add them as the data is gathered (sources in `populate-checklist.md`). Offline + updatable;
`standards-updater` can watch the cited sources. Never fabricate codes or mandates — cite a `source`
and mark `status`.
