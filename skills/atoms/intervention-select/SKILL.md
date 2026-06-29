---
name: intervention-select
description: "Match a tiered intervention to a documented student need at a specified MTSS tier (1/2/3). Use this atom when intervention-mtss needs to suggest evidence-based interventions. Do NOT fabricate intervention program names or research citations."
---

# intervention-select

Suggests an evidence-based intervention matched to a student need and MTSS tier, with implementation notes (frequency, duration, group size). Never fabricates program names or citations.

## Input

```json
{
  "need": "below grade level in reading fluency",
  "tier": 2,
  "grade": "3",
  "subject": "Reading"
}
```

## Output

```json
{
  "tool": "intervention-select",
  "intervention": {
    "approach": "Repeated reading with corrective feedback",
    "tier": 2,
    "frequency": "3x per week, 20 minutes",
    "group_size": "3-5 students",
    "duration_weeks": "8-12 weeks before review",
    "evidence_note": "Repeated reading is supported by the What Works Clearinghouse for improving fluency in elementary grades",
    "progress_monitoring": "ORF probes biweekly"
  },
  "human_review_required": true
}
```

## Do NOT use this atom for
- Fabricating specific program names or research citations
- Tier 3 interventions without IEP team involvement
- Replacing MTSS team decision-making
- Using real student data

## Pipeline note
Follows `references/method.md` at the Generation step (intervention matching). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — intervention selection must be confirmed by the MTSS/IEP team.
