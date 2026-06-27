# artifact-types.md
## Artifacts produced by this skill

`teacher-profile` produces operating-context artifacts (not instructional materials). Each ends with the
metadata block and `human_review_required: true`. No real student data — placeholders only.

### Teacher operating profile
- Purpose: one teacher's self-described roles, duties, handoff/role-interaction map, and preferences —
  the gitignored local source of truth other skills adapt to.
- Required elements: `teacher.display_name`; ≥1 role with provenance/confidence; (as available) duties,
  handoffs (each with what/direction/counterparty_role), meetings, preferences; `human_review_required`.
- Standards: n/a (operating context, not standards-aligned content); school link resolves to FLDOE MSID
  via `shared/schools/`.
- Differentiation: n/a directly; the profile's preferences/overrides feed differentiation in other skills.
- Template: `shared/context/profiles/teacher.example.json` (shape); schema `teacher.schema.json`.
- Validation: `scripts/profile_wizard.py --validate` (required fields, handoff shape, `human_review_required`);
  no student PII; teacher-stated facts marked as such.

### Context registration fragment
- Purpose: the contribution merged into `shared/context/` — a classroom-scope `sop_ref` to the profile,
  `overrides[]` from preferences, and a `role_interaction_map` for routing skills.
- Required elements: `sop_refs[]` (id/scope/path), `overrides[]`, `role_interaction_map`, `scope: classroom`,
  `human_review_required`.
- Standards: n/a.
- Differentiation: carries the teacher's defaults (e.g. reading-level) into downstream generation.
- Template: emitted by `scripts/profile_wizard.py --register`.
- Validation: scopes are valid context scopes; precedence resolved by the context engine; teacher-stated
  outranks crawled.
