# Skills catalog

The Teacher Operating System is a set of focused AI assistants ("skills"). One **coordinator**
(`teacher-core`) reads each request and routes it to the right specialized skill; those skills
produce the actual materials; and `quality-review` checks them before they're considered done. Every
skill shares one source of truth in `shared/` and `protocol-layer/`, and an automated checker
(`tools/sync_check.py`) keeps each skill's copy of those shared rules identical to the originals.

| Skill | Role | Produces |
|---|---|---|
| `teacher-core` | Hub / router / orchestrator | intake, routing, multi-skill workflows |
| `quality-review` | Governance | Quality-Gates evaluations + decision records (`scripts/score.py`) |
| `lesson-planner` | Capability (reference) | lessons, units, guided notes, exit tickets, centers, projects |
| `assessment-designer` | Capability | assessments, rubrics, performance tasks, item banks |
| `presentation-builder` | Capability | instructional slide decks (renders via the `pptx` skill) |
| `curriculum-mapping` | Capability | curriculum maps, pacing guides, scope & sequence |
| `special-education-support` | Capability | accommodation/modification plans, IEP goal drafts, progress monitoring |
| `intervention-mtss` | Capability | Tier 1/2/3 plans, MTSS docs, progress monitoring |
| `family-communication` | Capability | newsletters, parent letters, conference points, report comments |
| `professional-learning` | Capability | observation tools, coaching guides, PD plans |
| `school-administration` | Capability | walkthrough tools, implementation & monitoring plans |

## Anatomy (every skill)
`SKILL.md` + `references/` (incl. synced `method.md` + `quality-gates.md`) + `assets/templates/` +
`scripts/` + `examples/` + `evals/evals.json`.

## Working with skills
```bash
python3 tools/new_skill.py <name>      # scaffold a new skill (drift-clean)
python3 tools/sync_check.py            # drift guard — must pass
python3 tools/package_skill.py --all   # build installable .skill bundles into dist/
```
Edit canonical files in `shared/` or `protocol-layer/` — never a skill's synced copy. See `../CLAUDE.md`.
