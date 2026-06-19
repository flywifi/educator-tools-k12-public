# STATE.md
## Teacher Operating System — Live Status & Recovery
Update at every phase boundary and after each skill ships. Recovery package = the charters + Quality
Gates 001–100 + `TOS_ECOSYSTEM_BUILD_OUTLINE.md` + this file.

**Last updated:** Phase 0 complete.
**Active branch:** `claude/fervent-hawking-nyrzy5`
**Resume here:** Begin **Phase A** — build `quality-review`, then `lesson-planner` (reference skill),
`assessment-designer`, `presentation-builder`. Use the inner loop (draft → evals → iterate).

---

## Phase status
| Phase | Scope | Status |
|---|---|---|
| 0 — Skill Architecture & Foundations | scaffold, shared core, protocols, governance docs, teacher-core, tooling | ✅ Complete |
| A — Educational Foundations | quality-review + capability skills (lesson/assessment/presentation) | ⬜ Not started |
| B — Governance Infrastructure | protocols finalized + wired; metadata everywhere; ledger | ⬜ Not started |
| C — Operational Integration | cross-skill workflows; example library; expansion skills | ⬜ Not started |
| D — Repository Hardening | packaging, CI, security review, READMEs, versioning | ⬜ Not started |
| E — Advanced Architecture | ontology, AI systems, analytics, deployment | ⬜ Not started |

## Skill status
| Skill | Role | Status |
|---|---|---|
| `teacher-core` | hub / router | ✅ built (Phase 0) |
| `quality-review` | Quality Gates executor | ⬜ Phase A |
| `lesson-planner` | capability (reference skill) | ⬜ Phase A |
| `assessment-designer` | capability | ⬜ Phase A |
| `presentation-builder` | capability | ⬜ Phase A |
| expansion set (6 skills) | capability | ⬜ Phase C |

## Protocol layer
| Protocol | Status |
|---|---|
| `quality-gates.md` | ✅ canonical (consolidated from provided 001–100) |
| `metadata-schema.md` | ⚠️ drafted from QG refs — pending your review |
| `assumptions-protocol.md` | ⚠️ drafted — pending review |
| `standards-verification.md` | ⚠️ drafted — pending review |
| `conflict-protocol.md` | ⚠️ drafted — pending review |
| `failure-recovery.md` | ⚠️ drafted — pending review |

## Last drift-guard result
`python3 tools/sync_check.py` → see commit (Phase 0: PASS — 1 skill, 8 invariants, 2 synced refs).

## Confirmed decisions
- Scope of this pass: **Phase 0 foundations only.**
- Standards/grade: **Full K-12, breadth-first** (state-agnostic adapter).
- 5 missing protocols: **drafted from QG references**, pending review.
- Assumed defaults: repo home = this repo; **FULL §33.1 9-dimension weighting authoritative**; QG
  canonical skill names adopted; `.pptx/.docx/.pdf` outputs will build on the existing
  `pptx/docx/pdf` skills.

## Open items for the user
1. Review the 5 drafted protocols (or upload the originals if they exist).
2. Confirm the assumed defaults above.
3. Standards licensing for any specific state corpora before bundling.

## Success metrics (populated from Phase E)
Artifact / Standards / Differentiation / Quality / Governance / AI-Safety coverage — _pending._
