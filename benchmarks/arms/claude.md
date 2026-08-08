# Arm: `claude` — claude.ai (native, no TOS)

The "AI alone" baseline on Anthropic's side: claude.ai with its native file tools, Projects, and
artifacts — **without** the TOS skills or Reference Pack loaded. This isolates what a teacher gets
from the raw product.

## Run mode
Hosted → manual or subagent. Cannot run headless from this repo.

## Setup (record in `meta.json`)
- A fresh chat or a Project with **no TOS files** attached.
- Record the model/version shown in the UI and the date as `arm_version` / `captured`.

## Per-task protocol
1. Paste the task's `prompt` verbatim (from `benchmarks/tasks/<task>.json`). Attach any
   `input_files`.
2. Save the full response as `results/claude/<task>/output.md` (or export the artifact/file).
3. For grounding tasks, copy every standard/course code the answer cites into
   `results/claude/<task>/cited-codes.txt`, one per line — the objective grader resolves these
   against `tools/offline_index.py` exactly as it does for TOS (FL-shaped codes must exist;
   impossible asks must return empty, i.e. the model should refuse/ްflag rather than invent).
4. Note whether the response produced any **recorded, deterministic decision** (a gated verdict
   with a composite score) or only prose — that is the axis-2 governance signal.

## What to watch for (dimensions this arm tends to win/lose)
- Claude's underlying model is strong: per `docs/BENCHMARK.md` it *also* caught a fabricated
  standard and *also* refused a real-PII IEP request. Expect parity on the safety floor and on
  spotting obvious errors.
- The differences to capture honestly: does it record a **version** with a cited standard? Does it
  emit an **auditable gated decision** (not just advice)? Does it return **empty** on an impossible
  standards lookup, or invent a plausible code? These are the axis-1/axis-2 separators.
- Native artifacts/canvas can produce polished docs; capture any real file it exports for the
  axis-5 comparison and validate it with `tools/validate_document.py`.

## Evidence required
`output.md` (or exported file/screenshot) + `meta.json` + `cited-codes.txt` (grounding tasks).
Without these the task is `unrun` for `claude`.
