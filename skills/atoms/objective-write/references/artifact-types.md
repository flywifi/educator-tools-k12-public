# Artifact Types — atom-objective-write

## measurable objectives

The single artifact produced by this atom is a **set of measurable learning objectives** — a
structured JSON list, each with a Bloom's level, standard alignment, and action verb.

**Required fields:**
- `objectives`: list of `{text, bloom_level, standard_code, verb}`
- `human_review_required: true`

**Not produced by this atom:** activities, assessment items, or differentiated content.
