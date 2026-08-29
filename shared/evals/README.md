<!-- last_reviewed: 2026-08-17 | owner: evals-maintainer -->
# shared/evals — the eval case contract

`eval-case.schema.json` is the one shape an eval case may take. `tools/run_evals.py` executes the
kinds that can be executed and reports honestly on the kinds that cannot.

## Why this exists

75 eval cases were authored across 18 skills and **none had ever been executed by a machine.** The
proof was a case that was false: `skills/core/skill-health` asserted `readiness_band: "strong"`
while its own recorded command, `health.py --scan`, returned `"not_ready"`. It had been wrong for
as long as the 44 "no eval cases" warnings had existed, because the CI step named *"Validate eval
files"* ran `json.load()` and nothing more — a file containing `{}` passed, and so did a lie.

There were also **six** case shapes: four dialects actually in use, a fifth prescribed by the note
inside the 43 empty atom stubs, and a sixth in the skill template. Four dialects cannot share a
runner, which is a large part of why no runner existed.

## The three kinds

| `kind` | Executed in CI? | What it is |
|---|---|---|
| `command` | **yes** | An allow-listed argv; assertions run against parsed stdout. |
| `call` | **yes** | An in-repo callable (`module.path:function`); assertions run against its return. |
| `prompt` | **no — never** | Model-facing. Prose `assertions`, judged by a human or a blind judge. Evidence is recorded under `benchmarks/results/`; absent evidence is `unrun`, which is a visible gap and not a pass. |

A case is `prompt` when no code performs the behaviour it describes. That is a statement about the
repo, not a fallback: 17 `meeting-classifier` cases carry `input` + `assert` and look executable,
but nothing in the tree classifies meeting evidence — `router.meeting_route()` maps an
*already-known* type to a skill. Calling them `call` cases would assert a callable that does not
exist.

## The assert grammar

Plain keys and dotted paths (`required_cadence.authority`) read the parsed output. Reserved
meta-keys:

- `has: [k, …]` — every key present
- `each.<listkey>: [k, …]` — every item of that list carries those keys
- `stdout_contains: [s, …]` — substrings of raw stdout; the only honest form for a tool that emits
  prose rather than JSON
- `exit_code: N`

A string value beginning `>=`, `<=`, `>`, `<` or `!=` is a comparison (a list compares by length);
a list compares order-insensitively; **a bool compares by identity**, so `1` does not satisfy
`true`.

## Skips and `unrunnable` are findings, not passes

- **skip** — the command has an unfilled `<placeholder>`, names a fixture that does not exist,
  needs the network, or names a missing tool. Each is a coverage gap someone chose not to close.
- **unrunnable** — the case asserts structured keys against a tool that emits prose. The case needs
  a `--json` mode on that tool, or reclassifying. It is not a runner bug and it is not a pass.

Both are counted and printed. Only a genuine `FAIL` exits nonzero.

## Running it

```bash
python3 tools/run_evals.py --check       # shape only; executes nothing
python3 tools/run_evals.py --run         # executes command + call kinds (CI does this)
python3 tools/run_evals.py --self-test   # the grammar, the skip gate, the allow-list
```

`command` cases are data in a JSON file, so `argv[0]` is checked against an allow-list of
interpreters — without it, editing an eval file would be arbitrary code execution in CI. Network
commands never run unless `--allow-network` is passed.

## Trigger evals

`trigger_evals` tests the *description's* routing rather than the skill's behaviour: does this skill
activate on prompts it should own, and stay quiet on prompts it should not? The bar (mandated by the
skill template since it was written) is **≥10 positive / ≥5 negative**, passing at ≥80% positive and
≤20% negative, where an activation counts only on an actual invocation. Two or more negative
activations makes the run **DETECTOR SUSPECT** — the description is broken and the run cannot be
scored as a pass.

`graded_by: "router"` means the set is machine-gradable offline through
`shared/routing/router.py`, which is deterministic; `graded_by: "model"` means it needs a recorded
run.
