# Artifact Types — atom-differentiate

## differentiated content

The single artifact produced by this atom is a **differentiated version of provided content** —
a structured JSON object with the modified text and a list of supports added.

**Required fields:**
- `differentiated`: the modified content (same type as input)
- `supports_added`: list of specific modifications made
- `supports_NOT_changed`: what was intentionally preserved
- `human_review_required: true`

**Not produced by this atom:** original content generation or assessment items.
