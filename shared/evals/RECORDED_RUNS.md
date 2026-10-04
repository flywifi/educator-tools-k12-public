<!-- last_reviewed: 2026-10-03 | owner: evals-maintainer -->
# Recorded model runs — the protocol for `kind: prompt` evidence

The decision this implements (R4, project owner): **model-facing behaviour is verified by
deliberate model runs, recorded as dated evidence; CI checks the record and never calls a
model.** `tools/eval_evidence.py` is the only writer of evidence files
(`benchmarks/results/evals/<skill>/<case-slug>.json`, schema `evidence.schema.json`).

## The bar
- `protocol: full` — >=3 recorded runs per case, and a second judge on >=20% of all full-protocol
  cases repo-wide. This is `benchmarks/README.md`'s own bar, applied unchanged.
- `protocol: single` — one recorded run. The documented long-tail bar; any case may be promoted
  to `full` at any time (the schema does not change).

## Recording a run
1. Compose the run context: the skill's `SKILL.md` + its boundary/safety references + the case
   `prompt` (or rendered `input`) as the teacher message. The model under test sees exactly what
   a deployed instance would carry — no extra coaching, no assertion list.
2. Save the model's answer **verbatim** to a file. Never edit it. An abridged or cleaned output
   is not evidence.
3. `python3 tools/eval_evidence.py --record '<skill>/<case>' --output-file <answer.txt>
   --arm <arm> --model '<model id as reported by the runtime — never guessed>' ...`
   - Machine sub-checks (the case's `machine` block; its `assert` block against the first JSON
     object in the output) are graded by the tool. They are never hand-typed.
   - A case with prose `assertions` REQUIRES `--judge-verdict` + `--judge-by`
     (`model:<id>` or `human:<name>`); attach `--per-assertion-file` with
     `[{assertion, verdict, quote}]`. `machine:eval_evidence` is legal only for cases whose
     whole contract is a structured `assert` block.

## Judging
The judge is blind: it receives the teacher prompt, the verbatim output, and the assertion list —
not the machine results and not the recorder's opinion. Every per-assertion verdict carries the
quote it rests on. Any assertion `fail` -> run verdict `fail`. An `unclear` is re-examined with
the skill's references; an `unclear` that survives re-examination is recorded `mixed` and treated
as a finding, not rounded up to a pass. Second judges are independent contexts, preferably a
different model.

## Arms
`arm` says who produced the outputs. `claude-session` = an in-repo Claude session run (the
recording campaign's arm). `teacher-device`, `claude-plugin-desktop`, etc. are open for runs on
real product surfaces; an arm label never claims more fidelity than it has.

## What the gate holds forever
Editing a case's prompt orphans its evidence (`prompt_sha256` mismatch = STALE = red CI). A
recorded `overall: fail` is a RED build until the skill or the case is deliberately fixed — a
recorded failure is a finding. Unrecorded cases are counted and printed, never silently passed.
