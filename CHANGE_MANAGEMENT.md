# CHANGE_MANAGEMENT.md
## Teacher Operating System (TOS) — Change Management
Governance document (Quality Gates §2.1). How changes are made safely and traceably (QG §2.4 scope
governance; QG §98 maintenance).

---

## 1. Branching
- Develop on a feature branch (this work: `claude/fervent-hawking-nyrzy5`). **Never push to `main`.**
- Commits are descriptive; significant changes reference the affected protocol/skill.

## 2. The change loop
```
branch → make the change → run the drift guard → (Phase A+) run evals → commit → push → review
```
- After **any** edit to `shared/` or `protocols/`, run `python3 tools/sync_check.py` and ensure it
  exits 0 (the synced per-skill copies must match canon).
- New skills are scaffolded with `python3 tools/new_skill.py <name>` so they start from the standard
  anatomy and pass the drift guard.

## 3. Editing canonical vs. synced files
- Edit the **canonical** file in `shared/` or `protocols/`. **Do not** hand-edit a skill's synced
  `references/` copy — re-sync instead (the drift guard will flag drift otherwise).
- `tools/sync_manifest.json` defines the canonical→synced mapping.

## 4. Scope changes (QG §2.4)
- Adding an artifact type or skill is a scope change: document the rationale, add it via the
  template + an eval gate, and update `STATE.md` and `TOS_ECOSYSTEM_BUILD_OUTLINE.md`.
- Undocumented scope changes are prohibited (QG §2.3).

## 5. Versioning & maintenance
- The ecosystem uses **semantic versioning** (`VERSION`, recorded in `CHANGELOG.md`):
  **MAJOR** = a breaking change to a protocol, the metadata schema, or the pipeline contract;
  **MINOR** = a new skill or artifact type, or a backward-compatible capability;
  **PATCH** = fixes, doc, or content corrections.
- Protocols carry their own version line (currently all v1.0). Record notable changes in
  `CHANGELOG.md`; cut a `VERSION` bump + a changelog entry at each release.
- Review the quality model when governance, audit, certification, or architecture changes (QG §98).
- Update `STATE.md` at every phase boundary and after each skill ships (preservation/recovery).

## 6. Quality bar for merges (toward Phase D)
A change is mergeable when: the drift guard passes; affected skills' evals pass; docs are updated;
no critical-failure conditions (fabrication, real PII, unsafe output) are present; and `STATE.md`
reflects reality.
