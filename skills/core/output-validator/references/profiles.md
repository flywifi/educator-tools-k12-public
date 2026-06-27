# Validation profiles — per-artifact required keys

Which schema + required keys apply to each governed artifact. `tools/validate_outputs.py --schema <key>`
runs the JSON-Schema check (when `jsonschema` is present) on top of the universal rule catalog.

| Artifact | `--schema` | Schema file | Key fields that must be present |
|---|---|---|---|
| Records handoff package | `records` | `shared/records/records.schema.json` | identification-mode-rendered student, `human_review_required` |
| Traversal evidence envelope | `traversal` | `shared/traversal/traversal.schema.json` | `objective`, `seed_manifest`, `evidence`, `retrieval_gaps`, `checkpoint_state`, `handoff` |
| UDOM document | `udom` | `shared/docintel/udom.schema.json` | `udom_version`, `document_id`, `source`, `pages` |
| Connector feature-flags | `connector-flags` | `shared/connectors/connector.schema.json` | `deployment`, `connectors` |
| Meeting classification record | (rules only) | — | `meeting_type`, `request_intent`, `confidence`, `recommended_next_skill`, `human_review_required` |
| Quality decision record | (rules only) | `shared/context/decision.schema.json` | `decision`, `human_review_required` |

Artifacts without a dedicated schema are still checked against the universal rule catalog
(`rule-catalog.md`). When adding a new emitted artifact, add its schema here and a `--schema` key in
`tools/validate_outputs.py`.
