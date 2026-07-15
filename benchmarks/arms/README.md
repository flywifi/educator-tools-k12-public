# arms/ — how each comparison arm is exercised, and the evidence it must leave

Each `arms/<arm>.md` is the run protocol for one comparison arm: exactly what to do, and **what
evidence must land in `benchmarks/results/<arm>/<task>/`** for a result to count. The rule from the
root README applies everywhere: **no evidence → the arm is `unrun` for that task, never a scored
number** (`tools/run_benchmark.py --check` enforces it).

Two run modes:

- **Scripted** (`tos`, and installed `oss_parsers` in Phase B): `run_benchmark.py` produces the
  output and captures it automatically.
- **Hosted / manual-or-subagent** (`claude`, `chatgpt`, `gemini`, `ed_tools`): a person or a
  subagent runs the task in that product and saves the receipts. These results are **dated and
  version-pinned** — hosted products change, so a result is only ever "true as of `captured`."

## Blind judging (axis 3, all arms)

For generation-quality scoring, strip arm identity from every output before judging (rename to a
neutral `output.md`), have the judge assign the nine 0–5 dimensions **with a quoted evidence line
each** per `skills/core/quality-review/references/rubric.md`, then record them in the task's
scorecard so `score.py` can compute the composite. ≥3 runs/task; a second judge on ≥20% of outputs
for inter-rater agreement. The judge must not know which arm produced which output.

## Required evidence per output

Every `results/<arm>/<task>/` should contain:
- the raw output (`output.md`, or the produced file, or a screenshot if the product can't export);
- `meta.json`: `{"arm","task","captured":"YYYY-MM-DD","arm_version","source":"how produced/exported"}`;
- for grounding claims: the exact standard codes the output cited (so the objective grounding
  grader can resolve them against `tools/offline_index.py` the same way it grades TOS).
