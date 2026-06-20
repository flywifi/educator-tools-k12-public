# STATE.md
## Teacher Operating System — Live Status & Recovery
Update at every phase boundary and after each skill ships. Recovery package = the charters + Quality
Gates 001–100 + `TOS_ECOSYSTEM_BUILD_OUTLINE.md` + this file.

**Last updated:** Phases 0–C complete + Phase D mostly done (orchestration, packaging, CI, security
review). 11 skills · 6 protocols · ledger · benchmark · packaging.
**Active branch:** `claude/fervent-hawking-nyrzy5`
**Resume here:** (a) **Phase E** — analytics over the ledger → success-metric dashboard; ontology
hardening; LLM-as-judge for quality-review; (b) widen the eval benchmark to all 27 cases;
(c) finish Phase D tail — semantic versioning + (optional) per-skill READMEs.

---

## Phase status
| Phase | Scope | Status |
|---|---|---|
| 0 — Skill Architecture & Foundations | scaffold, shared core, protocols, governance docs, teacher-core, tooling | ✅ Complete |
| A — Educational Foundations | quality-review + lesson/assessment/presentation | ✅ Complete |
| B — Governance Infrastructure | 6 protocols approved; decision records emitted by every skill; Quality Ledger created | ✅ Largely complete (runtime automation later) |
| C — Operational Integration | expansion skills + teacher-core orchestration (`workflows.md`) + Example Library | ✅ Complete |
| D — Repository Hardening | `package_skill.py` (.skill), hardened CI, skills catalog, `SECURITY_REVIEW.md` | 🟡 Mostly (versioning + optional per-skill READMEs remain) |
| E — Advanced Architecture | ontology, AI systems, analytics, deployment | ⬜ Not started |

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

## Open items
1. Phase E — analytics over the ledger → success-metric dashboard; ontology hardening; LLM-as-judge.
2. Widen the eval benchmark to the full 27-case set (subset done — `BENCHMARK.md`).
3. Phase D tail — semantic versioning; optional per-skill READMEs (currently redundant with SKILL.md).

## Success metrics (Phase E)
Artifact / Standards / Differentiation / Quality / Governance / AI-Safety coverage — _pending the
analytics pass over the Quality Ledger._
