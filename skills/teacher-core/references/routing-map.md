# routing-map.md
## teacher-core routing table
Skill-local copy of the routing logic in `ROUTING_MODEL.md`. Route on **artifact type** first,
using persona/subject/grade band as supporting signals.

| Artifact the user wants | Route to | Status |
|---|---|---|
| lesson plan, unit, guided notes, exit ticket, centers, project | `lesson-planner` | Phase A |
| formative/summative assessment, rubric, performance task, item bank | `assessment-designer` | Phase A |
| slide deck / instructional presentation | `presentation-builder` | Phase A |
| evaluate/score an existing artifact against the gates | `quality-review` | Phase A |
| curriculum map, pacing guide, scope & sequence | `curriculum-mapping` | Expansion |
| IEP support, accommodation, modification, progress monitoring | `special-education-support` | Expansion |
| Tier 1/2/3 plan, MTSS documentation | `intervention-mtss` | Expansion |
| newsletter, parent communication, report | `family-communication` | Expansion |
| observation tool, coaching resource, PD plan | `professional-learning` | Expansion |
| walkthrough, implementation/monitoring plan | `school-administration` | Expansion |

## Rules
- **Single best match** → that skill. **Bundled request** → sequence one skill per artifact, each
  gated by `quality-review` (multi-skill workflow, Phase C).
- **Target not built yet** → `teacher-core` carries the pipeline using the shared core and labels
  the output's provenance.
- **Ambiguous** → ask one clarifying question (`protocols/assumptions-protocol.md`) rather than guess.
- **Always** finish with the Quality Gates before declaring an artifact final.
