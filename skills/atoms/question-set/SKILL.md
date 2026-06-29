---
name: question-set
description: "Generate a set of discussion or text-dependent questions at a target cognitive rigor level. Use this atom when lesson-planner needs questions for guided discussion, Socratic seminar, or close reading. Do NOT use for assessment items (use atom-assessment-item)."
---

# question-set

Creates 3-5 discussion or text-dependent questions scaffolded from lower to higher cognitive rigor (Bloom/DOK). Includes question type labels and suggested follow-ups.

## Input

```json
{
  "objective": "Students will analyze the author's use of figurative language.",
  "grade": "8",
  "subject": "ELA",
  "target_rigor": "DOK 3",
  "question_count": 4,
  "text_title": "The Road Not Taken"
}
```

## Output

```json
{
  "tool": "question-set",
  "questions": [
    {"level": "DOK 1", "question": "What two paths does the speaker describe?", "type": "literal"},
    {"level": "DOK 2", "question": "How does the speaker's description of each path differ?", "type": "inferential"},
    {"level": "DOK 3", "question": "Why might the speaker say the choice 'made all the difference' — is this sincere or ironic? Use evidence.", "type": "analytical"},
    {"level": "DOK 3", "question": "How does the poem's figurative language shape the reader's understanding of decision-making?", "type": "evaluative"}
  ],
  "human_review_required": true
}
```

## Do NOT use this atom for
- Assessment items with scoring (use atom-assessment-item)
- Reading comprehension quizzes (use assessment-designer)
- Questions without a text or topic anchor

## Pipeline note
Follows `references/method.md` at the Generation step (question design). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — question quality and rigor alignment must be teacher-verified.
