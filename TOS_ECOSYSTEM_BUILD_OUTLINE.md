# Teacher Operating System (TOS)
# SKILL.md Ecosystem — Expanded Build Outline

Version: 1.0
Status: Plan / Pre-build (awaiting confirmation on the decision points in §13)
Supersedes for execution purposes: it operationalizes Master Project Charter V4.
Authoritative inputs read for this plan: Charter V2, Charter V2 (duplicate), Charter V3 §§12–24, Charter V4, and the iMessage Forensic Toolkit (read as a quality/engineering exemplar, not as TOS domain content).

---

## 0. How to read this document

This is the bridge between your **charters** (vision, phases, "what") and an actual
**ecosystem of Claude Agent Skills** (the "how"). It is written to be:

- **Faithful to the charters** — every phase, engine, artifact category, persona, and
  the governance model are carried through and mapped explicitly (see §2 and §12).
- **Executable** — it specifies the exact directory layout, the anatomy of each skill,
  the shared infrastructure, and an ordered, phase-gated build plan with exit criteria.
- **Self-preserving** — per your preservation theme, this file plus `STATE.md` (created
  in Phase 0) plus the charters form the recovery package for future sessions.

It does **not** build anything yet. It is the plan you asked for. Build begins only
after the decision points in §13 are confirmed.

---

## 1. What a "SKILL.md ecosystem" actually is (grounding)

A **Skill** is a directory containing a `SKILL.md` file: YAML frontmatter (`name`,
`description`) plus a markdown body of instructions, optionally bundling `references/`,
`scripts/`, and `assets/`. Claude loads skills by **progressive disclosure**:

1. **Metadata** (name + description) — always in context (~100 words). The `description`
   is the *only* trigger signal; it must say *what the skill does* **and** *when to use it*.
2. **SKILL.md body** — loaded when the skill triggers (target < 500 lines).
3. **Bundled resources** — loaded only when needed; scripts can execute without being
   read into context.

This three-level model is the single most important constraint shaping the architecture
below: the charter's enormous capability surface (lesson plans → IEPs → MTSS → newsletters)
cannot live in one 500-line file, so it must be **decomposed into focused skills that share
a governed core** and pull detail from references on demand.

**Reconciling "a skill" (singular, per Charter V2) with "ecosystem" (plural):** the product
is delivered as a **hub-and-spoke ecosystem** — one orchestrator skill that *behaves* as the
single "Teacher Operating System," plus focused capability skills that all share one governed
core. To the user it feels like one system; to the maintainer it is a clean, testable set of
parts.

---

## 2. Charter → Build mapping (nothing dropped)

| Charter element | Source | Where it lands in this plan |
|---|---|---|
| Phases 0, A, B, C, D, E | V2, V4 | §11 Build Plan (one build phase per charter phase) |
| 7-stage production pipeline | V3 §15, V4 | §5 The Method (canonical pipeline) |
| 8 Engines (Lesson, Assessment, Curriculum, Intervention, IEP, Differentiation, Verification, Quality) | V3 §16 | §4 Skills (capability skills) + §6 Shared Core (cross-cutting engines) |
| 9 Artifact categories | V3 §14 | §4 Skill Inventory (one capability skill per category) |
| 7 Personas / users | V3 §13 | §3 Personas; encoded in `shared/personas/` and triggering |
| Repository architecture (11 dirs) | V3 §17 | §7 Repository Layout (mapped onto skills + shared core) |
| Quality Gates (final authority) | V3 §19 | §8 Governance & Quality (Quality Gates rubric) |
| Phase B protocols (Assumptions, Standards Verification, Metadata, Conflict, Failure Recovery, Repository Discovery) | V2, V4 | §8 Governance (`shared/governance/`) |
| Assumptions & Constraints; Risk Register; Success Metrics | V3 §§20–22 | §9 Safety/Constraints, §14 Risks, §10 Success Metrics |
| Preservation & Recovery | all charters | §12 Preservation (`STATE.md` + this file) |
| Engineering/quality bar, drift guard | iMessage toolkit | §8.4 Drift Guard, §11 Phase D, §9 quality bar |

---

## 3. Personas (the "who," from V3 §13)

These drive both skill **triggering** (descriptions written in their language) and skill
**defaults** (what a request from each persona usually needs). Encoded canonically in
`shared/personas/personas.md`.

1. Classroom Teacher — lessons, assessments, units, communication
2. Special Education Teacher — accommodations, modifications, IEP supports, progress monitoring
3. Interventionist — intervention plans, MTSS artifacts
4. Instructional Coach — observation tools, coaching resources, PD
5. Curriculum Specialist — curriculum maps, pacing guides, alignment
6. School Administrator — walkthroughs, implementation plans, monitoring
7. District Leader — district frameworks, large-scale implementation

---

## 4. The Skill Inventory (the ecosystem)

### 4.1 Architecture: hub-and-spoke

- **1 orchestrator (hub):** `teacher-operating-system` — owns mission, personas, the
  7-stage method, and *routing*. It classifies a request (artifact × persona × standards ×
  grade band) and routes to the right capability skill; if installed alone, it can run the
  full pipeline itself from its own references. This is the charter's "skill_mission_FULL.md"
  realized.
- **8 capability skills (spokes):** one per artifact category (V3 §14), each owning the
  artifacts, templates, and domain method for its area.
- **1 shared core** (`shared/`, see §6): the cross-cutting engines (Standards,
  Differentiation, Quality/Verification) + governance + ontology + personas. Single source
  of truth, synced into each skill at package time and policed by a drift guard (§8.4).

### 4.2 Capability skills (v1 target set)

| # | Skill name | Charter category | Primary artifacts | Maps to engine(s) |
|---|---|---|---|---|
| 1 | `lesson-design` | Instructional | lesson plans, unit plans, guided notes, exit tickets, centers, projects | Lesson |
| 2 | `assessment-builder` | Assessment | formative & summative assessments, rubrics, performance tasks, item banks | Assessment |
| 3 | `curriculum-mapping` | Curriculum | curriculum maps, pacing guides, scope & sequence | Curriculum |
| 4 | `special-education-support` | Special Education | IEP supports, accommodations, modifications, progress monitoring | IEP |
| 5 | `intervention-mtss` | Intervention | Tier 1/2/3 plans, MTSS documentation | Intervention |
| 6 | `family-communication` | Communication | newsletters, parent communication, reports | (Generation + Quality) |
| 7 | `professional-learning` | Professional Learning | observation tools, coaching resources, PD plans | (Generation + Quality) |
| 8 | `school-administration` | Administrative | walkthrough tools, implementation & monitoring plans | (Generation + Quality) |

The 9th charter category, **AI Artifacts**, is treated as an *internal/meta* concern and
folded into the shared core + Phase E (it is not a teacher-facing capability skill).

Cross-cutting engines (**Differentiation, Verification, Quality**) are deliberately **not**
standalone invokable skills — skills cannot cleanly call one another. They live in the shared
core (§6) and are pulled in by every capability skill, which keeps them consistent and
testable.

### 4.3 Sequencing

`lesson-design` is built **first and complete** as the reference implementation that proves
the whole pipeline and the skill template; the other seven are then produced by cloning the
proven pattern. (See §11, Phase A.)

---

## 5. The Method — canonical 7-stage pipeline (V3 §15 + V4)

Every skill applies the same governed pipeline; only the domain specifics change. It is
authored once in `shared/method/method.md` and referenced by each skill's `references/method.md`.

```
Request
  → 1. Analysis            (intake: persona, grade band, subject, constraints, assumptions logged)
  → 2. Standards Alignment (select & cite standards; record the standards set + version)
  → 3. Differentiation     (UDL, tiering, EL supports, IEP accommodations as applicable)
  → 4. Generation          (produce the artifact from the domain template)
  → 5. Verification        (factual/standards/alignment checks; the "did we build the right thing")
  → 6. Quality Review      (Quality Gates rubric; the "did we build it well")
  → (7. Governance Review) (assumptions/conflict/failure protocols; escalate to human where required)
  → Final Artifact         (+ metadata block)
```

Verification (5) and Quality (6) are distinct on purpose: verification is *correctness/alignment*,
quality is the *rubric bar*. Both must pass before an artifact is emitted.

---

## 6. Shared Core (`shared/`) — the cross-cutting engines & governance

Single source of truth, reused by every skill. This is the heart of "one operating system."

```
shared/
├── method/
│   └── method.md                 # the canonical 7-stage pipeline (§5)
├── personas/
│   └── personas.md               # the 7 personas + their default needs (§3)
├── ontology/
│   └── ontology.md               # canonical vocabulary (artifact, standard, accommodation, tier…)
├── standards/                    # STANDARDS ENGINE
│   ├── standards-framework.md    # how to select, cite, and verify standards
│   ├── ccss.md                   # Common Core (ELA/Math) reference
│   ├── ngss.md                   # Next Gen Science reference
│   └── state-standards-model.md  # state-agnostic adapter pattern (+ named states per §13.3)
├── differentiation/              # DIFFERENTIATION ENGINE
│   ├── udl.md                    # Universal Design for Learning
│   ├── tiering.md                # readiness/interest/profile tiering
│   ├── english-learners.md       # WIDA-style EL supports
│   └── accommodations-catalog.md # IEP/504 accommodations & modifications
├── quality/                      # QUALITY + VERIFICATION ENGINES
│   ├── quality-gates.md          # the Quality Gates rubric (final authority, §8)
│   ├── verification-checklists.md# per-artifact correctness/alignment checks
│   └── readability-age.md        # reading-level & age-appropriateness checks
└── governance/                   # PHASE B PROTOCOLS
    ├── assumptions-protocol.md
    ├── standards-verification.md
    ├── metadata-schema.md        # the metadata block every artifact carries
    ├── conflict-protocol.md
    ├── failure-recovery.md
    └── repository-discovery.md
```

These files are the **canonical copies**. At package time they are synced into each skill's
`references/` so every shipped skill is self-contained; the drift guard (§8.4) guarantees the
copies never diverge from canon.

---

## 7. Repository Layout (maps V3 §17 onto skills)

```
repo-root/
├── CLAUDE.md                      # conventions: branch rules, drift guard, build/test commands
├── README.md                     # top-level: what the ecosystem is, how to install skills
├── TOS_ECOSYSTEM_BUILD_OUTLINE.md# this document
├── STATE.md                      # live status dashboard + recovery pointer (Phase 0)
├── skills/
│   ├── teacher-operating-system/ # the orchestrator (hub)
│   ├── lesson-design/
│   ├── assessment-builder/
│   ├── curriculum-mapping/
│   ├── special-education-support/
│   ├── intervention-mtss/
│   ├── family-communication/
│   ├── professional-learning/
│   └── school-administration/
├── shared/                       # canonical cross-cutting core (§6)
├── tools/
│   ├── sync_check.py             # drift guard (canonical shared ⇄ per-skill copies)
│   ├── new_skill.py              # scaffolds a skill from the standard template (§4.2 anatomy)
│   └── package_skill.py          # builds installable .skill bundles (Phase D)
├── examples/                     # cross-skill Example Library (Phase C / V3 §17)
└── .github/workflows/ci.yml      # drift guard + eval smoke tests (Phase D)
```

Charter `repository/` dirs (`skill/`, `educational-artifacts/`, `standards/`,
`differentiation/`, `generation/`, `quality/`, `governance/`, `examples/`, `ontology/`,
`ai/`, `deployment/`) map cleanly: `skill/`→`skills/`; `standards|differentiation|quality|governance|ontology`→`shared/`;
`generation`→the per-skill templates+scripts; `educational-artifacts`→per-skill `references/artifact-types.md`;
`examples`→`examples/`; `ai`+`deployment`→Phase E.

---

## 8. Governance & Quality

### 8.1 Quality Gates (the final authority, V3 §19)
Operationalized as a **rubric** in `shared/quality/quality-gates.md`: a checklist an artifact
must pass before emission (standards cited & correct; differentiation present & appropriate;
age/reading-level appropriate; accessible; bias/representation reviewed; factually sound;
metadata complete; human-review note attached). No artifact is "Final" until it passes.
*Note:* the charters cite "Quality Gates sections 001–100 reconstructed" as completed work,
but those artifacts are **not in the uploads** — see decision §13.5.

### 8.2 Phase B protocols (`shared/governance/`)
Concrete, short, enforceable documents: **Assumptions Protocol** (log assumptions, surface
them in output), **Standards Verification** (every cited standard must be verifiable),
**Metadata Schema** (the block every artifact carries — see §8.3), **Conflict Protocol**
(what to do when inputs/standards conflict), **Failure Recovery** (graceful degradation +
what to tell the user), **Repository Discovery** (how a skill locates the shared core).

### 8.3 Metadata block (every artifact)
A required trailer on each generated artifact: artifact type, persona, grade band, subject,
standards set + version, differentiation applied, Quality Gates result, assumptions made,
and an explicit **human-review-required** flag (per V3 §12: "not a replacement for
professional judgment").

### 8.4 Drift Guard (borrowed from the iMessage toolkit)
`tools/sync_check.py` mirrors the toolkit's `sync_check.py`: it asserts **invariants**, not a
textual diff. Invariants include: (a) each skill's synced `references/standards.md`,
`differentiation.md`, `quality-gates.md` match the canonical `shared/` copies; (b) every
capability `SKILL.md` references the 7-stage method; (c) every skill emits the metadata block;
(d) every skill carries the human-review flag; (e) no skill ships placeholder TODOs. Exit 0 =
clean, exit 1 = drift report. Runs in CI (Phase D) and after every shared-core change.

---

## 9. Safety & Constraints (V3 §20, expanded for education)

Beyond Quality Gates, an explicit education-safety layer (this is the "AI Safety Coverage"
success metric, V3 §22):

- **Student-data / FERPA:** never request, infer, or store real student PII; all examples use
  placeholders ("Student A"). Enforced by a verification check.
- **Human-in-the-loop:** every artifact is decision-support, not a final professional/legal
  determination — explicit on IEP/504 and intervention outputs especially.
- **Accessibility:** UDL by default; outputs check against readability/age and accessibility.
- **Bias & representation:** a review step for names, contexts, and examples.
- **Legal/policy boundary:** IEP/504/MTSS outputs state they must be validated against the
  student's actual plan and local/state policy.

---

## 10. Success Metrics (V3 §22) — made measurable

| Charter metric | Concrete measure in this plan |
|---|---|
| Artifact Coverage | # artifact types with a template + gold example + passing eval |
| Standards Coverage | # standards frameworks wired into the Standards engine (CCSS, NGSS, + states) |
| Differentiation Coverage | each artifact type has UDL + tiering + EL + IEP variants verified |
| Quality Coverage | % of eval outputs passing Quality Gates |
| Governance Coverage | all 6 Phase B protocols implemented + enforced by drift guard |
| AI Safety Coverage | FERPA/bias/accessibility/human-review checks present & tested |

A small analytics script (Phase E) renders these into `STATE.md` automatically.

---

## 11. The Build Plan (phase-gated; one build phase per charter phase)

Each phase lists **Objective → Deliverables → Exit criteria**. Inside Phases A–C, each
individual skill is built with the **skill-creator inner loop** (§11.7).

### Phase 0 — Skill Architecture & Foundations  *(charter Phase 0)*
- **Objective:** stand up the skeleton everything else hangs on.
- **Deliverables:** repo scaffolding (§7); `CLAUDE.md` (branch/drift/test rules);
  `STATE.md`; the **orchestrator** `teacher-operating-system/SKILL.md` (mission, personas,
  method, routing) — the charter's `skill_mission_FULL.md`; the **shared core** (§6) authored;
  the **standard skill template** + `tools/new_skill.py`; `tools/sync_check.py` (drift guard).
- **Exit:** a throwaway skill scaffolds from the template, passes the drift guard, and a smoke
  eval triggers the orchestrator and routes correctly.

### Phase A — Educational Foundations  *(charter Phase A: A1 artifacts, A2 standards, A3 differentiation, A4 generation, A5 quality)*
- **Objective:** prove the pipeline end-to-end, then replicate.
- **Deliverables:** `lesson-design` built **completely** (references, templates, scripts,
  examples, evals) as the reference skill; then `assessment-builder`, `curriculum-mapping`,
  `special-education-support`, `intervention-mtss`, `family-communication`,
  `professional-learning`, `school-administration` cloned from the proven pattern.
- **Exit:** every capability skill triggers on realistic prompts, produces a gold-standard
  artifact, and passes Quality Gates + its evals.

### Phase B — Governance Infrastructure  *(charter Phase B)*
- **Objective:** make governance real and enforced.
- **Deliverables:** finalize the 6 Phase B protocols; wire the metadata block and
  assumptions/conflict/failure handling into every skill; standards-verification tooling.
- **Exit:** every artifact carries metadata; conflicts/failures handled deterministically;
  drift guard green across all skills.

### Phase C — Operational Integration  *(charter Phase C: C1 integration, C2 operations, C3 example library)*
- **Objective:** make the spokes work as one system.
- **Deliverables:** orchestrator cross-skill workflows (e.g., "build a unit + its assessments +
  differentiation + a parent letter" in one pass); operations docs; the populated
  **Example Library** (`examples/`).
- **Exit:** multi-artifact workflows run end-to-end; example library covers each skill.

### Phase D — Repository Hardening  *(charter Phase D)*
- **Objective:** reach the iMessage-toolkit quality bar.
- **Deliverables:** `package_skill.py` producing installable `.skill` bundles; CI running the
  drift guard + eval smoke tests on every change; an education **security/safety review** plus
  invariant checks; comprehensive per-skill READMEs and a top-level README; semantic versioning.
- **Exit:** CI green; skills install cleanly; docs match the exemplar's depth.

### Phase E — Advanced Architecture  *(charter Phase E: E1 knowledge, E2 AI, E3 analytics, E4 deployment)*
- **Objective:** the "advanced" layer.
- **Deliverables:** ontology/knowledge architecture hardening (E1); AI systems — e.g.,
  LLM-as-judge for Quality Gates and an AI-artifacts module (E2); analytics rendering the §10
  metrics into `STATE.md` (E3); deployment & update/distribution strategy (E4).
- **Exit:** success-metric dashboard exists; deployment/update path documented.

### 11.7 The per-skill inner loop (skill-creator methodology)
For each skill in Phases A–C: **draft `SKILL.md`** → write **2–3 realistic test prompts** →
run *with-skill vs. baseline* → review outputs (eval-viewer) → **iterate** → **optimize the
`description`** for trigger accuracy → **package**. Descriptions are written specific and
slightly "pushy" to combat under-triggering, and scoped with explicit "do NOT use for…" to
avoid cross-skill collisions (the docx skill is the model here).

---

## 12. Preservation & Recovery (carries the charter theme)

- **Recovery package:** the four charters + this outline + `STATE.md`.
- **`STATE.md`** is the live dashboard: phase status, per-skill status, last drift-guard
  result, success metrics, and a "resume here" pointer. Updated at every phase boundary and
  after each skill ships.
- **Recovery procedure:** upload this outline + `STATE.md` and say "continue from STATE.md."

---

## 13. Decisions to confirm before Phase 0 (genuine forks)

These are the only places the plan branches; my recommendation is given first.

1. **Architecture — ecosystem vs. mega-skill.** *Recommend:* the hub-and-spoke ecosystem in
   §4 (multiple installable skills + shared core). Alternative: a single mega-skill that
   internalizes everything via references. The ecosystem scales better and is more testable.
2. **Repository home.** *Recommend:* build here in this repo as the layout in §7. Alternative:
   fold into the larger "Antigravity Kit" monorepo referenced by the toolkit
   (`src/ui-ux-pro-max/`, `tools/…`). Which is the intended home?
3. **Standards scope for v1.** CCSS (ELA/Math) + NGSS + a state-agnostic adapter is the
   default. Which **specific state standards** (if any) must ship in v1? (Standards content
   accuracy/licensing is a real constraint — §14.)
4. **Grade-band scope for v1.** Full K–12, or start with one band (e.g., 3–5) to reach depth
   faster, then widen?
5. **Quality Gates artifacts.** The charters cite "sections 001–100 reconstructed" as done,
   but they aren't in the uploads. Do you have them to provide, or should I (re)construct the
   Quality Gates rubric from the charter intent (§8.1)?
6. **Output formats.** Markdown by default; do you also want polished **.docx/.pdf** outputs?
   (If so, the capability skills can build on the existing `docx`/`pdf` skills rather than
   re-implementing document generation.)

---

## 14. Risk Register (V3 §21 + additions) & mitigations

| Risk | Sev | Mitigation |
|---|---|---|
| Undefined ontology | High | `shared/ontology/ontology.md` authored in Phase 0 before any skill |
| Scope expansion | High | Fixed v1 skill set (§4.2); new artifacts only via the template + eval gate |
| Cross-protocol inconsistency | High | Single shared core + drift guard (§8.4) |
| Standards accuracy / licensing | High | Standards-verification protocol; cite versions; legal review of bundled standards |
| FERPA / student PII | High | No real PII; placeholders enforced by a verification check (§9) |
| Skill under-/over-triggering | Med | Description optimization + "do NOT use for…" scoping; trigger evals (§11.7) |
| Ecosystem drift across skills | Med | Drift guard in CI (§8.4, Phase D) |
| Quality Gates source missing | Med | Decision §13.5; reconstruct from charter intent if not provided |

---

## 15. Immediate next step (on approval)

Begin **Phase 0**: scaffold the repo (§7), author the shared core (§6) and `CLAUDE.md`/`STATE.md`,
write the orchestrator `teacher-operating-system/SKILL.md` (the charter's `skill_mission_FULL.md`),
and stand up `tools/new_skill.py` + `tools/sync_check.py`. Then build `lesson-design` end-to-end
(Phase A) as the reference skill before replicating the pattern.
