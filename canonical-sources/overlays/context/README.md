# Overlays registry

Composable, scoped rule-sets that stack onto the resolved context contract (see
`../overlays.md` for the model and `../overlay.schema.json` for the shape). One JSON per overlay:
`overlays/<scope>/<id>.json`.

```
overlays/
  national/   state/   framework/   county/   district/
  school/     program/ grade/       subject/   classroom/
```

- **scope** — where the rule lives; sets the default merge precedence (`SCOPE_RANK` in `context.py`;
  state/compliance wins on conflict).
- **match** — selectors that activate the overlay (e.g., `{"district":"Orange"}`); `{}` = always.
- **sets** (defaults, weak) · **adds** (accumulate: mandates/notes/sop_refs/exceptions, never lost) ·
  **overrides** (strong; highest precedence wins).

This ships representative **seed** overlays; `county/`, `school/`, `program/`, `classroom/` (and most
`district/`) are intentionally empty — add files as the data is gathered (the architecture supports
school-/county-/framework-/grade-/subject-specific rules without redesign). Never fabricate codes or
mandates — cite a source and mark `status`.

Resolve with: `python3 shared/context/context.py` (demo) or
`import context; context.resolve(school_type=..., district=..., framework=..., subject=..., grade_band=...)`.
