# Patch principles — repair a skill without breaking it

The smaller the change, the safer the repair. These rules keep a fix tight, durable, and reversible.

## Principles
- **Minimum change that solves the actual problem.** Fix the root cause when the evidence supports it;
  otherwise fix the symptom and say so. Never expand a narrow fix into a redesign.
- **Preserve purpose, voice, and triggering** unless those are the defect. Don't rewrite a working
  `description` while fixing a script.
- **Touch only what must change.** `SKILL.md`, references, scripts, metadata, assets — only where needed.
- **Prefer simplifying fragile logic** over adding more complexity. Remove stale examples / dead
  references discovered during repair only when they directly affect reliability.
- **Official docs over forum advice** when choosing a fix path.
- **Name big problems plainly.** If a skill fails because of broad architectural drift, recommend a
  larger refactor — do not bury it inside a "small patch."
- **Approval is explicit.** Dry-run → human approves → apply. Never auto-apply judgment changes.

## Mechanical vs judgment (the core split)
`tools/skill_repair.py` reads the `skill-health` repair plan and splits steps:
- **Mechanical (safe to automate):** regenerate derived files (`METRICS.md`), re-run the drift guard,
  fix a missing synced reference by re-copying canon. Reversible, deterministic, no naming/semantics.
- **Judgment (human-only):** anything touching wording, routing intent, schemas, frameworks, or a
  policy surface — proposed in plain language, never auto-changed.

## Repair classes mapped to skill-health findings
| Finding | Class | Action |
|---|---|---|
| missing synced `references/method.md`/`quality-gates.md` | mechanical | re-copy canon via `new_skill`/sync, re-run `sync_check` |
| `METRICS.md` stale after a change | mechanical | `python3 tools/metrics.py` |
| skill missing from routing/ontology | judgment | propose the exact line; human approves naming |
| `SKILL.md` name != folder | judgment | propose rename; confirm intent |
| engine not importable | judgment | diagnose import error; propose code fix for review |
| no eval cases | judgment | propose cases; author reviews |

## Hard stops
- Do not finalize if a risky change could not be validated.
- Do not edit a synced reference's per-skill copy — fix canon in `shared/`/`protocols/` and re-sync.
- Do not delete content you did not create without surfacing it first.
