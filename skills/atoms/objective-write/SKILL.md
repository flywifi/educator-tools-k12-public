---
name: objective-write
description: "Write 1–3 measurable learning objectives for a given standard code, grade, and topic. Use this atom directly when a teacher says 'write me an objective for standard X' or when a workflow (lesson-planner, unit planner) needs objectives before generating activities. Do NOT use for writing a full lesson plan — that is lesson-planner. Do NOT use for IEP goals — use atom-iep-goal."
---

# objective-write

Generates measurable learning objectives (Students will be able to...) aligned to a specific standard. Returns Bloom's level tag for each objective. Takes verified standard codes from atom-standards-match; never fabricates a standard.

## Input

```json
{
  "standards": [
    {"code": "MA.4.FR.1.1", "description": "Model and express a fraction..."}
  ],
  "grade": "4",
  "subject": "Math",
  "count": 2,
  "bloom_ceiling": "Apply"
}
```

`bloom_ceiling`: highest Bloom's level to target (Remember / Understand / Apply / Analyze / Evaluate / Create). Default: Apply. `count`: 1–3.

## Output

```json
{
  "tool": "objective-write",
  "objectives": [
    {
      "text": "Students will be able to represent fractions greater than one on a number line by partitioning equal intervals.",
      "bloom_level": "Apply",
      "standard_code": "MA.4.FR.1.1",
      "verb": "represent"
    },
    {
      "text": "Students will be able to compare two fractions with unlike denominators using benchmark fractions.",
      "bloom_level": "Analyze",
      "standard_code": "MA.4.FR.1.1",
      "verb": "compare"
    }
  ],
  "human_review_required": true,
  "note": "Objectives are drafts — teacher should verify alignment and measurability before use."
}
```

## Do NOT use this atom for
- Full lesson plans (use lesson-planner)
- IEP goals (use atom-iep-goal — different format, legal context)
- Objectives without a standard code — always pass a verified standard

## Pipeline note
Follows `references/method.md` at the Generation step (objectives only). Output conforms to `references/metadata-schema.md`. Generation step only (objectives). No activities, assessments, or differentiation — pass the output to atom-activity-generate, atom-assessment-item, or atom-differentiate. `human_review_required: true`.
