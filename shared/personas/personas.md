# personas.md
## The TOS Personas
Canonical source (Charter V3 §13). Drives skill triggering (descriptions written in persona
language) and skill defaults (what a request from each persona usually needs).

Personas are *defaults, not gates* — any persona may request any artifact. They help the ecosystem
choose sensible defaults and route well.

| Persona | Typically creates | Default needs |
|---|---|---|
| **Classroom Teacher** | lessons, assessments, units, family communication | grade band + subject; standards-aligned; differentiated; ready to use |
| **Special Education Teacher** | accommodations, modifications, IEP supports, progress monitoring | tie to a student's plan (placeholder data); legal-boundary care; human-review emphasis |
| **Interventionist** | intervention plans, MTSS (Tier 1/2/3) documentation | tier + target skill; progress-monitoring cadence; data-light placeholders |
| **Instructional Coach** | observation tools, coaching resources, PD | adult-learning framing; evidence/look-fors; non-evaluative tone options |
| **Curriculum Specialist** | curriculum maps, pacing guides, scope & sequence | span across units/year; vertical+horizontal alignment; standards coverage |
| **School Administrator** | walkthrough tools, implementation & monitoring plans | school-level scope; implementation fidelity; summarizable outputs |
| **District Leader** | district frameworks, large-scale implementation resources | multi-school scope; equity + coherence; rollout/communication framing |
| **Charter Teacher** | lessons/assessments within charter flexibility | B.E.S.T./NGSSS apply; charter SOPs + calendar; sponsor expectations |
| **Charter Governing Board Member** | governance, sponsor reporting, board materials | independent-board governance; sponsor contract; governance training |
| **Private School Teacher** | lessons/assessments in the school's framework | `school_defined` standards (IB/AP/Cambridge/Montessori/classical/faith-based); school handbook/SOPs |
| **Private School Administrator** | governance, accreditation, scholarship reporting | private governance; accreditation framework; scholarship accountability |
| **Home Education Parent/Guardian** | parent-directed lessons, scope & sequence, portfolios, evaluations | `parent_selected` standards (advisory); annual-evaluation/portfolio support; flexible pacing |
| **Microschool / Co-op Leader** | multi-age/blended lessons, co-op logistics | mixed contexts; flexible grouping; often `parent_selected` or `school_defined` |

## Cross-cutting expectations for every persona

- **Standards handled per context applicability** (`shared/context/`): verifiable FL codes for
  public/charter/virtual; the school's framework for private; advisory objectives for home education —
  and **never fabricate a code** (`protocols/standards-verification.md`).
- **Differentiated by default** (`shared/differentiation/`).
- **No real student data** — placeholders only (`SECURITY_AND_SAFETY.md`).
- **Human-in-the-loop** — outputs are decision support, not final determinations.
- Passes **Quality Gates** before being called Final.
