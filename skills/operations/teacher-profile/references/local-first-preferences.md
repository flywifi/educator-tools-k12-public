# Local-First preferences (L0)

The wizard captures how a teacher wants the system to run **offline / at low token cost**, as a
reversible `local_first` block inside the gitignored profile (`shared/context/profiles/teacher.local.json`).
Defaults are the safest, fully-offline path; anything that adds a dependency or sends work to a local
model is **OFF until the teacher gives explicit consent** — installs are never silent.

## What it stores

| Field | Values | Default | Consent needed |
|---|---|---|---|
| `offline_tier` | `cached_python` · `local_semantic` · `local_llm` | `cached_python` | `local_semantic` / `local_llm` |
| `retrieval_mode` | `stdlib_keyword` · `vector` | `stdlib_keyword` | `vector` ⇒ `local_semantic` |
| `local_model` | `off` · `ollama` · `llamafile` | `off` | — (inert until tier = `local_llm`) |
| `consents` | `{capability: {granted, at}}` | `{}` | — |
| `school_scope` | `{school, msid}` | `null` | — |

- **`cached_python` (default):** the L1 SQLite/FTS5 standards cache + pure-Python tools. Fully offline,
  zero token cost at query time, no extra dependency.
- **`local_semantic` (opt-in):** adds the L2 `sqlite-vec` vector index for paraphrase recall. Falls back
  to keyword search when the dependency is absent.
- **`local_llm` (opt-in):** drafts with a local model (`ollama` / `llamafile`) for air-gapped/no-budget
  use. Output still passes the Quality Gates and stays `human_review_required: true`.

## Commands

```bash
# View current preferences (no write)
python3 scripts/profile_wizard.py --preferences

# Opt in to the vector tier (consent + choice in one call)
python3 scripts/profile_wizard.py --preferences --consent local_semantic --set '{"retrieval_mode":"vector"}'

# Opt in to a local model
python3 scripts/profile_wizard.py --preferences --consent local_llm \
    --set '{"offline_tier":"local_llm","local_model":"ollama"}'

# Revoke a consent — any preference that needed it rolls back to the safe default
python3 scripts/profile_wizard.py --preferences --revoke local_semantic

# Moving schools: re-point scope and re-confirm preferences
python3 scripts/profile_wizard.py --preferences --school-change '{"school":"Lake Nona HS","msid":"480123"}'

# Changed your mind entirely: revert to safe defaults (clears consents)
python3 scripts/profile_wizard.py --preferences --reset
```

## Reversibility & honesty

- Setting a gated value **without** its consent is **refused**: the safe default is kept and a note
  explains how to grant consent. Nothing is enabled behind the teacher's back.
- **Revoking** a consent automatically rolls back any preference that depended on it.
- `--reset` returns everything to the fully-offline defaults and clears consents.
- `--register` surfaces the `local_first` block to the shared context so retrieval/generation engines
  honor the chosen tier without re-asking. Preferences are *data*, never code — changing them never
  requires a rebuild.
