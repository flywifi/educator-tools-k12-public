# Artifact Types — atom-quality-check

## quality gate result

The single artifact produced by this atom is a **quality gate check result** — a structured JSON
object with pass/fail/warn status, a finding, and a corrective action.

**Required fields:**
- `gate`: which gate was checked
- `result`: `pass | fail | warn`
- `finding`: what was found
- `corrective_action`: what to fix (empty string if passing)
- `human_review_required: true`

**Not produced by this atom:** content generation, differentiation, or multi-gate sweeps.
