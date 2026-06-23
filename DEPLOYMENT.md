# DEPLOYMENT.md
## Distribution, installation & update strategy (Phase E4)

How the Teacher Operating System ships and stays current. The repository is the **source of truth**;
installable bundles are built from it.

## 1. Packaging
Each skill is packaged into an installable `.skill` bundle (a zip of the skill directory):

```bash
python3 tools/package_skill.py --all     # -> dist/<skill>.skill  (dist/ is git-ignored)
python3 tools/package_skill.py lesson-planner
```
Packaging validates each skill first (SKILL.md present with `name`/`description` frontmatter + the
governance markers). A bundle contains the skill's `SKILL.md`, `references/` (incl. the synced
`method.md` + `quality-gates.md`), `assets/`, `scripts/`, `examples/`, and `evals/`.

## 2. Installation
Install the hub plus whatever capability skills are needed (the hub routes to them):
- **Claude Code / Agent SDK:** place the skill folder (or unzipped `.skill`) under the agent's skills
  directory so it appears in `available_skills`.
- **Claude.ai / Cowork:** upload the `.skill` bundle where skills can be added.
- **Always include `teacher-core`** (the router) + `quality-review` (the gate); add capability skills
  as needed. Skills are self-contained (synced references travel in the bundle).

**Install the whole suite as one Cowork plugin.** The repo root carries a `.claude-plugin/plugin.json`
(plugin metadata; the `skills/` dir is auto-discovered) and a `.claude-plugin/marketplace.json` so a
district/school can add TOS from a marketplace in one step instead of per-skill uploads. Bump
`plugin.json`'s `version` (and refresh `marketplace.json`) when skills are added/removed — the
registry-currency watcher flags this (below).

## 3. Update strategy
- **Versioning:** semantic versioning in `VERSION` + `CHANGELOG.md` (policy in `CHANGE_MANAGEMENT.md`).
- **Change → release loop:** edit the canonical file in `shared/`/`protocols/` → `python3
  tools/sync_check.py` (drift guard) → `python3 tools/metrics.py` → bump `VERSION` + changelog →
  `package_skill.py --all` → distribute.
- **CI gate:** `.github/workflows/ci.yml` runs the drift guard, validates evals, and packages all
  skills on every push — a change that breaks sync or packaging fails CI.
- **Re-sync on shared changes:** because skills carry synced copies of shared references, a change to
  `shared/`/`protocols/` requires re-packaging the affected skills so bundles aren't stale (the drift
  guard catches divergence in-repo).
- **Registry currency:** `python3 tools/registry_currency.py --summary` watches the stored
  authoritative registries (connectors, grade-scales, frameworks, ontology, routing, records field
  catalogs, the plugin manifest) for drift vs. recorded baselines and names the authority to re-verify
  on; `--update-baselines` after a human approves. (Education-standards crawling stays with
  `standards-updater` / `tools/standards_refresh.py`.) Structural health is `shared/health/health.py`.

## 4. Environment notes
- This repo currently lives at `flywifi/Repo-1`, developed on branch `claude/fervent-hawking-nyrzy5`.
- No runtime services or secrets — the ecosystem is skills + protocols + tooling (Python 3, stdlib
  only). `presentation-builder` relies on the host's `pptx` skill at render time.

## 5. Pre-distribution checklist
- [ ] `tools/sync_check.py` exits 0.
- [ ] `tools/metrics.py` regenerated `METRICS.md`.
- [ ] `tools/package_skill.py --all` succeeds.
- [ ] `VERSION` + `CHANGELOG.md` updated; `SECURITY_REVIEW.md` still accurate.
- [ ] No real student data anywhere (placeholders only).
