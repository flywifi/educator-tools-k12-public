# districts/ — District Overlays

Per-district configuration overlays that customize TOS behavior without forking the repository. Each overlay overrides only what differs from the shared defaults; the core skills, atoms, and shared engines are unchanged.

## Available overlays

| Directory | District | Status |
|---|---|---|
| `orange-county/` | Orange County Public Schools (OCPS), FL — District 48 | active |
| `_template/` | Starter template — copy to add a new district | template |

## What an overlay can contain

```
districts/<name>/
  overlay.json         # metadata: district name, MSID, state, config overrides
  templates/           # district-required artifact templates (lesson plan format, header/footer)
  policies/            # local policies that override shared defaults (grading scale, submission requirements)
  resources/           # approved resource lists, pacing guides, curriculum maps
  README.md            # what this overlay covers and who maintains it
```

## How overlays work
TOS reads `shared/context/overlays/` for active overlays. A district overlay is activated by the teacher profile wizard (`profile_wizard.py --preferences --district orange-county`), which registers it as a context fragment. The `sot_resolver.py` precedence hierarchy:

```
teacher_stated > district_overlay > school_profile > shared_defaults
```

Overlays are reversible — `--district reset` removes the overlay without changing any other preference.

## Adding a new district overlay
1. Copy `_template/` to `districts/<district-name>/`.
2. Fill in `overlay.json` with the district's name, MSID, state, and any config overrides.
3. Add a pointer in `shared/context/overlays/` (follow the existing OCPS entry as a pattern).
4. Run `python3 tools/sync_check.py`.
