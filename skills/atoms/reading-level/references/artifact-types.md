# Artifact Types — atom-reading-level

## reading-level estimate

The single artifact produced by this atom is a **reading-level estimate** — a structured JSON object
with a grade-band label, Lexile estimate, and a match rating for the target grade.

**Required fields:**
- `estimated_grade_band`: e.g. "3-4" or "6-8"
- `lexile_estimate`: e.g. "720L" or "uncertain"
- `match_for_target`: `below | on_level | above | uncertain`
- `method`: `flesch_kincaid | dale_chall | model_inferred`
- `recommendation`: one-line teacher action
- `human_review_required: true`

**Not produced by this atom:** differentiated rewrites, full document analysis, or student grading.
