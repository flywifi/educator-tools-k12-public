# results/ — the receipts

One directory per arm per task: `results/<arm>/<task-id>/`. Each holds the arm's **raw output**
plus its **evidence** — for hosted arms, an exported transcript and/or screenshot with a `captured`
date and the arm's version/build; for scripted arms (`tos`, installed `oss_parsers`), the actual
output file the harness produced.

**No evidence here → the arm is `unrun` for that task, never a scored number.**
`tools/run_benchmark.py --check` fails the build on any scorecard row that claims a result without a
matching evidence file. This is the same anti-fabrication discipline the repo applies to data
provenance (`tools/url-provenance.json`) — a benchmark result is a claim, and claims need evidence.

Each evidence file should carry a small sidecar `meta.json`:
`{"arm": "...", "task": "...", "captured": "YYYY-MM-DD", "arm_version": "...", "source": "how it was produced/exported"}`.
