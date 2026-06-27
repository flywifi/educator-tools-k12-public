# CLAUDE.md
Conventions for working in the Teacher Operating System (TOS) repository.

## What this repo is
A hub-and-spoke ecosystem of Claude Agent Skills that generate, validate, differentiate, and govern
K-12 educational artifacts. Read `docs/ARCHITECTURE.md` for the design. Live status: `STATE.md`.

## Layout
- `skills/` — sub-grouped: `core/` (hub + governance), `educator/` (content skills), `operations/` (tools/feeds/profile), `atoms/` (single-operation sub-skills).
- `shared/` — canonical cross-cutting engines (Standards, Differentiation, Quality). **Source of truth.**
- `protocol-layer/` — the 6 governance protocols. **Source of truth.** `quality-gates.md` is authoritative.
- `canonical-sources/` — authoritative reference data: `registries/` (FL standards + OCPS registries), `schools/` (school indexes), `districts/` (district overlays), `overlays/` (context overlays), root FL district + school-type JSON.
- `tools/` — `sync_check.py` (drift guard), `new_skill.py` (scaffolder), `skill-template/`, `sync_manifest.json`.
- `implementation/` — platform packaging: `gpt/api/` (OpenAI function YAMLs), `gpt/web/` (ChatGPT web doc), `claude/`, `gemini/`.
- `docs/` — architecture, deployment, model, and benchmark docs.
- `security/` — security and safety policies.
- `changes/` — changelog and change management.
- `examples/` — cross-skill example library.

## Branching & git
- Develop on the feature branch (currently `claude/educator-tools-k12-plan-f49yju`). **Never push to `main`.**
- Push with `git push -u origin <branch>`; retry network failures with backoff.
- Do not open a PR unless explicitly asked.

## The two-copy / sync rule (important)
Each skill carries byte-identical **synced copies** of shared references (see
`tools/sync_manifest.json`). **Edit the canonical file in `shared/` or `protocol-layer/`, never the
per-skill copy.** After any change to `shared/` or `protocol-layer/`, run the drift guard:

```bash
python3 tools/sync_check.py     # exit 0 = clean; 1 = drift report
```

## Adding a skill
```bash
python3 tools/new_skill.py <skill-name>   # scaffolds from the template + copies synced refs
python3 tools/sync_check.py               # must pass
```
Then edit `SKILL.md` (specific, slightly "pushy", scoped description with a "Do NOT use for…"
clause) and `references/artifact-types.md`. Follow the inner loop in `skill-creator` (draft → evals
→ iterate) for capability skills.

## Non-negotiables (enforced by the drift guard / Quality Gates)
- Every `SKILL.md` references the pipeline (`method.md`), the metadata schema (`metadata-schema.md`),
  and emits `human_review_required`.
- No real student data anywhere — placeholders only.
- Never fabricate standards/citations/results. Nothing is "Final" until it passes the Quality Gates.

## Commit messages
Describe the change and reference the affected protocol/skill. Update `STATE.md` at phase boundaries
and after a skill ships.
