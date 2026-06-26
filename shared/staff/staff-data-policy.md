# Staff / role directory — data-handling policy (canonical, GATED)

A teacher's workflow benefits from knowing **who holds which role** at their school — the case manager
for a shared student, the AP who signs referrals, the counselor, the nurse. This engine can hold that
**staff directory** (name, work email, position, department, school) so handoffs resolve to real people.
It is **OFF by default** and **authorized-first**, because staff personal data carries real ToS/privacy
obligations that student-style "legitimate educational interest" does **not** automatically cover.

## Honest legal caveat (read first)
- **Bulk-harvesting public staff emails is not a freebie.** Many district sites' Terms of Service
  prohibit scraping; some jurisdictions treat work emails as personal data (GDPR-style rules,
  state privacy laws). "It's on a public page" ≠ "you may crawl, store, and reuse it at scale."
- Therefore this engine is **authorized-first** and **minimum-necessary**, never an indiscriminate
  scraper. When in doubt, it asks the user / records a gap rather than harvesting.

## Source order (authorized-first)
1. **Authorized directory / SIS / HR connector** the teacher already has access to — the right source.
2. **Teacher-provided list** — the teacher pastes/uploads the people they work with (consented by use).
3. **Polite public crawl** — ONLY where `robots.txt` **and** the site ToS permit, identifying UA, rate
   limited (same discipline as `tools/standards_refresh.py`). Disabled unless explicitly authorized.

## The gate (off by default)
- Capability `staff_ingest` (see `tools/dependencies.json`) defaults **off**. It activates only when a
  deployment sets `STAFF_INGEST_AUTHORIZED=true` (an explicit, recorded authorization) **and** chooses a
  source above. With no authorization, `staff.py` runs in **read-only placeholder mode** and every
  ingest path is a recorded gap, not a silent crawl.
- Crawling is additionally bound by robots.txt + ToS at fetch time; a disallowed fetch is a gap.

## Storage (mirrors the student-data adapter)
- `local_gitignored` — real directory in `staff.local.json` (or `shared/staff/local/`), **gitignored**,
  the default where a writable FS exists.
- `session_ephemeral` / `uploaded_file` — paste/upload per session; nothing persisted.
- `connector_directory` — a live HR/directory connector is authoritative; no local copy needed.
- Committed repo content is **placeholders only** (`staff.example.json`); the drift guard keeps real
  staff data out of tracked files.

## Cadence & precedence
- **Not refreshed on the school cadence.** Staff turns over less predictably than schools open/close;
  refresh on demand or when a handoff fails to resolve, not on a fixed crawl schedule.
- An authorized directory/connector is **authoritative**; the local store is fallback/cache. Conflicts
  surface via the resolver (`shared/context/sot_resolver.py`) — never silently merged.

## Use with teacher-profile (consent-gated person links)
The teacher profile maps handoffs to **roles** (case_manager, AP, counselor). This directory can attach
an **optional person link** to a role — but only with the teacher's confirmation, and only from an
authorized source. Role-based handoffs keep working with **no** staff data at all.

## Non-negotiables
- **No student data** here (this is staff). **No staff PII in committed files** — placeholders only.
- `minimum-necessary`: store only the fields a handoff needs (name, role, work email, department, school).
- `human_review_required: true` on every output; provenance + an `authorized` flag on every record.
