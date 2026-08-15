<!-- last_reviewed: 2026-08-14 | owner: deployment-maintainer -->
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
**The primary channel is the plugin** — install the whole suite in one step (Claude Code and
Cowork/desktop, both surfaces):

```
/plugin marketplace add flywifi/educator-tools-k12-public
/plugin install teacher-operating-system@tos-marketplace
```

The repo root carries `.claude-plugin/plugin.json` + `marketplace.json`; `skills/` is
auto-discovered, and the plugin ships the whole tracked tree (`source: "./"`), so shared engines
and canonical data travel with it. **The manifests' versions and descriptions are GENERATED**
(`tools/export_plugin_manifest.py`) and freshness-gated in CI (`sync_check` check 21) — never
hand-edit them; a release (`python3 tools/version.py --release …`, §3) regenerates everything.

Per-skill `.skill` bundles remain a secondary channel for surfaces that take individual skill
uploads: always include `teacher-core` (the router) + `quality-review` (the gate); skills are
self-contained (synced references travel in the bundle).

## 3. Update strategy
- **How installed plugins actually update (the channel truth):** `autoUpdate: true` refreshes
  installs on session start, but **updates propagate on VERSION BUMPS, not on every push** — the
  2026-06-29 attempt at pure push-based updates was reverted within two hours because dropping
  the pinned version broke the CI version gate. A merge to `main` without a bump reaches nobody's
  install. Hence:
- **Versioning:** semantic versioning in `VERSION` + `changes/CHANGELOG.md` (policy in
  `changes/CHANGE_MANAGEMENT.md`).
- **Change → release loop:** edit the canonical file in `shared/`/`protocol-layer/` → `python3
  tools/sync_check.py` (drift guard) → `python3 tools/metrics.py` → **`python3 tools/version.py
  --release <patch|minor|major>`** (one command: bumps VERSION/versions.json(+updated)/plugin.json,
  regenerates both marketplace fields + all generated descriptions/catalog, rolls
  `[Unreleased]` into the release section) → commit → merge to `main` → installs pick it up.
- **Optional autopilot:** `.github/workflows/plugin-autobump.yml` can auto-cut a patch release on
  every merge to `main`; it ships **dormant** — uncommenting its `push:` trigger is the owner's
  enable act, made as a reviewable commit (same pattern as the currency-recheck schedule). Note:
  if `main` ever gains required-PR branch protection, the bot needs a bypass allowance — that
  setting lives outside the repo and cannot be gated from inside it.
- **CI gate:** `.github/workflows/ci.yml` runs the drift guard, validates evals, and packages all
  skills on every push — a change that breaks sync or packaging fails CI.
- **Re-sync on shared changes:** because skills carry synced copies of shared references, a change to
  `shared/`/`protocols/` requires re-packaging the affected skills so bundles aren't stale (the drift
  guard catches divergence in-repo).
- **Registry currency:** `python3 tools/registry_currency.py --summary` watches the stored
  authoritative registries (connectors, grade-scales, frameworks, ontology, routing, records field
  catalogs) for drift vs. recorded baselines and names the authority to re-verify
  on (the plugin manifest left this watchlist 2026-08-14 — it is generated and gated instead); `--update-baselines` after a human approves. (Education-standards crawling stays with
  `standards-updater` / `tools/standards_refresh.py`.) Structural health is `shared/health/health.py`.
- **Optional capabilities & deps:** `python3 shared/health/capabilities.py` shows which optional powers
  are active (PDF/OCR/Office/render/transcription/fonts) and which **cloud** providers are installed +
  credentialed. Install per-capability into the **managed venv** — `python3 tools/deps_preflight.py
  --install <capability>` (e.g. `office_authoring`) or `--install-all` — which uses the isolated,
  gitignored `.harvest-venv/` (wheels-only, never system Python, so **macOS/Homebrew PEP 668 never
  trips**); `--python-path` prints that venv's interpreter for a Claude Desktop MCP `command`/GUI
  launch. (Direct `pip install -r tools/requirements-*.txt` works too, but only inside a venv on
  macOS.) **System bins** are separate — LibreOffice, poppler, ffmpeg, tesseract (macOS:
  `brew install libreoffice tesseract ffmpeg poppler`); fonts: Noto/Liberation/Carlito/Caladea. macOS
  cross-platform details: `docs/DEPLOYMENT_SURFACES.md` + `docs/MACOS.md`. **Cloud providers**
  (Azure/fal/Nutrient/Firecrawl) are OFF until a deployment opts in via `cloud_providers` and supplies
  API keys **in the environment** (never the repo). Policy + privacy boundary:
  `shared/health/dependency-policy.md`.
- **Supply chain:** deps are pinned, auto-updated (`.github/dependabot.yml`), and scanned
  (`tools/security_scan.py` = pip-audit + bandit) as a CI gate — so every bump is current AND vetted.
- **Authoring outputs:** `shared/office/` emits real `.pptx/.docx/.xlsx` (gated on python-pptx/docx/
  openpyxl; LibreOffice renders PDF/PNG for QA) and `shared/office/google_bridge.py` emits Google
  Docs/Sheets/Slides (the Office file imports losslessly, plus a generated Apps Script for native/advanced
  builds). Live Google creation runs through the **host AI's native Google integration** or a deployment
  **Node/clasp** runner (`@google/clasp` + `googleapis`); credentials come from the environment only.

## 4. Environment notes
- This repo lives at `flywifi/educator-tools-k12-public` (the public repo — never to be
  confused with `flywifi/Repo-1`, a separate repository this project must not touch);
  development happens on the feature branch named in `CLAUDE.md`, currently
  `claude/educator-tools-k12-plan-f49yju`. **Never push to `main`.**
- No runtime services or secrets — the core ecosystem is skills + protocols + tooling
  (Python 3, stdlib for everything governed; the OPTIONAL capabilities in §3 install into the
  managed venv and are off until enabled). `presentation-builder` relies on the host's `pptx`
  skill at render time.

## 5. Pre-distribution checklist
- [ ] `tools/sync_check.py` exits 0.
- [ ] `tools/metrics.py` regenerated `METRICS.md`.
- [ ] `tools/package_skill.py --all` succeeds.
- [ ] `python3 tools/version.py --release …` run (VERSION/manifests/changelog all move
      together); `security/SECURITY_REVIEW.md` still accurate.
- [ ] No real student data anywhere (placeholders only).
