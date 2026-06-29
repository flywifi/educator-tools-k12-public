---
name: feedback-write
description: "Write actionable feedback on a placeholder student response compared to a rubric. Use this atom when a workflow needs to model what good feedback looks like for a given rubric and response. Do NOT use with real student data — placeholders only. Do NOT use for grading."
---

# feedback-write

Generates model feedback on a placeholder response evaluated against a rubric. Shows teachers what actionable, growth-oriented feedback looks like. No real student data ever.

## Input

```json
{
  "rubric": {"criteria": [{"criterion": "Text evidence", "levels": {"Meets": "Cites 2+ relevant quotes", "Below": "No evidence cited"}}]},
  "placeholder_response": "[Student Name] wrote: The character was sad because of the events.",
  "grade": "7"
}
```

## Output

```json
{
  "tool": "feedback-write",
  "feedback": "You identified the character emotion — nice start! To move from Approaching to Meets, go back to paragraph 3 and find a specific quote that shows WHY the character feels this way. Try starting with: According to the text...",
  "rubric_level_matched": "Approaching",
  "growth_target": "Meets",
  "human_review_required": true
}
```

## Do NOT use this atom for
- Using real student data (placeholders only)
- Assigning grades or scores (this models feedback, not grading)
- Generating rubrics (use atom-rubric-build)

## Pipeline note
Follows `references/method.md` at the Generation step (feedback modeling). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — feedback tone and accuracy must be teacher-reviewed.
