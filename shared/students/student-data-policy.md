# Student data — PII / ePHI handling policy (canonical)

A teacher's job legitimately requires real student information: a student's and guardian's **name** (to
call home about discipline or a medical issue), the **student ID** (the unique key), plan flags
(IEP/504/EL), and **ePHI** such as a student's **anaphylaxis action plan** that states when/where to
administer an EpiPen. This engine catalogs that as a **student profile** (`student-profile.schema.json`)
and defines how it is accessed, stored, identified, and reconciled — safely.

## The line (a refinement of "placeholders only", not a break)
- **Committed repo content stays placeholders-only.** Every schema, example
  (`students.example.json`), and *committed* artifact uses obvious fake data. The drift guard keeps real
  student data out of tracked files.
- **The runtime may handle the authorized teacher's real PII/ePHI** under **FERPA legitimate
  educational interest** and the **minimum-necessary** principle — but it is held by the storage adapter
  for the surface and is **never committed to git**.

## Storage adapter (by deployment surface)
- `local_gitignored` — Claude Code / desktop with a writable repo FS. Real data in
  `students.local.json` (or `shared/students/local/`), **gitignored**. The default where a FS exists.
- `session_ephemeral` — web chat with no FS: the teacher pastes the profile each session; nothing is
  persisted by the tool.
- `uploaded_file` — web chat: a profile file uploaded per session, read via `shared/docintel/`.
- `connector_sis` — any surface with a live SIS/roster connector: authoritative, no local copy needed.

Auto-detect: use `local_gitignored` if a writable repo FS exists, else `session_ephemeral`. The
precedence + conflict rules below hold on **every** surface.

## Source precedence + conflict (SIS-first)
A connected **SIS is authoritative** for student data (it updates regularly and is usually most
accurate) and is used **first unless the teacher overrides**; the **local store** is the fallback/cache.
A live SIS link is uncommon, so the local store is the usual source in practice.

When SIS data **conflicts** with the local store, **never silently merge**:
1. surface the conflict via the resolver (`shared/context/sot_resolver.py` + the `student_record` claim
   in `source-roles.json`: SIS = authoritative, local = secondary);
2. **raise it with the user** — ask **which source to use** and **whether to update the local record**;
3. log the decision; if it stays unresolved, keep a **minority report**
   (`shared/context/minority-report.md`). `students.py --reconcile` flags conflicts per field and
   recommends SIS-first **without** auto-updating.

## Identification mode (feature flag)
`identify_students_by: name | id` (default **name**). In **ID-only** mode, saved records, handoffs, and
any shareable artifact reference the student by **student ID**; the real name is shown only in the live
teacher-facing view and resolved on demand — a pseudonymization option for privacy.

## ePHI safety (medical / health information)
- **Surface, do not generate.** Health guidance is surfaced **verbatim from the source on file**, quoted
  with its `source_type`, `source_authority`, `provided_by`, and `effective_dates`. **Never fabricate
  medical instructions, dosages, or protocols.**
- **Trust multiple sources — a signature is not required.** Health info usually lives on **district or
  school-specific forms, nurse notes, guardian notes, or sick notes**, and a physician signature is
  rarely available (you do not need a doctor's signature for a sick note or EpiPen instructions). Ingest
  and trust these; record each item's `source_type` + `source_authority` (official form / action plan =
  high; nurse or guardian note = medium; verbal / unverified = low) so the basis is visible. `signed` is
  optional.
- **Conflicts** between health sources go through the resolver (`shared/context/sot_resolver.py`; the
  authority tier orders them) — never silently merge.
- Treat it as **safety-critical**: defer to the **school nurse / 911** and the source on file; escalate
  any individual-student medical specifics to a human. The tool is not medical advice.
- Health records are the most sensitive PII — strict minimum-necessary; surface only to staff with
  legitimate educational interest for the task at hand.

## Security & retention
Gitignored at rest; redact on export (apply the identification mode); retention per district policy;
record `provenance` + `last_verified` on each profile. Ties to `SECURITY_AND_SAFETY.md` and the
privacy norms in `skills/family-communication/`.

## Use the helper
```bash
python3 shared/students/students.py --list
python3 shared/students/students.py --get S-000123 --mode name   # or --mode id
python3 shared/students/students.py --reconcile <sis_export.json> # flag SIS<->local conflicts
```
Loads the gitignored local store if present, else the placeholder example. Offline, stdlib only.
