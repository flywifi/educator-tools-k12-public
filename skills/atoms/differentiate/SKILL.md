---
name: differentiate
description: "Apply ONE differentiation profile (ELL, IEP/SPED, Gifted, 504, Below-grade, Above-grade) to a SINGLE piece of existing content. Use this when a teacher says 'make this activity ELL-friendly' or 'add IEP supports to this passage'. Do NOT use for full lesson differentiation — call this atom once per content piece. Do NOT generate new content from scratch — use atom-activity-generate or atom-assessment-item first, then differentiate."
---

# differentiate

Takes one piece of instructional content (activity, passage, question, instructions) and returns a differentiated version for the specified learner profile. Keeps the learning target constant; only modifies scaffolding, vocabulary, format, and support level.

## Input

```json
{
  "content": "Complete the number line by placing these fractions: 5/4, 3/2, 7/4.",
  "content_type": "activity_instructions | passage | question | rubric | directions",
  "profile": "ELL | IEP | gifted | below_grade | above_grade | 504",
  "grade": "4",
  "subject": "Math",
  "standard_code": "MA.4.FR.1.1",
  "notes": "Student reads at grade 2 level; native language Spanish"
}
```

`profile`: the differentiation target. `notes`: optional additional context about the learner (no real student names or IDs — use descriptors only).

## Output

```json
{
  "tool": "differentiate",
  "profile": "ELL",
  "original": "Complete the number line by placing these fractions: 5/4, 3/2, 7/4.",
  "differentiated": "Put each fraction on the number line. Use the word bank below.\n\n• 5/4 means 5 pieces of size 1/4\n• 3/2 means 3 pieces of size 1/2\n• 7/4 means 7 pieces of size 1/4\n\n[Word bank: number line, fraction, place, between]",
  "supports_added": ["simplified vocabulary", "visual word bank", "decomposed fraction meaning"],
  "supports_NOT_changed": ["learning target", "standard alignment", "required fractions"],
  "human_review_required": true,
  "note": "Verify the differentiated version still meets the standard before use. No real student data used."
}
```

## Profiles reference
- **ELL**: simplified vocabulary, sentence frames, visual supports, native-language glossary note
- **IEP**: chunked instructions, reduced items, visual schedule, extra time note, reduced reading level
- **Gifted**: extension question, independent research prompt, higher DOK, open-ended variation
- **504**: formatting adjustments, reduced visual clutter, extended time note
- **below_grade / above_grade**: Lexile and vocabulary adjustment, keeping standard alignment

## Do NOT use this atom for
- Generating new content (use atom-activity-generate first, then differentiate)
- Writing IEP goals (use atom-iep-goal)
- Real student PII — descriptors only (grade level, language, profile type)

## Pipeline note
Follows `references/method.md` at the Differentiation step. Output conforms to `references/metadata-schema.md`. Runs after Generation (atom-activity-generate / atom-assessment-item). `human_review_required: true`.
