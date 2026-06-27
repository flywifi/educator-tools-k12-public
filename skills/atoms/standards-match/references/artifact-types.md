# Artifact Types — atom-standards-match

## standards-match result

The single artifact produced by this atom is a **standards lookup result** — a structured JSON object
listing the 1–5 most relevant Florida B.E.S.T. standards for a given grade/subject/topic.

**Required fields:**
- `standards`: list of `{code, description, source, confidence}` — may be empty if no match found
- `match_method`: `keyword | L1_cache | uncertain`
- `human_review_required: true`
- `note`: honest explanation when matches are uncertain or empty

**Not produced by this atom:** lesson plans, activities, assessments, or any instructional content.
