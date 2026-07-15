<!-- last_reviewed: 2026-07-15 | owner: benchmarks-maintainer -->
# TOS Document Benchmark — methodology, axes, and the win-bar

**Question this program answers, with receipts:** is TOS meaningfully *above and beyond* what a
teacher gets from AI alone (or from consumer ed-AI tools) for document-related work — and does it
stay that way as the products evolve?

This is a governed benchmark: it lives under the same rules as everything else in this repo.
**Fabricating a result is a Quality-Gates §37 critical failure.** So every number a competitor
"scores" here must be backed by a captured evidence file; results are *generated from evidence* by
`tools/run_benchmark.py`, never hand-typed into the report; and external product claims are dated
observations declared in `tools/url-provenance.json`. The generated report carries
`human_review_required: true`. A benchmark that overclaims fails our own gates — by design.

## Two tracks (why the claim splits)

"Document-related" is really two different contests, and honesty requires naming which one a claim
belongs to:

- **Generation track** — content grounded in verified standards + governance, where TOS genuinely
  wins and can prove it (axes 1–6).
- **Ingestion track** — raw parsing (PDF tables, OCR, layout), a contest against purpose-built
  engines (Docling, Marker, Unstructured) that publish leaderboard numbers (axis 7). TOS's edge
  here is provenance + i18n-honesty + capability-gap honesty, not raw-extraction supremacy, so its
  honest goal is *parity + honesty edge* — potentially by composing a best-in-class engine under
  TOS governance rather than claiming to out-parse it.

## The comparison arms

| Arm | What it is | How exercised |
|---|---|---|
| `tos` | This repository's skills + tooling | **Headless/scripted** by `tools/run_benchmark.py` (real artifacts captured automatically) |
| `claude` | claude.ai Projects + artifacts + native file tools | Hosted → structured manual/subagent run, evidence captured |
| `chatgpt` | ChatGPT Projects + Advanced Data Analysis + Canvas | Hosted → structured manual/subagent run, evidence captured |
| `gemini` | Google Gemini + its file/canvas tools | Hosted → structured manual/subagent run, evidence captured |
| `oss_parsers` | Docling / Marker / Unstructured (ingestion track) | Scriptable if installed; else public-leaderboard citation with source |
| `ed_tools` | MagicSchool / Diffit / SchoolAI (generation axis) | Hosted → structured manual/subagent run, evidence captured |

Per-arm exercise protocol and the exact evidence each must capture live in `arms/<arm>.md`.
A result with **no evidence file is recorded as `unrun`, never a number** — enforced by
`run_benchmark.py --check`.

## The seven axes (what we measure)

| # | Axis | Objective grader | Track |
|---|---|---|---|
| 1 | **Standards-grounding fidelity** *(headline)* | every standard/course code an output cites is resolved against `tools/offline_index.py`; count fabricated (count=0), miscoded, and version-missing. Impossible asks (Hogwarts; grade-1-math photosynthesis) must return *empty*, not an invented code. | generation |
| 2 | **Governance / auditability** | presence of a gated decision record + deterministic composite (`score.py`) + the fabricated-`3.NF.A.9` critical-failure catch + `human_review_required`. | generation |
| 3 | **Generation quality** | blind 9-dimension rubric composite via `score.py` (judge assigns dims with quoted evidence per `quality-review/references/rubric.md`). | generation |
| 4 | **Differentiation consistency** | correct, standards-aligned ELL / IEP / gifted tiers present and internally consistent. | generation |
| 5 | **Output / format fidelity** | real `.pptx/.docx/.xlsx/PDF` structural validity via `tools/validate_document.py`; Google-bridge manifest. | generation |
| 6 | **Cost / efficiency** | tokens for grounded lookup vs. loading the corpus (the measured ~99.93% reduction, `docs/END_TO_END_WALKTHROUGH.md`). | generation |
| 7 | **Ingestion / parsing** | text-recovery, table-fidelity (TEDS/GriTS-style), i18n-preservation, container recursion, and **retrieval_state honesty** (visibility ≠ extraction). | ingestion |

## The win-bar ("above and beyond" as a number, not an adjective)

TOS is only allowed to *claim* superiority on an axis where it clears the bar with receipts:

- **Axis 1 (grounding):** TOS fabricated-citation rate must be **0**, and every arm's rate is
  quantified against it. Any TOS fabrication is itself a critical failure to fix, not to report
  around.
- **Axis 2 (governance):** TOS must emit an auditable gated decision record; the axis is won only
  if no comparison arm produces an equivalent recorded, deterministic verdict.
- **Axis 3 (generation):** TOS blind composite ≥ the best arm's composite **+ 0.3** (a stated
  margin, on the 0–5 scale) to claim a win; within ±0.3 is reported as *parity*, below is a
  *loss to fix*.
- **Axes 4–6:** TOS must meet or beat every arm; ties are reported as parity, not wins.
- **Axis 7 (ingestion track):** the honest target is **parity on raw accuracy + a measured honesty edge**
  (retrieval_state correctness, capability-gap disclosure vs. silent drop). Supremacy is not
  claimed unless measured.

Anything that fails its bar is a **finding to act on** (extend the skill/engine) — never a number
to soften. See "the durable loop" below.

## Grading protocol (blind, multi-run, anti-gaming)

1. **Objective axes (1, 4, 5, 6)** are scored by script in `run_benchmark.py` — no judge, no
   discretion.
2. **Subjective axis (3)** is blind-judged: the harness strips arm identity from each output, a
   judge subagent assigns the nine 0–5 dimension scores **with a quoted line of evidence per
   dimension** per `rubric.md`, and `score.py` computes the composite/decision. **≥3 runs per
   task**; a **second judge on a ≥20% subset** for inter-rater agreement.
3. Guards against the QG §89 anti-patterns (metric worship, gate shopping, documentation theater):
   the rubric is published, judging is blind, and the report links every score to its evidence
   receipt.

## The durable loop (how TOS *stays* ahead)

- **Regression gate:** re-run on any skill/engine change. If an arm closes a gap below the
  win-bar, that is a finding.
- **Loss → new eval:** any case where an arm beats TOS is promoted to a new eval case via the
  existing `tools/validate_outputs.py --promote` pattern, feeding the next skill iteration. This
  loop — not any single scoreboard — is what keeps TOS above and beyond.

## Layout

```
benchmarks/
  README.md          # this file — methodology + win-bar + honesty rules
  tasks/*.json       # the task suite (prompt + inputs + assertions + axis + artifact_type)
  arms/*.md          # per-arm exercise protocol + required evidence
  results/<arm>/<task>/   # captured raw outputs + evidence receipts (dated, version-pinned)
  scorecards/*.json  # per-task per-arm: objective metrics + judge dims + score.py verdict
  corpus/            # ingestion-track adversarial documents
```

Run everything through `tools/run_benchmark.py` (see repo root). The report is generated —
never hand-edit `docs/BENCHMARK.md` / `docs/BENCHMARK_COMPETITIVE.md`.
