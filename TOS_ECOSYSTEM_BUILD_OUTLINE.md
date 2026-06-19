# Teacher Operating System (TOS)
# SKILL.md Ecosystem — Expanded Build Outline

Version: 2.0
Status: Phase 0 (Foundations) BUILT on `claude/fervent-hawking-nyrzy5` — see `STATE.md`. The §13 decisions were resolved this session (Phase 0 only; full-K–12 breadth-first; 5 protocols drafted from QG; defaults accepted) and are recorded in `STATE.md`.
Operationalizes: Master Project Charter V4 + the Quality Gates Protocol v3.0.0 (sections 001–100).

Authoritative inputs read for this plan:
- Charter V2, Charter V2 (duplicate), Charter V3 §§12–24, Charter V4
- **Quality Gates Protocol v3.0.0 — full sections 001–100** (the 20 `_FULL` files + the two condensed editions)
- iMessage Forensic Toolkit (read as an engineering/quality exemplar, not TOS domain content)

### Changelog v1.0 → v2.0
The Quality Gates package resolved the biggest unknown and **revealed the project's real
architecture and naming**, which the charters did not. Changes:
- Adopted the **canonical skill names** from Quality Gates §2.1 (`teacher-core`, `quality-review`,
  `lesson-planner`, `assessment-designer`, `presentation-builder`) — these supersede v1's invented
  names. The broader charter categories become the **expansion set** (§4).
- Promoted **Quality Gates from "to be reconstructed" to a fully specified, buildable governance
  engine** with a concrete 9-dimension rubric, weights, thresholds, gate order, decision records,
  certification levels, release readiness, and 8 repository invariants (§8).
- Added the **6-file protocol layer** and **5 governance documents** named in QG §2.1 to the
  repository layout and build plan (§7, §11).
- Re-sequenced Phase A to match QG's stated **"Next Expansion Target: `skills/teacher-core/`"** (§11).
- Updated decisions/risks: §13.5 (Quality Gates) is **resolved**; new open items are the **5 other
  protocols** (referenced as complete but not delivered) and a **weighting inconsistency** (§13, §14).

---

## 0. How to read this document

This is the bridge between your **charters + Quality Gates Protocol** (the "what" and the
governance "how") and an actual **ecosystem of Claude Agent Skills** (the build). It is:

- **Faithful to your source documents** — every charter phase/engine/persona AND the full Quality
  Gates model are carried through and mapped explicitly (§2, §8, §12).
- **Executable** — exact directory layout, the anatomy of each skill, the shared/governed core, and
  an ordered, phase-gated build plan with exit criteria.
- **Self-preserving** — this file + `STATE.md` (Phase 0) + the charters + Quality Gates form the
  recovery package, honoring your preservation theme.

It does not build anything yet. Build begins after the decision points in §13 are confirmed.

---

## 1. What a "SKILL.md ecosystem" is (grounding)

A **Skill** = a directory with a `SKILL.md` (YAML frontmatter: `name`, `description`) + a markdown
body, optionally bundling `references/`, `scripts/`, `assets/`. Claude loads skills by **progressive
disclosure**: (1) name+description always in context (~100 words; the `description` is the only
trigger signal); (2) SKILL.md body when triggered (target < 500 lines); (3) bundled resources only
when needed (scripts can run without being read in).

This three-level limit is why the charter's huge surface (lessons → IEPs → MTSS → newsletters)
**must** be decomposed into focused skills sharing a governed core — exactly the structure Quality
Gates §2.1 already prescribes.

---

## 2. Source → Build mapping (nothing dropped)

| Source element | Origin | Where it lands |
|---|---|---|
| Phases 0, A–E | Charters V2/V4 | §11 Build Plan |
| 7-stage production pipeline | Charter V3 §15, V4 | §5 (merged with the QG lifecycle) |
| QG governance pipeline (Routing→…→Release) | QG §3.1 | §5 (merged) |
| 8 Engines | Charter V3 §16 | §4 skills + §6 shared core |
| 9 Artifact categories | Charter V3 §14 | §4 capability skills (v1 + expansion) |
| 7 Personas | Charter V3 §13 | §3 + `shared/personas/` |
| Canonical skill names | **QG §2.1** | §4 Skill Inventory |
| 6 Protocols | **QG §2.1, §3.3** | §6 `protocols/` + §8 |
| 5 Governance docs | **QG §2.1** | §7 repo root docs |
| Quality Gates rubric/thresholds/gates/certs/invariants | **QG §§1–100** | §8 Governance & Quality |
| Decision-record schema | QG §39, §93 | §8.5 metadata/decision block |
| 8 Repository Invariants | QG §96 | §8.6 drift guard + CI |
| Preservation & Recovery | all charters | §12 + `STATE.md` |
| Quality/engineering bar, drift guard | iMessage toolkit | §8.6, §11 Phase D |

---

## 3. Personas (Charter V3 §13)

Drive both triggering (descriptions in their language) and skill defaults. Canonical in
`shared/personas/personas.md`:
Classroom Teacher · Special Education Teacher · Interventionist · Instructional Coach ·
Curriculum Specialist · School Administrator · District Leader.

---

## 4. The Skill Inventory (the ecosystem)

### 4.1 Architecture — hub-and-spoke (now confirmed by QG §2.1, not just inferred)

- **Hub:** `teacher-core` — mission, personas, the unified pipeline (§5), and **routing**. This is
  the charter's `skill_mission_FULL.md` and QG's stated next target (`skills/teacher-core/`).
- **Governance skill:** `quality-review` — the **executor of the Quality Gates Protocol** (§8). It
  scores artifacts on the 9 dimensions, applies thresholds + critical-failure overrides, and emits
  the decision record. It is the pipeline's penultimate stage.
- **Capability skills (spokes):** produce artifacts; each self-checks against the rubric, then hands
  to `quality-review` for the authoritative gate (defense in depth).
- **Shared/governed core** (`shared/` + `protocols/`, §6): standards/differentiation engines +
  the 6 protocols + ontology + personas. Single source of truth, synced into each skill at package
  time, policed by the drift guard (§8.6).

### 4.2 v1 skill set (named in QG §2.1 — build these first)

| Skill | Role | Primary artifacts |
|---|---|---|
| `teacher-core` | Hub / router | intake, routing, pipeline orchestration, shared mission |
| `quality-review` | Quality Gates executor | dimension scores, gate decisions, decision records, certification |
| `lesson-planner` | Capability | lesson plans, unit plans, guided notes, exit tickets, centers, projects |
| `assessment-designer` | Capability | formative/summative assessments, rubrics, performance tasks, item banks |
| `presentation-builder` | Capability | slide decks / instructional presentations (likely on the `pptx` skill — see §13.6) |

### 4.3 Expansion skill set (charter V3 §14 categories, post-v1)

`curriculum-mapping` (maps, pacing, scope & sequence) · `special-education-support` (IEP supports,
accommodations, modifications, progress monitoring) · `intervention-mtss` (Tier 1/2/3, MTSS) ·
`family-communication` (newsletters, parent comms, reports) · `professional-learning` (coaching,
observation tools, PD) · `school-administration` (walkthroughs, implementation, monitoring).

Naming will follow the QG `-er`/role style for consistency (confirm in §13.7). The charter's 9th
category, **AI Artifacts**, stays internal/meta (folded into shared core + Phase E).

### 4.4 Standard anatomy of every skill (consistency = an ecosystem, not a pile of skills)

```
<skill-name>/
├── SKILL.md                 # frontmatter + workflow (<500 lines); pushy, scoped description
├── references/
│   ├── artifact-types.md    # the artifacts this skill produces, with specs
│   ├── method.md            # the unified pipeline (§5) applied to this domain
│   ├── standards.md         # (synced from shared) standards alignment
│   ├── differentiation.md   # (synced from shared) UDL/tiering/EL/IEP
│   └── quality-gates.md     # (synced from shared) the rubric this skill self-checks against
├── assets/templates/        # output templates
├── scripts/                 # deterministic helpers (standards lookup, rubric builder, exporters)
├── examples/                # gold-standard worked outputs
└── evals/evals.json         # test prompts + assertions (skill-creator methodology, §11.7)
```

`lesson-planner` is built **first and complete** as the reference implementation; the rest clone it.

---

## 5. The Unified Pipeline (Charter 7-stage method ⊕ QG lifecycle §3.1)

The charter describes the *generation* path; Quality Gates describes the *governance* path around
it. Merged, authored once in `shared/method/method.md`:

```
Request
 → 1. Routing             (teacher-core: persona × artifact × subject × grade band → skill)
 → 2. Protocol Enforcement(assumptions logged · metadata initialized · standards-verification armed)
 → 3. Generation          (capability skill: Analysis → Standards Alignment → Differentiation → Generation)
 → 4. Validation          (minimum correctness before gates — QG §7.3)
 → 5. Quality Gates       (quality-review: 9-dimension scoring in gate order, thresholds, overrides — §8)
 → 6. Approval / Certification (decision record + certification level — QG §38, §59)
 → 7. Release             (release-readiness check; Final Artifact + metadata block)
```

Validation (4), Quality Gates (5), and Release (7) are distinct on purpose (QG §56: an artifact can
pass quality and still fail release readiness).

---

## 6. Shared/Governed Core

```
shared/
├── method/method.md                 # unified pipeline (§5)
├── personas/personas.md             # 7 personas + default needs (§3)
├── ontology/ontology.md             # canonical vocabulary (artifact, standard, accommodation, tier…)
├── standards/                       # STANDARDS ENGINE
│   ├── standards-framework.md       # select / cite / verify standards
│   ├── ccss.md  ├── ngss.md  └── state-standards-model.md
├── differentiation/                 # DIFFERENTIATION ENGINE
│   ├── udl.md ├── tiering.md ├── english-learners.md └── accommodations-catalog.md
└── quality/                         # QUALITY + VERIFICATION ENGINES (mirrors the QG Protocol)
    ├── quality-gates.md             # the rubric, weights, thresholds, gate order (from QG §§6–45)
    ├── verification-checklists.md   # per-artifact correctness/alignment checks
    └── readability-age.md

protocols/                           # THE 6-FILE PROTOCOL LAYER (QG §2.1) — governance source of truth
├── quality-gates.md                 # ✅ PROVIDED (sections 001–100)
├── metadata-schema.md               # ⛔ referenced "complete" but NOT delivered — see §13.5
├── assumptions-protocol.md          # ⛔ not delivered
├── standards-verification.md        # ⛔ not delivered
├── conflict-protocol.md             # ⛔ not delivered
└── failure-recovery.md              # ⛔ not delivered
```

`shared/quality/quality-gates.md` is the operational rubric the skills self-check against;
`protocols/quality-gates.md` is the authoritative protocol the `quality-review` skill enforces. The
drift guard keeps the two in sync.

---

## 7. Repository Layout

```
repo-root/
├── CLAUDE.md                         # branch rules, drift guard, build/test commands
├── README.md                         # what the ecosystem is, how to install skills
├── TOS_ECOSYSTEM_BUILD_OUTLINE.md    # this document
├── STATE.md                          # live status dashboard + recovery pointer (Phase 0)
├── ARCHITECTURE.md  QUALITY_MODEL.md  SECURITY_AND_SAFETY.md  ROUTING_MODEL.md  CHANGE_MANAGEMENT.md   # the 5 governance docs (QG §2.1)
├── skills/
│   ├── teacher-core/  quality-review/  lesson-planner/  assessment-designer/  presentation-builder/   # v1
│   └── (curriculum-mapping/ … school-administration/)                                                 # expansion
├── shared/                           # standards/differentiation/quality engines (§6)
├── protocols/                        # the 6 protocols (§6)
├── tools/
│   ├── sync_check.py                 # drift guard (invariants, incl. QG §96) — modeled on the toolkit
│   ├── new_skill.py                  # scaffolds a skill from the standard anatomy (§4.4)
│   └── package_skill.py              # builds installable .skill bundles (Phase D)
├── examples/                         # cross-skill Example Library (Phase C)
└── .github/workflows/ci.yml          # drift guard + eval smoke tests (Phase D)
```

Charter `repository/` dirs map cleanly: `skill/`→`skills/`; `standards|differentiation|quality|governance|ontology`→`shared/`+`protocols/`;
`generation`→per-skill templates+scripts; `educational-artifacts`→per-skill `artifact-types.md`;
`examples`→`examples/`; `ai`+`deployment`→Phase E.

---

## 8. Governance & Quality — the Quality Gates Protocol, operationalized

The `quality-review` skill is the **executor**; `protocols/quality-gates.md` is the **spec**. Below
is the operational distillation of QG §§1–100.

### 8.1 The 9 quality dimensions, rubric, and weights (QG §§22, 33.1)
Each dimension scored **0–5** (0 critical failure … 5 exemplary; QG §23).

| Dimension | Weight | Note |
|---|---|---|
| Integrity | 25% | highest; may never weigh less than Accuracy (QG §33.3) |
| Accuracy | 20% | |
| Alignment | 15% | |
| Educational Quality | 15% | distinct from accuracy (QG §17.1) |
| Governance Compliance | 10% | |
| User Intent | 7% | |
| Accessibility | 3% | |
| Professional Quality | 3% | |
| Safety | 2% | |

> **Inconsistency to resolve (§13.6):** the condensed edition omits Safety and uses User Intent 10 /
> Accessibility 2. This plan treats the **FULL 9-dimension weighting (§33.1) as authoritative**.

### 8.2 Composite & thresholds (QG §§34, 35.3)
`Composite = Σ(dimension × weight)`. Approved ≥ 4.0 · Conditionally Approved 3.0–3.99 ·
Remediation Required 2.0–2.99 · Rejected < 2.0.

### 8.3 Critical-failure override (QG §§35.4, 36.4, 37) — non-negotiable
Any of these → **Rejected regardless of composite**, and may never be overridden: fabricated
citation/source/audit/certification/verification, critical safety violation, approval without
evidence, undocumented exception, falsified documentation.

### 8.4 Gate execution order with early termination (QG §§20.2, 42.2)
Integrity → Safety → Governance → Accuracy → Alignment → Educational Quality → Accessibility →
Professional Quality → User Intent. Gate outcomes: **PASS / FAIL / REMEDIATION REQUIRED** (§6.2).
Stop early on a critical failure (§20.4).

### 8.5 Decision record / metadata block (QG §§39, 93) — every artifact carries one
Required: `decision_id, artifact_id, reviewer, date, decision, evidence, rationale`.
Recommended: `score_summary, risk_summary, audit_reference, remediation_reference`.
Plus the education trailer (persona, grade band, subject, standards set+version, differentiation
applied, **human-review-required** flag).

### 8.6 Drift guard (tools/sync_check.py) — enforces the 8 Repository Invariants (QG §96)
Asserts invariants, not diffs (toolkit pattern). Invariant set = QG §96 + ecosystem rules:
1. Integrity precedes approval · 2. Evidence precedes certification · 3. Validation precedes release ·
4. Audits remain independent · 5. Critical failures block approval · 6. History remains traceable ·
7. Quality decisions remain auditable · 8. Certification requires evidence · plus: each skill's
synced `references/quality-gates.md` matches `shared/quality/`, every skill emits the decision block,
every skill references the unified pipeline, no skill ships TODOs. Exit 0/1; runs in CI.

### 8.7 Certification & release readiness (QG §§59, 83, 87)
Certification levels: Development → Review → Production → Governance Certified → Repository Certified.
Release-readiness domains (all must pass): Quality · Governance · Documentation · Audit ·
Remediation · Certification → outcome Ready / Conditionally Ready / Not Ready.

### 8.8 Anti-patterns the system actively guards against (QG §89)
Approval Without Evidence · Metric Worship · Documentation Theater · Audit Evasion · Gate Shopping.

---

## 9. Safety & Constraints (Charter V3 §20 + QG Safety/Integrity gates, expanded for education)

The Safety dimension + the `SECURITY_AND_SAFETY.md` governance doc encode:
- **Student data / FERPA:** never request/infer/store real student PII; placeholders only — enforced
  as an Integrity/Safety check.
- **Human-in-the-loop:** every artifact is decision support, not a final professional/legal
  determination (explicit on IEP/504/MTSS) — the `human-review-required` flag.
- **Accessibility:** UDL by default; the Accessibility gate (QG §31) checks readability/age/usability.
- **Bias & representation:** a review step for names, contexts, examples.
- **Integrity:** no fabricated standards/citations — an automatic-failure condition (QG §37.3).

---

## 10. Success Metrics (Charter V3 §22, now measurable via QG metrics §§61–67)

| Charter metric | Measure |
|---|---|
| Artifact Coverage | # artifact types with template + gold example + passing eval |
| Standards Coverage | # frameworks wired into the Standards engine (CCSS, NGSS, + states) |
| Differentiation Coverage | each artifact has UDL+tiering+EL+IEP variants verified (QG Differentiation Coverage Rate §65.3) |
| Quality Coverage | % eval outputs passing Quality Gates (≥4.0, no critical failure) |
| Governance Coverage | all 6 protocols implemented + enforced by drift guard |
| AI Safety Coverage | FERPA/bias/accessibility/human-review checks present & tested |

A Phase E analytics script renders these (+ QG longitudinal trends §95) into `STATE.md`.

---

## 11. Build Plan (one build phase per charter phase; QG sets the order)

### Phase 0 — Skill Architecture & Foundations  *(charter Phase 0)*
- **Deliverables:** repo scaffolding (§7); `CLAUDE.md`; `STATE.md`; the 5 governance docs; the
  `shared/` core + `protocols/` (placing the provided `quality-gates.md`, drafting the other 5 if
  approved — §13.5); the **`teacher-core`** orchestrator SKILL.md (= `skill_mission_FULL.md`); the
  standard skill template + `tools/new_skill.py`; `tools/sync_check.py` with the QG §96 invariants.
- **Exit:** a throwaway skill scaffolds, passes the drift guard, and `teacher-core` routes a smoke
  prompt correctly.

### Phase A — Educational Foundations  *(charter Phase A; QG "Next Target: skills/teacher-core/")*
- **Order:** `teacher-core` → `quality-review` (stand up Quality Gates execution early so every
  later skill is gated from birth) → `lesson-planner` (built complete as the reference) →
  `assessment-designer` → `presentation-builder`.
- **Exit:** each skill triggers on realistic prompts, produces a gold artifact, and passes
  `quality-review` (≥4.0, no critical failure) + its evals.

### Phase B — Governance Infrastructure  *(charter Phase B)*
- **Deliverables:** finalize all 6 protocols; wire decision records + assumptions/conflict/failure
  handling into every skill; standards-verification tooling; the Quality Ledger (QG §94) format.
- **Exit:** every artifact carries a decision record; conflicts/failures handled deterministically;
  drift guard green across all skills.

### Phase C — Operational Integration  *(charter Phase C)*
- **Deliverables:** `teacher-core` cross-skill workflows (e.g., "unit + its assessments +
  differentiation + a slide deck + a parent letter" in one pass); operations docs; the populated
  **Example Library**; the expansion skills (§4.3) as capacity allows.
- **Exit:** multi-artifact workflows run end-to-end and each passes Quality Gates.

### Phase D — Repository Hardening  *(charter Phase D)*
- **Deliverables:** `package_skill.py` → installable `.skill` bundles; CI (drift guard + eval smoke
  tests); education safety review + QG-invariant checks; per-skill + top-level READMEs at the
  toolkit's documentation bar; semantic versioning + the Maturity Model (QG §79) self-assessment.
- **Exit:** CI green; skills install cleanly; docs match the exemplar.

### Phase E — Advanced Architecture  *(charter Phase E)*
- **Deliverables:** ontology hardening (E1); AI systems — LLM-as-judge for Quality Gates scoring,
  AI-artifacts module (E2); analytics rendering §10 metrics + QG longitudinal monitoring into
  `STATE.md` (E3); deployment/update/distribution strategy (E4).
- **Exit:** metrics dashboard exists; deployment path documented.

### 11.7 Per-skill inner loop (skill-creator methodology; inside Phases A–C)
Draft `SKILL.md` → 2–3 realistic test prompts → run with-skill vs. baseline → eval-viewer review →
iterate → optimize the `description` for trigger accuracy (specific + slightly pushy + explicit
"do NOT use for…") → package.

---

## 12. Preservation & Recovery

Recovery package = the charters + Quality Gates sections 001–100 + this outline + `STATE.md`.
`STATE.md` is the live dashboard (phase + per-skill status, last drift-guard result, success
metrics, "resume here" pointer), updated at every phase boundary. Recovery procedure: upload this
outline + `STATE.md`, say "continue from STATE.md."

---

## 13. Decisions to confirm before Phase 0

1. **Architecture** — hub-and-spoke is now *confirmed by QG §2.1* (teacher-core hub + quality-review
   + capability skills + protocol layer). Only sub-question: enforce quality both as the
   `quality-review` skill **and** as each skill's self-check? *Recommend: yes (defense in depth).*
2. **Repository home** — build here in Repo-1 per §7, or fold into the larger "Antigravity Kit"
   monorepo the toolkit references? *Recommend: here, unless you want it alongside the kit.*
3. **Standards scope (v1)** — CCSS (ELA/Math) + NGSS + a state-agnostic adapter is the default.
   Which **specific state standards**, if any, must ship in v1? (Accuracy/licensing is a real risk.)
4. **Grade-band scope (v1)** — full K–12, or start with one band (e.g., 3–5) for depth?
5. **The other 5 protocols** — QG §2.1 lists `metadata-schema`, `assumptions-protocol`,
   `standards-verification`, `conflict-protocol`, `failure-recovery` as **complete**, but only
   `quality-gates.md` was delivered. Do you have these to upload, or should I **draft them from the
   QG references** in Phase 0? *Recommend: upload if they exist; otherwise I draft + you review.*
6. **Quality Gates weighting** — confirm the **FULL 9-dimension weighting (§33.1)** is authoritative
   over the condensed 8-dimension version. *Recommend: yes.*
7. **Output formats** — `presentation-builder` implies slide decks (likely `.pptx` via the `pptx`
   skill). Also want polished **`.docx`/`.pdf`** for lessons/assessments (via the `docx`/`pdf`
   skills), or Markdown-first? *Recommend: build on the existing office skills.*
8. **Naming** — adopt the QG names verbatim and align expansion-skill names to the same style?
   *Recommend: yes.*

---

## 14. Risk Register (Charter V3 §21 + QG + additions)

| Risk | Sev | Mitigation |
|---|---|---|
| Undefined ontology | High | `shared/ontology/ontology.md` authored in Phase 0 before any skill |
| Scope expansion | High | Fixed v1 set (§4.2); new artifacts only via template + eval gate |
| Cross-protocol / cross-skill inconsistency | High | Single shared core + drift guard w/ QG §96 invariants |
| Standards accuracy / licensing | High | standards-verification protocol; cite versions; legal review |
| FERPA / student PII | High | No real PII; placeholders enforced as an Integrity/Safety auto-failure |
| 5 protocols referenced-but-missing | Med | Decision §13.5: upload or draft-from-QG in Phase 0 |
| QG weighting inconsistency (FULL vs condensed) | Med | Decision §13.6: FULL §33.1 authoritative |
| Skill under-/over-triggering | Med | Description optimization + "do NOT use for…" + trigger evals |
| Quality-as-theater (QG anti-patterns §89) | Med | Evidence-based decision records; independent quality-review; CI |

---

## 15. Status & next step

**Phase 0 is built and verified** (`tools/sync_check.py` PASS): repo scaffolding (§7); the `shared/`
core; all 6 protocols (`quality-gates.md` canonicalized from the provided 001–100; the other 5
drafted from QG references, marked pending review); the 5 governance docs; `CLAUDE.md` / `README.md`
/ `STATE.md`; `tools/sync_check.py` (QG §96 invariants) + `tools/new_skill.py` + the skill template;
a CI stub; and `teacher-core/SKILL.md` (the charter's `skill_mission_FULL.md`).

**Next — Phase A** in QG order:
`quality-review → lesson-planner (reference skill) → assessment-designer → presentation-builder`,
each via the skill-creator inner loop (§11.7). See `STATE.md` for the live dashboard and the open
items (review the 5 drafted protocols; confirm defaults).
