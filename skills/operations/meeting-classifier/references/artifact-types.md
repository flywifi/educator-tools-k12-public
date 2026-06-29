# artifact-types.md
## Artifacts produced by meeting-classifier

This skill **classifies + routes** (and produces a light prep brief). It does not author the meeting's
own artifacts — those are produced by the skill it routes to. All outputs carry the metadata block with
`human_review_required: true`; committed examples use placeholders.

### Meeting classification record (the machine-readable object)
- **Purpose:** the structured classification + routing decision.
- **Required elements:**
  `meeting_type`, `request_intent`, `confidence` (high|medium|low),
  `subject_student` (rendered per identification mode — name by default), `guardians` (when a call home
  is relevant), `required_cadence` (`{required, authority, verify_on_source}` for IEP/504),
  `recommended_next_skill`, `escalate_to_human` (bool),
  `source_availability` / `sources_unavailable` / `degraded` / `convergence_path` / `execution_trace`
  (from the connector plan), `evidence`/`reasons`, `missing_evidence`, and
  `minority_report` (resolver-shaped) when material ambiguity remains, else `null`.

### Routing recommendation
- **Purpose:** the single best-fit next skill (or `manual_review`) + why, honoring "recommend only a
  skill that exists."

### Light prep brief / handoff packet
- **Purpose:** a short brief passed to the owner skill so it can start with context.
- **Required elements:** the classification summary, the context contract, guardian-contact info when a
  call home is needed, and a **medical safety banner** (surfaced from the source on file, attributed,
  never fabricated) when the meeting/call is medical. No full artifact authoring here.

## Validation (extends `shared/quality/verification-checklists.md`)
- Exactly one `meeting_type` + one `request_intent`; `unknown` preferred over a forced label.
- High-stakes types (IEP/504/observation/medical) are **corroborated** before assertion; otherwise a
  minority report or `unknown`.
- `required_cadence` is **advisory** with `verify_on_source: true`; no per-student determination.
- Disabled connectors are never shown as active; degraded paths lower confidence and are recorded.
- No real student data in any committed example (placeholders only); ePHI surfaced from the source on file (attributed; signature not required).
