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
| `skills/core/` | the hub (`teacher-core`), governance (`quality-review`), and health/repair skills |
| `skills/educator/` | capability skills: `lesson-planner`, `assessment-designer`, `presentation-builder`, `curriculum-mapping`, `special-education-support`, `intervention-mtss`, `family-communication`, `professional-learning`, `school-administration` |
| `skills/operations/` | operational skills: `document-intelligence`, `feed-curator`, `meeting-classifier`, `standards-updater`, `teacher-profile` |
| `skills/atoms/` | single-operation sub-skills composed by the capability skills |
| `shared/` | cross-cutting engines: Standards, Differentiation, Quality (source of truth) |
| `protocol-layer/` | 6 governance protocols, incl. the authoritative `quality-gates.md` |
| `canonical-sources/` | authoritative reference data: FL standards/course registries, school indexes, district overlays |
| `tools/` | `sync_check.py` drift guard, `new_skill.py` scaffolder, offline index, harvest pipeline, skill template |
| `implementation/` | platform packaging: `gpt/api/`, `gpt/web/`, `claude/`, `gemini/` |
| `docs/` · `security/` · `changes/` | architecture/benchmark docs, security policies, changelog |

## Key documents
- `docs/ARCHITECTURE.md` · `docs/QUALITY_MODEL.md` · `docs/ROUTING_MODEL.md` — design and governance.
- `security/SECURITY_AND_SAFETY.md` · `security/SECURITY_REVIEW.md` — security and safety.
- `changes/CHANGE_MANAGEMENT.md` · `changes/CHANGELOG.md` — change management.
- `STATE.md` — live status + recovery pointer.
- `CLAUDE.md` — working conventions.

## How it works (every artifact)
`Request → Routing → Protocol Enforcement → Generation → Validation → Quality Gates →
Approval/Certification → Release`. Standards-aligned, differentiated (UDL by default), and gated by a
9-dimension quality rubric. **Every output is decision support, not a final professional or legal
determination, and uses placeholder data only — never real student information.**

## Status
**Core build complete.** 19 skills (5 core incl. the hub `teacher-core`, 9 educator capability
skills, 5 operations skills) plus 43 atoms, 6 approved protocols (`protocol-layer/`), the live
**Quality Ledger** (`ledger/`), cross-skill **orchestration** (+ Example Library, `examples/`), a
passing **eval benchmark** (`docs/BENCHMARK.md`), installable **packaging**
(`tools/package_skill.py`), hardened **CI**, **semantic versioning** (`VERSION` /
`changes/CHANGELOG.md`), a **security review** (`security/SECURITY_REVIEW.md`), a
**success-metrics dashboard** (`docs/METRICS.md`, via `tools/metrics.py`), and an offline-first
data layer (`tools/offline_index.py`, harvest pipeline). The drift guard (`tools/sync_check.py`)
passes across all skills. Live status in `STATE.md`.

## Provenance
Built from the TOS Master Project Charters (V2–V4) and the Quality Gates Protocol v3.0.0
(sections 001–100). The drift-guard pattern follows a proven invariants-based approach.
