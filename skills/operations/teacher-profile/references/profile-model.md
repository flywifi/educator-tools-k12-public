# Teacher profile — data model

The profile is one teacher's **self-described operating context**. Schema:
`shared/context/profiles/teacher.schema.json`; example: `shared/context/profiles/teacher.example.json`;
live (gitignored) store: `teacher.local.json` in the same folder.

## Sections
- **teacher** — `display_name`, optional `school_msid` (links to `shared/schools/`), `school_name`,
  `district`, and `contact_local_only` (minimum-necessary; stays local, never committed).
- **roles[]** — one or more roles (multi-role supported), each with optional `subject`/`grade`/
  `department`, a `primary` flag, and `provenance`/`confidence`.
- **duties[]** — recurring responsibilities with `cadence`/`workload`.
- **handoffs[]** — the **role-interaction map**: `what`, `direction` (to/from/bidirectional),
  `counterparty_role` (a ROLE, not a person — survives turnover), `trigger`, `cadence`, `notes`.
- **meetings[]** — recurring meetings + the teacher's `role_in_meeting`.
- **preferences{}** — free-form generation/behavior defaults (tone, templates, communication rules,
  pacing norms) that become context `overrides`.
- **overrides[]** — explicit control-plane instructions (`instruction`, `by`, `timestamp`).

## Provenance & truth (RFC Vol 2/12)
Every fact carries `provenance ∈ {teacher_stated, crawled, inferred, imported}` + `confidence`.
**Teacher-stated outranks crawled/inferred** — public sites rarely reflect a teacher's true duties, so a
crawled guess is confirmed by the teacher before it shapes behavior
(`shared/context/source-of-truth.md`). Conflicts surface; they are not silently merged.

## How it reaches other skills
The wizard's `--register` emits a context contribution:
- a classroom-scope `sop_ref` pointing at the (gitignored) profile,
- `overrides[]` derived from `preferences` + explicit overrides,
- a `role_interaction_map` (roles + handoffs) for routing skills (`meeting-classifier`, records handoffs).
A context build merges this via `shared/context/` (precedence in `authority_precedence`); the wizard does
not mutate a contract directly. `human_review_required: true` stays on every output.

## Privacy
Gitignored local store; **no student PII**; teacher contact is minimum-necessary and local-only.
The committed `teacher.example.json` is placeholders only.
