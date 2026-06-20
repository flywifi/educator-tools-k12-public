# STATE.md
## Teacher Operating System — Live Status & Recovery
Update at every phase boundary and after each skill ships. Recovery package = the charters + Quality
Gates 001–100 + `TOS_ECOSYSTEM_BUILD_OUTLINE.md` + this file.

**Last updated:** Phases 0–E delivered — 11 skills, 6 protocols, ledger, benchmark, packaging,
versioning, and the metrics dashboard. Core build complete.
**Active branch:** `claude/fervent-hawking-nyrzy5`
**Resume here:** maintenance mode. **Florida B.E.S.T./NGSSS is now wired** (`shared/standards/florida-best.md`
+ `resources/`). Optional follow-ups: widen the eval benchmark to all 27 cases; add more state corpora
via the Florida template; deepen the ontology; tag a `v1.0.0` release.

---

## Phase status
| Phase | Scope | Status |
|---|---|---|
| 0 — Skill Architecture & Foundations | scaffold, shared core, protocols, governance docs, teacher-core, tooling | ✅ Complete |
| A — Educational Foundations | quality-review + lesson/assessment/presentation | ✅ Complete |
| B — Governance Infrastructure | 6 protocols approved; decision records emitted by every skill; Quality Ledger created | ✅ Largely complete (runtime automation later) |
| C — Operational Integration | expansion skills + teacher-core orchestration (`workflows.md`) + Example Library | ✅ Complete |
| D — Repository Hardening | packaging, CI, catalog, security review, **versioning** (`VERSION`/`CHANGELOG`) | ✅ Complete (per-skill READMEs omitted — redundant with each `SKILL.md`) |
| E — Advanced Architecture | analytics (`metrics.py`/`METRICS.md`), artifact registry, `DEPLOYMENT.md`, AI-systems doc | ✅ Largely complete (ontology can deepen later) |

## Skill status (11 built)
| Skill | Role | Status |
|---|---|---|
| `teacher-core` | hub / router | ✅ built |
| `quality-review` | Quality Gates executor (+ `scripts/score.py`) | ✅ built |
| `lesson-planner` | capability (reference skill) | ✅ built (gold example) |
| `assessment-designer` | capability | ✅ built |
| `presentation-builder` | capability (renders via `pptx`) | ✅ built |
| `curriculum-mapping` | capability | ✅ built |
| `special-education-support` | capability (high-stakes; safety-emphasized) | ✅ built (example) |
| `intervention-mtss` | capability (high-stakes) | ✅ built (example) |
| `family-communication` | capability (privacy-emphasized) | ✅ built |
| `professional-learning` | capability (non-evaluative coaching) | ✅ built |
| `school-administration` | capability (school/system level) | ✅ built |

## Protocol layer (all v1.0)
| Protocol | Status |
|---|---|
| `quality-gates.md` | ✅ canonical (consolidated from provided 001–100) |
| `metadata-schema.md` | ✅ approved (reconstructed from QG) |
| `assumptions-protocol.md` | ✅ approved |
| `standards-verification.md` | ✅ approved |
| `conflict-protocol.md` | ✅ approved |
| `failure-recovery.md` | ✅ approved |

## Governance
- **Quality Ledger:** `ledger/quality-ledger.md` — append-only decision log, seeded with 5 entries
  (the worked examples; all Approved). Format/rules: `ledger/README.md`.
- Every `SKILL.md` references the pipeline + metadata schema and emits `human_review_required`
  (enforced by the drift guard).

## Last drift-guard result
`python3 tools/sync_check.py` → **PASS — 11 skills, 8 invariants, 2 synced refs.**
`quality-review/scripts/score.py` verified (normal / critical-override / threshold cases).

## Validation note
Every skill ships `evals/evals.json` (prompts + assertions) and worked examples. The eval
**benchmark ran** on a representative 3-case subset (with-skill vs. no-skill baseline): **with-skill
12/12 vs. baseline 8/12** — biggest uplift in governance/auditability and standards rigor; no
regressions. Details in **`BENCHMARK.md`**. Widening to the full eval set is a follow-up.

## Confirmed decisions
Full-K-12 breadth-first standards; FULL §33.1 9-dimension weighting authoritative; QG canonical
names; build on `pptx/docx/pdf` for rendered outputs; the 5 reconstructed protocols are approved.

## Open items (optional follow-ups — core build complete)
1. Widen the eval benchmark to the full 27-case set (subset done — `BENCHMARK.md`).
2. Florida B.E.S.T./NGSSS wired (`shared/standards/florida-best.md` + `resources/florida-2025-26.md`); add other states via the same template (licensing-gated).
3. Deepen the ontology; optional LLM-as-judge automation; tag a `v1.0.0` git release.

## Success metrics (Phase E)
Live dashboard: **`METRICS.md`** (regenerate with `python3 tools/metrics.py`). Current: 11 skills ·
40 artifact types · 27 eval cases · 10 standards frameworks (incl. Florida B.E.S.T./NGSSS) · 4 differentiation engines · 6/6
protocols · 100% ledger approval (seed) · 11/11 skills emit `human_review_required`.
