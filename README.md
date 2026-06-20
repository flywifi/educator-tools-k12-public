# Teacher Operating System (TOS)

A production-grade educational AI **skill ecosystem** — a hub-and-spoke set of Claude Agent Skills
that generate, validate, differentiate, govern, and improve K-12 educational artifacts: lesson and
unit plans, assessments and rubrics, instructional slide decks, curriculum maps, IEP/504 supports,
MTSS/intervention plans, family communication, coaching/PD tools, and administrative resources.

It is designed to feel like one "Teacher Operating System" while remaining a modular, testable set
of skills that share one governed core.

## How it's organized

| Path | What |
|---|---|
| `skills/teacher-core/` | the hub: mission, personas, the pipeline, and routing |
| `skills/` (Phase A+) | capability skills: `quality-review`, `lesson-planner`, `assessment-designer`, `presentation-builder`, then the expansion set |
| `shared/` | cross-cutting engines: Standards, Differentiation, Quality (source of truth) |
| `protocols/` | 6 governance protocols, incl. the authoritative `quality-gates.md` |
| `tools/` | `sync_check.py` drift guard, `new_skill.py` scaffolder, skill template |

## Key documents
- `TOS_ECOSYSTEM_BUILD_OUTLINE.md` — the full, phase-gated build plan.
- `ARCHITECTURE.md` · `QUALITY_MODEL.md` · `SECURITY_AND_SAFETY.md` · `ROUTING_MODEL.md` ·
  `CHANGE_MANAGEMENT.md` — governance.
- `STATE.md` — live status + recovery pointer.
- `CLAUDE.md` — working conventions.

## How it works (every artifact)
`Request → Routing → Protocol Enforcement → Generation → Validation → Quality Gates →
Approval/Certification → Release`. Standards-aligned, differentiated (UDL by default), and gated by a
9-dimension quality rubric. **Every output is decision support, not a final professional or legal
determination, and uses placeholder data only — never real student information.**

## Status
**Core build complete — Phases 0–E delivered.** 11 skills (hub `teacher-core` + `quality-review` + 9
capability skills), 6 approved protocols, the live **Quality Ledger**, cross-skill **orchestration**
(+ Example Library), a passing **eval benchmark** (`BENCHMARK.md`), installable **packaging**
(`tools/package_skill.py`), hardened **CI**, **semantic versioning** (`VERSION` / `CHANGELOG.md`), a
**security review** (`SECURITY_REVIEW.md`), and a live **success-metrics dashboard** (`METRICS.md`,
via `tools/metrics.py`). The drift guard passes across all 11 skills. Optional follow-ups in
`STATE.md`.

## Provenance
Built from the TOS Master Project Charters (V2–V4) and the Quality Gates Protocol v3.0.0
(sections 001–100). The drift-guard pattern follows a proven invariants-based approach.
