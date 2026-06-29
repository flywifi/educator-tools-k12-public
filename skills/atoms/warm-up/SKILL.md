---
name: warm-up
description: "Generate ONE bell-ringer or do-now warm-up activity aligned to a standard or objective. Use this atom when lesson-planner needs an opening activity. Do NOT use for full lesson planning — that is lesson-planner. Do NOT use for assessment items."
---

# warm-up

Creates a single 3-5 minute warm-up activity (bell-ringer, do-now) that activates prior knowledge and connects to the day's learning objective.

## Input

```json
{
  "objective": "Students will compare fractions with unlike denominators.",
  "grade": "4",
  "subject": "Math",
  "minutes": 5
}
```

## Output

```json
{
  "tool": "warm-up",
  "warm_up": {
    "title": "Fraction Comparison Challenge",
    "instructions": "Look at the two fractions on the board: 3/8 and 1/4. Without computing, which is larger? Write your prediction and reasoning in your journal.",
    "duration_minutes": 5,
    "materials": ["whiteboard", "math journals"],
    "connection_to_lesson": "Builds intuition for comparing fractions before formalizing with common denominators"
  },
  "human_review_required": true
}
```

## Do NOT use this atom for
- Full lesson planning (use lesson-planner)
- Assessment item generation (use atom-assessment-item)
- Activities longer than 10 minutes (use atom-activity-generate)

## Pipeline note
Follows `references/method.md` at the Generation step (warm-up creation). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — teacher should verify appropriateness for their specific class.
