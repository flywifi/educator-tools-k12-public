---
name: referral-draft
description: "Draft ONE referral (MTSS, evaluation, counselor, or outside agency) with required fields. Use this atom when intervention-mtss or special-education-support needs a referral template filled with placeholder data. Do NOT use with real student data."
---

# referral-draft

Creates a referral draft with all required fields (student info, reason, prior interventions, data summary) for MTSS escalation, special education evaluation, or counselor referral. Placeholders only.

## Input

```json
{
  "referral_type": "special_education_evaluation",
  "student_name": "[Student Name]",
  "grade": "2",
  "concern": "Persistent below-grade reading despite Tier 2 intervention for 12 weeks",
  "prior_interventions": ["Repeated reading 3x/week for 12 weeks", "Small group phonics instruction"]
}
```

## Output

```json
{
  "tool": "referral-draft",
  "referral": {
    "type": "special_education_evaluation",
    "student": "[Student Name]",
    "grade": "2",
    "date": "[Date]",
    "referring_staff": "[Teacher Name]",
    "reason": "Persistent below-grade reading despite 12 weeks of Tier 2 intervention",
    "prior_interventions": ["Repeated reading 3x/week for 12 weeks", "Small group phonics instruction"],
    "data_summary": "[Insert progress monitoring data showing inadequate response to intervention]",
    "requested_action": "Evaluation for possible Specific Learning Disability in Reading"
  },
  "human_review_required": true
}
```

## Do NOT use this atom for
- Using real student data (all fields use placeholders)
- Replacing parent consent or due process requirements
- Making eligibility determinations

## Pipeline note
Follows `references/method.md` at the Generation step (referral drafting). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — referral must be completed with actual data and submitted through district procedures.
