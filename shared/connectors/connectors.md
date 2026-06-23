# Connectors — workplace tools as feature-flagged evidence sources (canonical)

Teachers work across many tools (email, calendar, drive, LMS, video calls, the SIS). This engine lets a
skill **use whatever the deployment has connected**, **degrade** to whatever it has permission for, and
**converge** on an answer via alternate sources — with **unused connectors flagged off** so nothing is
probed when it's not there. It is a *contract*, not a set of live API clients: actual retrieval happens
through whatever the deployment connected (or manual paste / uploaded files via `shared/docintel/`); the
registry says what each connector **would** provide and how to behave when it's off. First consumer:
`skills/meeting-classifier/`.

Files: `connectors.json` (registry), `connector.schema.json` (contract), `feature-flags.example.json`
(sample per-deployment flags), `connectors.py` (offline resolver). Companion privacy policy for student
data: `shared/students/student-data-policy.md`.

## Connectors shipped
`manual_paste` + `uploaded_file` (always `available` — the offline fallback), `google_workspace`,
`google_classroom`, `microsoft_365`, `microsoft_teams`, `zoom`, `canvas`, `blackboard`, `salesforce`,
and `sis` (**authoritative for student data when connected**). Extensible stubs: `webex`, `google_meet`.
All third-party connectors **default `not_installed`**.

## Canonical states
`available · disabled · not_installed · permission_blocked · metadata_only · unsupported · unknown`.
- A **non-`available`** source is never presented as an active retrieval path.
- `metadata_only` is **never** treated as content-ingested truth (visibility ≠ extraction).
- Any degraded/partial path **lowers confidence** and is recorded — never hidden in prose.

## Normalized evidence types
`calendar_event · email · roster · attendee_roles · transcript · call_notes · chat_history · file ·
student_profile · guardians · plan_flags`. Skills consume evidence **types**, not connectors, so an
answer can be reached from whichever connector is live.

## Degradation + convergence policy
Evidence priority, strong → weak:
`explicit user statement > calendar_event > email (sender title/role) > attendee roles >
subject/body keywords > prior thread > transcript / call notes > filename`.
- If the **top** source for a signal is off/blocked/`not_installed`/`permission_blocked`, **drop to the
  next available** source for the same signal, **record it** in the execution trace, and **lower
  confidence**.
- **Converge**: corroborate several weak available sources (e.g., calendar title + attendee role +
  attachment) before asserting. A **single weak** source ⇒ low confidence / `unknown`.
- **Skip** connectors that are flagged off — do not probe them (saves time/resources).
- `sis` is **authoritative for student data**: when `available` it is used first (unless overridden);
  conflicts with the local student store are escalated, not merged (`shared/students/student-data-policy.md`).

## Override policy (user says use / avoid / prioritize a source)
- Set `allowed_sources` when the user narrows the path; set `blocked_sources` when they exclude one;
  append the instruction to an `override_log`.
- An override is a **control-plane reset**: invalidate hypotheses built mainly from now-blocked sources;
  do not keep a blocked path open just because it was already open. Preserve recorded provenance and
  blocked-path notes. If the user later broadens ("just figure it out"), log a new override and widen
  `allowed_sources` deliberately while keeping prior degraded/blocked history visible.

## Resilience mapping (make failure visible)
Carry `execution_trace` (retries, fallbacks, overrides, route decisions) and classify each path with a
shared failure class: `SUCCESS · TRANSIENT · PERMISSION · NOT_FOUND · UNSUPPORTED · AMBIGUOUS_EMPTY ·
STALE · MIXED_STATE · DEGRADED_SUCCESS`. **Hard rule:** never bury an unsupported/blocked connector in
narrative — make it a visible gap and lower confidence accordingly. Unresolved material alternates go to
a **minority report** (`shared/context/minority-report.md`).

## Privacy boundary
Connecting email/calendar/drive/transcripts can expose real student/guardian PII (and ePHI in health
records). Extract **only** classification-relevant signals (minimum necessary), **never persist real
student data to git** (placeholders only in the repo), and follow
`shared/students/student-data-policy.md` + `SECURITY_AND_SAFETY.md`.

## Use the resolver
```bash
python3 shared/connectors/connectors.py --list
python3 shared/connectors/connectors.py --flags shared/connectors/feature-flags.example.json --plan
```
`--plan` prints each source's effective state, the active sources, the per-evidence-type provider chain
(primary + fallbacks), and any evidence-type **gaps** (no active provider).

## Maintenance
Offline JSON. Add a connector by appending to `connectors.json` (registry order = tie-break for the
provider chain). Connector + grade-scale + framework sources are watched by `standards-updater` so the
registries stay current.
