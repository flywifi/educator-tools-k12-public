# Teacher Operating System (TOS)

A set of AI assistants that help K–12 teachers create and double-check the everyday materials of
teaching — lesson and unit plans, assessments and rubrics, slide decks, curriculum maps, IEP/504
supports, intervention (MTSS) plans, family messages, and coaching/PD resources.

Everything it makes is aligned to your state's standards, built with differentiation in mind, and
**flagged for your review** — it's a strong starting point, not a final decision. It never uses real
student information; examples use placeholders only.

## What you can do with it
- Draft a standards-aligned lesson or unit plan
- Build assessments, rubrics, and answer keys
- Turn a lesson into a slide deck
- Map curriculum across a unit or a year
- Get differentiation and accommodation ideas for diverse learners (special education, English
  learners, gifted)
- Write family communication — and translate it
- Plan interventions / MTSS supports
- Prepare coaching and professional-learning materials

## Who it's for
Classroom teachers first — plus special educators, instructional coaches, and school administrators.
You don't need to be technical to use it.

## How you use it
Ask in plain language — e.g., *"Make me a 5th-grade fractions lesson aligned to my standards"* — and
the right assistant takes it from there. For a complete real example (a teacher setting up and
producing a lesson start to finish), see
**[docs/END_TO_END_WALKTHROUGH.md](docs/END_TO_END_WALKTHROUGH.md)**.

Using it in Claude Code: install the plugin with
`/plugin marketplace add flywifi/educator-tools-k12-public`, then
`/plugin install teacher-operating-system@tos-marketplace`.

## Under the hood (for the curious or technical)
You don't need any of this to use TOS — but here's how it's built:
- **A coordinator** (`skills/core/teacher-core`) reads your request and sends it to the right
  specialized skill.
- **Specialized skills** do the work (lesson planning, assessment design, special-education support,
  and so on), grouped under `skills/` as `core/`, `educator/`, `operations/`, and small
  single-purpose `atoms/`.
- **Shared engines** under `shared/` give every skill one source of truth for standards,
  differentiation, and quality.
- **A quality check** runs before anything is called "done," and an **automated consistency checker**
  (`tools/sync_check.py`) keeps the shared rules each skill carries identical to the originals.

## Learn more
- **[docs/END_TO_END_WALKTHROUGH.md](docs/END_TO_END_WALKTHROUGH.md)** — a real teacher, start to
  finish (best place to begin).
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — how the pieces fit together.
- **[docs/QUALITY_MODEL.md](docs/QUALITY_MODEL.md)** — how outputs are checked for quality.
- **[protocol-layer/quality-gates.md](protocol-layer/quality-gates.md)** — the rules every output
  must pass before it's considered ready.
- **[CLAUDE.md](CLAUDE.md)** — conventions for developers working in this repo.

## What these words mean (quick glossary)
- **Skill** — one focused AI assistant (e.g., the lesson planner).
- **Coordinator (`teacher-core`)** — the skill that decides which other skill handles your request.
- **Quality gates** — a checklist every output must pass before it's considered ready.
- **Quality Ledger** — a running log of those quality decisions, so there's a record.
- **Drift guard (`tools/sync_check.py`)** — an automated check that keeps each skill's copy of the
  shared rules identical to the originals.
- **Decision support** — you get a strong draft to review and adjust; you, the educator, always make
  the final call.
