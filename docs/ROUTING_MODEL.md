# ROUTING_MODEL.md
## Teacher Operating System (TOS) — Routing Model
Governance document (Quality Gates §2.1). How `teacher-core` classifies a request and routes it to
the right capability skill (pipeline step 1).

> **Engine (shared router).** Routing is **data-driven**: the canonical registry is
> `shared/routing/routing.json` and the scorer is `shared/routing/router.py`, consumed by **both**
> `teacher-core` and `meeting-classifier` so the logic lives in one place.
> `router.route({text | artifact_type | meeting_type, persona})` returns the recommended skill +
> confidence + alternates (+ a **minority report** on a tie). The table below is the human-readable
> companion; when a new skill ships, add it to `routing.json` (and `shared/ontology/artifact-types.json`)
> and `tools/sync_check.py` verifies every route target is a real skill.

---

## 1. Classification signals
From the request (and conversation), determine:
- **Artifact type** — what deliverable is asked for (lesson, assessment, rubric, slide deck, IEP
  support, intervention plan, newsletter, …). Strongest signal.
- **Persona** — who is asking (`shared/personas/personas.md`). Sets defaults.
- **Subject** — Math / ELA / Science / … (selects the standards framework).
- **Grade band** — K-2 / 3-5 / 6-8 / 9-12 (assume + log if missing).

## 2. Artifact → skill routing table

| Artifact | Skill | Status |
|---|---|---|
| lesson plan, unit, guided notes, exit ticket, centers, project | `lesson-planner` | available |
| formative/summative assessment, rubric, performance task, item bank | `assessment-designer` | available |
| slide deck / instructional presentation | `presentation-builder` | available |
| run the Quality Gates on any artifact | `quality-review` | available |
| curriculum map, pacing guide, scope & sequence | `curriculum-mapping` | available |
| IEP support, accommodation, modification, progress monitoring | `special-education-support` | available |
| Tier 1/2/3 plan, MTSS documentation | `intervention-mtss` | available |
| newsletter, parent communication, report | `family-communication` | available |
| observation tool, coaching resource, PD | `professional-learning` | available |
| walkthrough, implementation/monitoring plan | `school-administration` | available |
| classify a meeting/invite + route it (faculty, observation, IEP/504, conference, MTSS, planning, PD, safety) | `meeting-classifier` | available |
| diagnose/repair the ecosystem itself (skill + engine health, audit-trail diagnosis, impact analysis, repair plan) | `skill-health` | available |
| validate one output before it ships (artifact schema/rules + document structure) | `output-validator` | available |
| apply an approved repair plan minimally (mechanical fixes; judgment stays human) | `skill-repair` | available |

## 3. Routing rules
- **Single best match:** route to the one skill whose artifact family fits. If a request bundles
  several (e.g., "a unit *and* its assessments *and* a parent letter"), `teacher-core` sequences a
  **multi-skill workflow** (Phase C) — one skill per artifact, each gated by `quality-review`.
- **No spoke yet / ambiguous:** if the target skill isn't built yet, `teacher-core` **carries the
  pipeline itself** using the shared core, and labels the output's provenance. If genuinely
  ambiguous, ask one clarifying question rather than guess (`protocols/assumptions-protocol.md`).
- **Meeting-centered requests:** when the request is about a meeting, invite, or calendar event,
  classify it via `meeting-classifier` first — it returns the meeting type, request intent, IEP/504
  advisories, the subject student/guardians, and the recommended owner skill (then route there).
- **Always gate:** whatever produces the artifact, the final stage is the Quality Gates
  (`quality-review` / the operational rubric) before "Final."

## 4. Examples
- *"Make a 3rd-grade fractions lesson"* → `lesson-planner` (Phase A); subject Math, band 3-5,
  standard `CCSS.MATH.CONTENT.3.NF.*`.
- *"Build an exit ticket and a rubric for that lesson"* → `assessment-designer`.
- *"Turn it into slides for tomorrow"* → `presentation-builder` (builds on the `pptx` skill).
- *"Is this lesson any good?"* → `quality-review` (score it against the gates).
