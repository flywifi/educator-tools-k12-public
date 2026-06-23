# Evidence model — piecing a meeting together from context clues (meeting-classifier)

Classify from whatever evidence is available, corroborate before asserting, and make uncertainty
visible. Evidence is normalized into the types defined in `shared/connectors/connectors.md` and supplied
by whatever connectors are on (or by manual paste / uploaded files via `shared/docintel/`).

## Clue precedence (strong → weak)
1. **Explicit statement** — the teacher says what it is ("my IEP meeting", "faculty meeting").
2. **Calendar event** — title, time, recurrence, organizer, location, attendees.
3. **Sender identity + title/role** (from the signature) — principal/AP → observation/faculty; case
   manager / LEA / staffing → IEP; 504 coordinator/counselor → 504; school nurse → health plan; parent
   → conference/parent_contact.
4. **Sender domain** — internal staff vs guardian/external vs district.
5. **Attendee roster + roles** — who's invited corroborates the type.
6. **Subject line**, then **email body** keywords.
7. **Prior thread / chat continuity** — what this is a follow-up to.
8. **Transcript / call notes** language.
9. **Attachments / filenames** — observation rubric, IEP draft, agenda.

## Connector → evidence mapping
Resolve active sources with `shared/connectors/connectors.py`. Live connectors are the **host AI's
native integrations** (Claude/OpenAI/Gemini/…); uploaded `.ics`/`.eml` files are read via
`shared/docintel/` (the `--file` ingest folds them into the clues). A signal's provider chain is
primary→fallbacks among **active** connectors; if the top provider is off/blocked — or
**district-restricted for that evidence even while active** (`restricted_sources`, failure class
`PERMISSION`) — **drop to the next available** source, record it in `execution_trace`, and **lower
confidence**. Skip connectors flagged off. `sis` is authoritative for **student** data
(name/guardians/plan flags) when connected.

## Convergence + confidence
- **Converge**: corroborate ≥2 weak available signals before asserting a high-stakes type
  (e.g., calendar title "IEP" + attendee "LEA rep" + attachment "IEP draft" ⇒ `iep_meeting`, high).
- A **single weak** signal ⇒ low confidence; if nothing stronger exists ⇒ `unknown`.
- A disabled/blocked/`metadata_only` source is **never** treated as an active/true path; degraded paths
  carry a failure class (`shared/connectors/connectors.md`).

## When to escalate to a human
- Any **individual-student determination**: IEP/504 obligation, eligibility, evaluation result, or a
  **medical** decision. The classifier states only the general rule + surfaces the **signed** plan;
  specifics go to the team / nurse / `special-education-support`.
- Never fabricate medical instructions, a student's contacts, or plan facts
  (`shared/students/student-data-policy.md`).

## When to emit a minority report (not a guess)
When two meeting types are **materially plausible** on the available evidence — classic case:
`annual_review_observation` vs `interim_observation` (a calendar "observation" with no formal-evaluation
corroboration) — or when SIS conflicts with the local student store, emit a decision record with a
minority report via `shared/context/sot_resolver.py` (policy `shared/context/minority-report.md`):
the **chosen** type, the **alternate(s)**, **why** the primary won, and **what evidence would overturn
it**. Do not bury the disagreement in prose.
