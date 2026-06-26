# Teacher-profile setup wizard — interview script

A short, friendly interview that establishes (or updates) the teacher's profile, then registers it into
the context. Driver: `scripts/profile_wizard.py` (interactive, or answers-file/`--demo` for headless).
Keep it short — smaller is more robust; depth can be added later.

## Principles
- **Teacher-stated is truth.** Record what the teacher says as `teacher_stated`/`high`. Anything you
  pre-fill from a public site or the school index is `crawled`/`inferred` and must be **confirmed**.
- **One question at a time, skippable.** Never block on a field; a blank stays a gap, not a guess.
- **Roles before duties before handoffs** — each builds on the last.
- **No student PII.** If the teacher volunteers a student name, drop it; profiles describe roles, not kids.

## Flow
1. **Who & where** — display name; school (offer a `shared/schools/` lookup by name → MSID); district.
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

## Maintenance
Re-run any section to update; the profile carries an `updated` timestamp. Because behavior reads the
resolved context, an updated profile changes skill behavior on the next run — no skill edit, no redeploy.
A future crawl (gated `shared/staff/`) can *propose* role/handoff person-links, but the teacher confirms
before anything person-specific is stored.

## Commands
```bash
python3 skills/teacher-profile/scripts/profile_wizard.py --demo        # build from the example
python3 skills/teacher-profile/scripts/profile_wizard.py --init answers.json
python3 skills/teacher-profile/scripts/profile_wizard.py --validate
python3 skills/teacher-profile/scripts/profile_wizard.py --register    # context sop_refs/overrides fragment
```
