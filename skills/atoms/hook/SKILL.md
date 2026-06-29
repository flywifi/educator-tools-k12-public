---
name: hook
description: "Generate ONE anticipatory set or engagement hook for a lesson objective. Use this atom when lesson-planner needs a compelling opening that draws students into the topic. Do NOT use for warm-ups (use atom-warm-up) or full lessons."
---

# hook

Creates a single engagement hook (question, scenario, demo, visual, story opener) designed to spark curiosity and connect to the lesson's learning objective.

## Input

```json
{
  "objective": "Students will explain how volcanoes form at tectonic plate boundaries.",
  "grade": "6",
  "subject": "Science",
  "hook_type": "scenario"
}
```

## Output

```json
{
  "tool": "hook",
  "hook": {
    "type": "scenario",
    "text": "Imagine you are a geologist who just received an urgent call: a new island appeared in the Pacific Ocean overnight. Your job is to figure out how it got there. What questions would you ask first?",
    "follow_up_prompt": "What forces under the Earth could push rock above the ocean surface?",
    "connection_to_objective": "Sets up inquiry into plate tectonics and volcanic formation"
  },
  "human_review_required": true
}
```

## Do NOT use this atom for
- Warm-up / bell-ringer activities (use atom-warm-up)
- Full lesson planning (use lesson-planner)
- Assessment or evaluation hooks

## Pipeline note
Follows `references/method.md` at the Generation step (engagement design). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — teacher should adapt the hook to their class context.
