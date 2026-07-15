# Teacher-profile setup wizard — interview script

A short, friendly interview that establishes (or updates) the teacher's profile, then registers it into
the context. Driver: `scripts/profile_wizard.py` (interactive, or answers-file/`--demo` for headless).
Keep it short — smaller is more robust; depth can be added later.

## Principles
- **Teacher-stated is truth.** Record what the teacher says as `teacher_stated`/`high`. Anything you
  pre-fill from a public site or the school index is `crawled`/`inferred` and must be **confirmed**.
- **One question at a time, skippable.** Never block on a field; a blank stays a gap, not a guess.
- **Say the why out loud.** Every question states, in teacher terms, what answering it buys her
  (e.g., school type → "it changes what 'aligned to standards' means for you"). The per-step whys
  live in the chat-platform sibling script `implementation/gpt/api/web-wizard.md` — keep the step
  list and whys aligned between the two files.
- **Roles before duties before handoffs** — each builds on the last.
- **No student PII.** If the teacher volunteers a student name, drop it; profiles describe roles, not kids.

## Flow
1. **Who & where** — display name; school (offer a lookup by name → MSID via
   `python3 tools/offline_index.py --school "<name>"`; data: `canonical-sources/schools/`); district.
   **Always ask school type** (public / magnet / charter / virtual / home-ed / private — and if
   private, whether it enrolls FL scholarship students); resolve the rule-set from
   `canonical-sources/school-types.json` and tell the teacher what it means for her (why: standards
   applicability and assessment rules differ — B.E.S.T. is mandatory for public schools, the
   school's own choice for private ones).
2. **Role(s)** — "What are all your roles this year?" Capture each (subject/grade/department; mark the
   primary). Multi-role is normal (e.g. teacher + MTSS lead).
3. **Duties / workload** — "What are your recurring responsibilities?" with cadence + rough load.
4. **Handoff & role-interaction map** — the heart of it. For each recurring handoff: *what* moves,
   *direction* (to/from), the *counterparty role* (case manager, AP, counselor, nurse, co-teacher,
   grade/department team), the *trigger*, and *cadence*. "Who do you hand X to? Who hands you Y?"
5. **Meetings** — recurring meetings + the teacher's role in each.
6. **Preferences** — tone, lesson template, communication rules (e.g. no contact home after 5pm),
   pacing norms, reading-level defaults.
7. **Confirm & register** — show a summary; on approval write `teacher.local.json` and run `--register`
   to contribute the sop_ref + overrides + role map to the context.
8. **Offer the requirements map.** After registering, offer to assemble the teacher's consolidated
   requirements map — one table scoped to their profile: every standard for their grade + subject
   (code + full statement, via `python3 tools/fl_lookup.py` or `tools/offline_index.py --standards`;
   data: `shared/standards/resources/florida/data/`), their course code(s)
   (`canonical-sources/references/fl-course-codes.json`), their district
   (`canonical-sources/florida-districts.json`), and their school-type rule-set
   (`canonical-sources/school-types.json`). **Citation rule: every row names the source file it came
   from and the external authority to verify it on (CPALMS / the FLDOE URLs those files cite), plus
   the capture date.** Mandatory footer: *DRAFT — verify anything used in a formal document on the
   cited authority (`human_review_required`)*. On chat platforms without these tools, the same map is
   assembled from the uploaded Reference Pack files instead — same columns, same citation rule, plus
   the **completeness contract**: exact enumeration only when the file is truly read (data-analysis
   tool; report *matched N of the file's `count` total*), otherwise the table is labeled
   *best-effort — retrieved, not exhaustively enumerated*; one subject per table (~40 rows max,
   offer "next"); social-studies rows carry an extra "verify on CPALMS" flag (legacy-doc parse).

## Moving the profile between the desktop and the Claude/ChatGPT app
The desktop tools keep the profile as `teacher.local.json` (gitignored); the apps keep it as
`my-teacher-profile.md` in a Project. Bridge them so a teacher never re-does the interview:
- **Desktop → app:** `python3 scripts/profile_wizard.py --export-md my-teacher-profile.md` renders a
  human-readable file (that the app reads) with the exact profile embedded — add it to the Project.
- **App → desktop:** download `my-teacher-profile.md` from the Project, then
  `python3 scripts/profile_wizard.py --import-md my-teacher-profile.md` rebuilds `teacher.local.json`.
The round-trip is lossless and tolerates a Windows/Notepad BOM + CRLF (import reads `utf-8-sig`; the
embedded `json` block is the source of truth). Placeholders only — never real student names.

## Maintenance
Re-run any section to update; the profile carries an `updated` timestamp. Because behavior reads the
resolved context, an updated profile changes skill behavior on the next run — no skill edit, no redeploy.
A future crawl (gated `shared/staff/`) can *propose* role/handoff person-links, but the teacher confirms
before anything person-specific is stored.

## Commands
```bash
python3 skills/operations/teacher-profile/scripts/profile_wizard.py --demo        # build from the example
python3 skills/operations/teacher-profile/scripts/profile_wizard.py --init answers.json
python3 skills/operations/teacher-profile/scripts/profile_wizard.py --validate
python3 skills/operations/teacher-profile/scripts/profile_wizard.py --register    # context sop_refs/overrides fragment
```
