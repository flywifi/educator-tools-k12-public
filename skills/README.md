# Skills catalog

The Teacher Operating System ships as a hub-and-spoke set of Claude Agent Skills. The hub routes;
the spokes produce artifacts; `quality-review` gates them. All share the governed core (`shared/`,
`protocol-layer/`) via synced references; the drift guard (`tools/sync_check.py`) keeps them in sync.

Skills are sub-grouped: `core/` (hub + governance + health), `educator/` (content capability
skills), `operations/` (tools/feeds/profile), and `atoms/` (single-operation sub-skills).

| Skill | Group | Role | Produces |
|---|---|---|---|
| `teacher-core` | core | Hub / router / orchestrator | intake, routing, multi-skill workflows |
| `quality-review` | core | Governance | Quality-Gates evaluations + decision records (`scripts/score.py`) |
| `output-validator` | core | Governance | structural/metadata validation of artifacts |
| `skill-health` | core | Maintenance | ecosystem health checks |
| `skill-repair` | core | Maintenance | guided repair of failing skills |
| `lesson-planner` | educator | Capability (reference) | lessons, units, guided notes, exit tickets, centers, projects |
| `assessment-designer` | educator | Capability | assessments, rubrics, performance tasks, item banks |
| `presentation-builder` | educator | Capability | instructional slide decks (renders via the `pptx` skill) |
| `curriculum-mapping` | educator | Capability | curriculum maps, pacing guides, scope & sequence |
| `special-education-support` | educator | Capability | accommodation/modification plans, IEP goal drafts, progress monitoring |
| `intervention-mtss` | educator | Capability | Tier 1/2/3 plans, MTSS docs, progress monitoring |
| `family-communication` | educator | Capability | newsletters, parent letters, conference points, report comments |
| `professional-learning` | educator | Capability | observation tools, coaching guides, PD plans |
| `school-administration` | educator | Capability | walkthrough tools, implementation & monitoring plans |
| `document-intelligence` | operations | Operations | parsed/structured content from teacher documents |
| `feed-curator` | operations | Operations | curated education news/resource feeds |
| `meeting-classifier` | operations | Operations | meeting-note classification and routing |
| `standards-updater` | operations | Operations | standards registry refresh workflows |
| `teacher-profile` | operations | Operations | teacher context profiles for personalization |

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
