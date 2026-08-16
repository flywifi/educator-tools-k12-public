<!-- last_reviewed: 2026-08-16 | owner: change-manager -->
# CHANGE_MANAGEMENT.md
## Teacher Operating System (TOS) — Change Management
Governance document (Quality Gates §2.1). How changes are made safely and traceably (QG §2.4 scope
governance; QG §98 maintenance).

---

## 1. Branching
- Develop on a feature branch (this work: `claude/educator-tools-k12-plan-f49yju`). **Never push to `main`.**
- Commits are descriptive; significant changes reference the affected protocol/skill.

## 2. The change loop
```
branch → make the change → run the drift guard → (Phase A+) run evals → commit → push → review
```
- After **any** edit to `shared/` or `protocol-layer/`, run `python3 tools/sync_check.py` and ensure it
  exits 0 (the synced per-skill copies must match canon).
- New skills are scaffolded with `python3 tools/new_skill.py <name>` so they start from the standard
  anatomy and pass the drift guard.
- A correction is **UNTESTED** — not resolved — until it has been validated on the surface where it
  runs (QG §49: completing an action is not proof it worked). Say which one it is in the findings
  log / commit message; the status vocabulary is RESOLVED / OPEN / UNTESTED (`docs/MACOS.md`
  findings log).

## 3. Editing canonical vs. synced files
- Edit the **canonical** file in `shared/` or `protocol-layer/`. **Do not** hand-edit a skill's synced
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

## 7. Component versioning & rollback
**One source of truth:** `versions.json` carries the `ecosystem` semver (mirrored into `VERSION`,
`.claude-plugin/plugin.json`, and **both `.claude-plugin/marketplace.json` version fields**) plus a
semver for **every skill and shared engine** for traceability. `python3 tools/version.py --check`
enforces agreement (ecosystem == VERSION == plugin == marketplace; skill list == installed) and runs
in CI; `--bump <target> <semver>` updates one target. **A release is one command:**
`python3 tools/version.py --release <patch|minor|major>` — it bumps the whole version chain, stamps
`versions.json.updated`, regenerates the plugin/marketplace descriptions + skills catalog
(`tools/export_plugin_manifest.py`), and rolls `[Unreleased]` into the changelog release section.
Installed plugins update on version bumps (not on pushes), so a release is what ships.

**Rollback on a major failure is WHOLE-ECOSYSTEM, not per-component** (matching `tools/rollback.py`
and `versions.json`'s `_comment`; per-component restore invites cross-version mismatch — an earlier
revision of this section said otherwise and was wrong). Restore the entire working tree to a
known-good snapshot:
```
python3 tools/rollback.py --to <git-ref> --reason "<failure>"            # dry-run (target = whole tree)
python3 tools/rollback.py --to <git-ref> --reason "..." --apply          # human-approved
```
A deliberately narrowed `--target` leaves the GENERATED plugin metadata stale, and sync_check
check 21 will fail the post-restore drift guard **by design** — that red is the gate telling you to
either restore the whole tree or run `python3 tools/export_plugin_manifest.py` and commit.
- **Human approval is required by default** — `--apply` is the human approving. An automated caller
  (e.g. `skill-health` / `skill-repair`) must pass `--auto`, which is **refused unless** the deployment
  set `auto_rollback: true` in its flags. That flag is the "automatic permission" grant.
- **The failure is noted**: every rollback (reason, target, ref, mode) is appended to
  `ledger/rollback-log.json`; the drift guard re-runs afterward; a human reviews the working-tree diff
  and commits to finalize.
- **MAINTAINER tie-in**: each skill's `MAINTAINER.md` update checklist + `tools/skill-maintenance.md`
  point here, so versioning + rollback work the same way across every skill. Prefer the smallest rollback
  that achieves the goal (one skill/engine), paired with a `skill-health` diagnosis.
