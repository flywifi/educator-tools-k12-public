<!-- last_reviewed: 2026-07-15 | owner: canonical-data-maintainer -->
# canonical-sources — authoritative reference data

The single home for authoritative, cited reference data the skills draw on. Values here are verbatim
from a real source (each file carries `provenance`/`_comment`); skills embed **found** rows, never
generated ones.

## Layout
- `references/` — reference corpora (course codes, toolkit links, taxonomies). See its README.
- `schools/` — school indexes (public + private). See its docs.
- `registries/` — FL standards + OCPS registries, `fldoe-data-sources.json`, `msid-cache/`.
- `districts/` — district overlays.
- `overlays/` — composable context overlays. See its README.
- `index/` — the gitignored offline reference index + committed `index-manifest.json`. See its README.

## Root taxonomy files
- **`florida-districts.json`** — log of Florida's **67** county school districts (the LEAs). Most
  fields are fillable stubs populated per district (rule refs, virtual-school notes, key rules).
- **`school-types.json`** — the FL school-type taxonomy with **exception rule-sets**.
  `traditional_public` is the `baseline`; every other type declares only how it *differs*. Current
  types: `traditional_public`, `magnet_public`, `charter_public`, `district_virtual_instruction`,
  `flvs_statewide`, `home_education`, `private_scholarship`, **`private_independent`**.

## Non-negotiable invariants / gotchas
- **Never fabricate** a code, district field, or type rule — cite the source and mark `status`.
- **Indexed sources must stay in step with the offline index:** after editing any file the index
  reads (see `references/README.md` and `index/README.md`), rebuild with
  `python3 tools/offline_index.py --build` and commit `index-manifest.json`, or `sync_check.py`
  check 14 fails.
