# Artifact Types — atom-assessment-item

## single assessment item

The single artifact produced by this atom is **one assessment item** — a structured JSON object
with stem, options (for MC), answer key, DOK level, and distractor analysis.

**Required fields:**
- `item`: `{stem, type, dok_level, options, answer_key, rationale, distractor_analysis}`
- `human_review_required: true`

**Not produced by this atom:** full assessments, rubrics, or activities.
