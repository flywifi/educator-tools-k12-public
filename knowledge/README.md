# knowledge/ — Offline Knowledge Packs

Versioned, offline-first knowledge packs used by the TOS atom sub-skills and workflow orchestrators. Each pack contains structured reference material that reduces token cost by giving the model a compact, trusted knowledge source instead of requiring it to recall from training data.

## Packs

| Directory | What it covers | Primary consumers |
|---|---|---|
| `iep-guidance/` | IEP goal formats, PLOP standards, IDEA compliance, FL ESE procedures | atom-iep-goal, special-education-support |
| `behavior/` | Positive behavior support strategies, FBA overview, PBIS tiers, behavior goal templates | intervention-mtss, special-education-support |
| `teaching-strategies/` | Marzano strategies, Bloom's taxonomy verbs, Kagan structures, UDL principles | atom-objective-write, atom-activity-generate |
| `assessment-design/` | UbD framework, item-writing guidelines, rubric design, DOK levels | atom-assessment-item, assessment-designer |
| `reading-levels/` | Lexile bands, F&P levels, WIDA language proficiency, grade-level benchmarks | atom-reading-level, atom-differentiate |
| `math-practices/` | Standards for Mathematical Practice (SMP), math discourse moves, number talks | atom-activity-generate, lesson-planner |

## Design rules
- **Versioned**: each pack has a `version.json` with a date and sha256 of the pack contents.
- **Offline-first**: all content is static Markdown or JSON — no network access required.
- **Compact**: each file is a reference snippet, not a textbook. Target < 200 lines per file.
- **No student data**: packs contain curriculum/pedagogical knowledge only.
- **Updateable**: packs sync via L3 (tools/sync_cache.py) when the teacher chooses to refresh.

## Adding a new pack
1. Create a directory under `knowledge/`.
2. Add a `README.md` and one or more `.md` or `.json` files.
3. Add a `version.json`: `{"pack": "name", "version": "0.1.0", "updated": "YYYY-MM-DD"}`.
4. Run `python3 tools/sync_check.py` (packs are not synced refs, so this is just a sanity check).
