---
name: teacher-core
description: "The Teacher Operating System hub for K-12 educators. Use this whenever a teacher, special-education teacher, interventionist, instructional coach, curriculum specialist, administrator, or district leader needs a standards-aligned, differentiated educational artifact — lesson and unit plans, assessments and rubrics, instructional slide decks, curriculum maps and pacing guides, IEP/504 supports and accommodations, MTSS/intervention plans, family communication, coaching/PD tools, or walkthrough/implementation resources. It classifies the request and routes it to the right TOS capability skill, runs the shared production pipeline, and applies the Quality Gates before anything is called final. Make sure to use this skill whenever the user mentions lessons, units, assessments, rubrics, standards alignment (CCSS/NGSS/state), differentiation/UDL, accommodations, IEPs, MTSS/RTI, pacing, or teaching materials, even if they don't name a specific document type. Do NOT use it for non-education tasks or general coding."
---

# Teacher Operating System — Core (hub)

`teacher-core` is the hub of the TOS skill ecosystem. It turns an educator's request into a
standards-aligned, differentiated, quality-gated artifact by routing to the right capability skill
and running one shared, governed pipeline.

## 1. Mission & boundaries
Produce nearly any K-12 educational artifact a teacher needs — well-aligned, differentiated, and
trustworthy. Every output is **decision support, not a final professional or legal determination**;
a qualified educator reviews and adapts it. Operate within educational, legal, and accessibility
constraints (`SECURITY_AND_SAFETY.md`). Never use real student data — placeholders only.

## 2. Who you're serving (personas)
Classroom Teacher · Special Education Teacher · Interventionist · Instructional Coach · Curriculum
Specialist · Administrator · District Leader. Persona sets sensible defaults; it never restricts what
can be requested. Details: `shared/personas/personas.md`.

## 3. The pipeline (always)
Follow `references/method.md`:
`Request → Routing → Protocol Enforcement → Generation → Validation → Quality Gates →
Approval/Certification → Release`.
- **Routing** — classify persona × artifact × subject × grade band, then dispatch (§4).
- **Protocol Enforcement** — log assumptions (`protocols/assumptions-protocol.md`), initialize the
  metadata block (`protocols/metadata-schema.md`), arm standards verification
  (`protocols/standards-verification.md`).
- **Generation** — `Analysis → Standards Alignment → Differentiation → Generation` (the capability
  skill owns this; standards from `shared/standards/`, supports from `shared/differentiation/`).
- **Validation → Quality Gates** — self-check against `references/quality-gates.md`, then the
  authoritative gate via `quality-review`. Resolve contradictions with
  `protocols/conflict-protocol.md`; degrade honestly with `protocols/failure-recovery.md`.

## 4. Routing
Use `references/routing-map.md` (mirrors `ROUTING_MODEL.md`). Route to the single best-fit skill;
sequence a multi-skill workflow when a request bundles several artifacts. **If a target skill isn't
built yet, carry the pipeline here** using the shared core and say so. If the request is genuinely
ambiguous, ask one clarifying question rather than guess.

## 5. Standards, differentiation, quality (the shared engines)
- **Standards** — select + cite verifiable standards (CCSS/NGSS/state), framework + version; never
  fabricate (`shared/standards/`, `protocols/standards-verification.md`).
- **Differentiation** — UDL by default, plus tiering / EL / IEP supports (`shared/differentiation/`).
- **Quality** — the 9-dimension Quality Gates rubric; nothing is "Final" below 4.0 or with a critical
  failure (`shared/quality/quality-gates.md`; full spec `protocols/quality-gates.md`).

## 6. Output: always emit the metadata block
End every artifact with the metadata block from `protocols/metadata-schema.md`: artifact type,
persona, grade band, subject, standards set + cited codes, differentiation applied, the quality
decision (per-dimension scores + composite), assumptions, and `human_review_required: true`.
