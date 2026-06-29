---
name: progress-monitor-plan
description: "Create ONE progress-monitoring schedule and probe plan for an IEP goal or MTSS intervention. Use this atom when special-education-support or intervention-mtss needs a measurement plan. Do NOT use for generating the goals themselves (use atom-iep-goal)."
---

# progress-monitor-plan

Designs a progress-monitoring schedule with probe type, frequency, decision rules, and data collection method for a single IEP goal or intervention target.

## Input

```json
{
  "goal": "By [Date], [Student Name] will read 80 words correct per minute on grade-level passages.",
  "current_level": "45 WCPM",
  "target_level": "80 WCPM",
  "timeline_weeks": 36
}
```

## Output

```json
{
  "tool": "progress-monitor-plan",
  "plan": {
    "probe_type": "Oral Reading Fluency (ORF) — 1-minute timed passage",
    "frequency": "Biweekly",
    "aimline": "~1 WCPM gain per week",
    "decision_rule": "If 3 consecutive data points fall below the aimline, team meets to adjust intervention",
    "data_collection": "Chart WCPM on a line graph; compare to aimline",
    "review_dates": ["Week 9", "Week 18", "Week 27", "Week 36"]
  },
  "human_review_required": true
}
```

## Do NOT use this atom for
- Generating IEP goals (use atom-iep-goal)
- Administering assessments or recording data
- Making placement decisions

## Pipeline note
Follows `references/method.md` at the Generation step (monitoring plan). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — monitoring plans must be approved by the IEP/MTSS team.
