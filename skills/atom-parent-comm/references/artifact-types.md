# Artifact Types — atom-parent-comm

## parent communication draft

The single artifact produced by this atom is a **draft parent communication** — a structured JSON
object with subject line, greeting, body, and closing. All real names/dates are placeholders.

**Required fields:**
- `draft`: `{subject_line, greeting, body, closing}`
- `placeholders_used`: list of placeholders teacher must fill before sending
- `human_review_required: true`
- `legal_notice`: data-privacy reminder

**Not produced by this atom:** student records, IEP communications, or disciplinary notices.
