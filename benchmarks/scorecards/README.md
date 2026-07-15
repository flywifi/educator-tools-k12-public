<!-- last_reviewed: 2026-07-15 | owner: scorecards-maintainer -->
# scorecards/ — per-task, per-arm scored results (generated, not hand-edited)

One file per task: `scorecards/<task-id>.json`. Written by `tools/run_benchmark.py`, consumed by
`--report`. Never hand-edit — a hand-entered number is a fabricated result (QG §37).

Shape:

```json
{
  "task": "T1-lesson-fractions",
  "axes": [1, 3, 4],
  "arms": {
    "tos": {
      "evidence": "results/tos/T1-lesson-fractions/output.md",
      "objective": {
        "axis1_codes_cited": 2, "axis1_codes_fabricated": 0, "axis1_version_recorded": true,
        "axis4_tiers_present": ["ell", "iep", "gifted"],
        "axis5_binary_valid": null, "axis6_lookup_tokens": 715
      },
      "judge": {
        "integrity": 5, "accuracy": 5, "alignment": 4, "educational_quality": 4,
        "governance": 5, "user_intent": 5, "accessibility": 4, "professional_quality": 4, "safety": 5,
        "evidence_quotes": {"integrity": "…quoted line…"}
      },
      "verdict": {"composite": 4.62, "decision": "Approved", "critical_override": false},
      "runs": 3, "judge_count": 1
    },
    "claude":  {"evidence": null, "status": "unrun"},
    "chatgpt": {"evidence": null, "status": "unrun"},
    "gemini":  {"evidence": null, "status": "unrun"},
    "ed_tools":{"evidence": null, "status": "unrun"}
  }
}
```

`objective.*` values come from the scripted graders (grounding via `offline_index.py`, format via
`validate_document.py`, tokens, differentiation presence). `judge.*` are the blind-assigned 9
dimensions with a quoted evidence line each; `verdict` is `score.py`'s output on those dims.
An arm with `status: "unrun"` contributes no number to the report — only a visible gap.
