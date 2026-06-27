---
name: distractor-generate
description: "Generate plausible multiple-choice distractors tied to common misconceptions for an assessment item. Use this atom when assessment-designer needs realistic wrong answer choices. Do NOT use for generating the item stem — that is atom-assessment-item. Do NOT use for open-response items."
---

# distractor-generate

Creates plausible wrong-answer choices (distractors) for MC items, each linked to a documented misconception. Used after atom-assessment-item and atom-misconception to make MC items diagnostic, not just tricky.

## Input

```json
{
  "item_stem": "What is 3/4 + 1/2?",
  "correct_answer": "5/4 or 1 1/4",
  "grade": "4",
  "subject": "Math",
  "misconceptions": ["adds numerators and denominators separately", "converts to decimals incorrectly"]
}
```

## Output

```json
{
  "tool": "distractor-generate",
  "distractors": [
    {"choice": "4/6", "misconception": "adds numerators and denominators separately (3+1)/(4+2)"},
    {"choice": "1.0", "misconception": "converts to decimals incorrectly: 0.75 + 0.5 rounded down"},
    {"choice": "3/8", "misconception": "multiplies instead of adding"}
  ],
  "human_review_required": true
}
```

## Do NOT use this atom for
- Generating the item stem or correct answer (use atom-assessment-item)
- Open-response or constructed-response items (distractors are for MC only)
- Diagnosing individual student errors

## Pipeline note
Follows `references/method.md` at the Generation step (distractor creation). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — distractors must be plausible but clearly wrong; teacher review prevents ambiguous options.
