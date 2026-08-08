<!-- last_reviewed: 2026-07-15 | owner: context-overlays-maintainer -->
# canonical-sources/overlays — context overlay data

Composable, scoped rule-sets that stack onto the resolved teaching-context contract, so a lesson or
assessment adapts to state/district/school/grade/subject without redesigning each skill.

## What's here
- `context/` — the overlays registry: one JSON per overlay at `context/<scope>/<id>.json`, grouped by
  scope (`national/ state/ framework/ county/ district/ school/ program/ grade/ subject/ classroom/`).
  See `canonical-sources/overlays/context/README.md` for the per-overlay shape.

## The model lives in the engine
The overlay **model** and **schema** are part of the context engine, not this data bucket:
- `shared/context/overlays.md` — precedence, merge semantics (`sets` / `adds` / `overrides`), scope
  ranking.
- `shared/context/overlay.schema.json` — the JSON shape each overlay file must satisfy.
Resolve with `python3 shared/context/context.py` (demo) or `import context; context.resolve(...)`.

## Non-negotiable invariants / gotchas
- **Never fabricate codes or mandates** — cite a source and mark `status`. Representative *seed*
  overlays ship; empty scopes (`county/`, `school/`, `program/`, `classroom/`, most `district/`) are
  intentional — add files as data is gathered.
- **State/compliance scope wins on conflict** (`SCOPE_RANK` in `shared/context/context.py`); `adds`
  accumulate and are never dropped.
