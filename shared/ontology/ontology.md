# ontology.md
## TOS Canonical Vocabulary
Canonical source. One name per concept so skills, protocols, and metadata stay consistent
(QG Risk §21: "undefined ontology" is the top risk — this file mitigates it).

---

## Core entities

- **Artifact** — any output the ecosystem produces (lesson plan, rubric, slide deck, IEP support…).
  Each artifact has a *type*, a *metadata block*, and a *quality decision*.
- **Artifact type** — a named, specified kind of artifact (see each skill's `artifact-types.md`).
- **Skill** — a packaged capability (`SKILL.md` + bundled resources). The **hub** is
  `teacher-core`; **spokes** are capability skills; `quality-review` is the governance skill.
- **Engine** — a cross-cutting capability used by many skills, implemented in `shared/`:
  Standards, Differentiation, Quality/Verification (Charter V3 §16).
- **Protocol** — a governance rule set in `protocols/` (the 6 files).

## Educational terms

- **Standard** — a coded learning expectation from a *framework* (CCSS, NGSS, a state set) at a
  *version*. Always cited with framework + version + code.
- **Grade band** — K-2 (primary), 3-5 (upper elementary), 6-8 (middle), 9-12 (high). Individual
  grades (K, 1, …, 12) roll up into bands.
- **Objective** — a specific, measurable learning goal for an artifact.
- **Differentiation** — adjusting content/process/product for learner variability. Channels: **UDL**
  (proactive design), **tiering** (readiness/interest/profile), **EL supports** (English learners),
  **accommodations/modifications** (IEP/504).
  - *Accommodation* = change in **how** a student accesses/demonstrates learning (expectation
    unchanged).
  - *Modification* = change in **what** a student is expected to learn (expectation changed).
- **MTSS** — Multi-Tiered System of Supports. **Tier 1** universal, **Tier 2** targeted, **Tier 3**
  intensive.
- **Formative assessment** — checks for learning *during* instruction. **Summative** — measures
  learning *at the end*.

## Quality terms (from Quality Gates)

- **Gate** — an evidence-based decision point (PASS / FAIL / REMEDIATION REQUIRED).
- **Dimension** — a 0–5 scored quality category (9 of them; Integrity highest).
- **Composite** — weighted sum of dimension scores; thresholds map it to a decision.
- **Critical failure** — a condition that forces Rejected regardless of composite (e.g.,
  fabrication).
- **Certification level** — Development → Review → Production → Governance Certified → Repository
  Certified.
- **Decision record** — the auditable record of a quality decision (`protocols/metadata-schema.md`).

## Persona

- **Persona** — the role making the request (7 of them; `shared/personas/personas.md`). A default
  lens, not a restriction.
