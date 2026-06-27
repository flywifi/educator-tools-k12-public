# Rule catalog — governance + claim checks (output-validator)

The universal checks `tools/validate_outputs.py` applies to every governed JSON artifact. `blocking` =
must fix before ship; `warning` = confirm; `info` = note. Mirrors the ecosystem non-negotiables
(`CLAUDE.md`, `protocols/metadata-schema.md`).

| Rule | Severity | What it asserts | Why |
|---|---|---|---|
| `human_review_required` | blocking | the flag is present and `true` | every output is decision support, never a final/automatic determination |
| `no_empty_standard` | blocking | `standards_cited` / `standards_set` contain no blank codes | a fabricated or empty citation is never a basis for a decision (standards-verification) |
| `no_real_pii` | blocking | no SSN-pattern value anywhere | real PII/ePHI must never appear in an emitted/committed artifact |
| `placeholder_pii` | warning | phone numbers use the `555` placeholder range | catches real contact data that slipped past placeholders |
| schema validity | blocking (when checked) | validates against the named JSON Schema | structural contract for downstream consumers |
| `jsonschema_not_installed` | info | schema check skipped, not failed | stdlib-first: absence of a lib degrades to a gap, never a false failure |

## Operating rules
- **Never fail because a checker is missing.** A check that can't run is reported `skipped`/`gap`, so the
  validator always returns a usable verdict — it must work no matter what is installed.
- **Promote failures.** `--promote <evals.json>` records a failing case as a regression so the same
  defect is caught next time (the prior system's promote-failures pattern).
- **Separate the layers.** Governance rules, JSON-schema validity, and document-structure validity are
  reported independently; a pass on one is never reported as a pass on another.
- **Escalate, don't fix.** A validator never edits the artifact; it reports + routes (mechanical fixes →
  `skill-repair`, judgment → the owning skill, teaching quality → `quality-review`).
