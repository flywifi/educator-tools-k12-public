# routing-map.md
## teacher-core routing table
Skill-local copy of the routing logic in `ROUTING_MODEL.md`. Route on **artifact type** first,
using persona/subject/grade band as supporting signals. The canonical, data-driven source is the
**shared router** (`shared/routing/routing.json` + `router.py`) — call
`router.route({text, artifact_type, persona})` to get the skill + confidence + alternates; this table
is the readable companion.

| Artifact the user wants | Route to | Status |
|---|---|---|
| lesson plan, unit, guided notes, exit ticket, centers, project | `lesson-planner` | available |
| formative/summative assessment, rubric, performance task, item bank | `assessment-designer` | available |
| slide deck / instructional presentation | `presentation-builder` | available |
| evaluate/score an existing artifact against the gates | `quality-review` | available |
| curriculum map, pacing guide, scope & sequence | `curriculum-mapping` | available |
| IEP support, accommodation, modification, progress monitoring | `special-education-support` | available |
| Tier 1/2/3 plan, MTSS documentation | `intervention-mtss` | available |
| newsletter, parent communication, report | `family-communication` | available |
| observation tool, coaching resource, PD plan | `professional-learning` | available |
| walkthrough, implementation/monitoring plan | `school-administration` | available |
| classify a meeting/invite + route it (observation, IEP/504, conference, MTSS, planning, PD, safety) | `meeting-classifier` | available |
| diagnose/repair the ecosystem itself (skill + engine health, diagnosis, impact, repair plan) | `skill-health` | available |

## Rules
- **Single best match** → that skill. **Bundled request** → sequence one skill per artifact, each
  gated by `quality-review` (multi-skill workflow, Phase C).
- **Target not built yet** → `teacher-core` carries the pipeline using the shared core and labels
  the output's provenance.
- **Ambiguous** → ask one clarifying question (`protocols/assumptions-protocol.md`) rather than guess.
- **Always** finish with the Quality Gates before declaring an artifact final.
