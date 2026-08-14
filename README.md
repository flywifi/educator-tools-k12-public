<!-- last_reviewed: 2026-08-11 | owner: tos-maintainer -->
# Teacher Operating System (TOS)

A set of AI assistants that help K–12 teachers create and double-check the everyday materials of
teaching — lesson and unit plans, assessments and rubrics, slide decks, curriculum maps, IEP/504
supports, intervention (MTSS) plans, family messages, and coaching/PD resources.

Everything it makes is aligned to your state's standards, built with differentiation in mind, and
**flagged for your review** — it's a strong starting point, not a final decision. It never uses real
student information; examples use placeholders only.

## What you can do with it
- Draft a standards-aligned lesson or unit plan
- Build assessments, rubrics, and answer keys
- Turn a lesson into a slide deck
- Map curriculum across a unit or a year
- Get differentiation and accommodation ideas for diverse learners (special education, English
  learners, gifted)
- Write family communication — and translate it
- Plan interventions / MTSS supports
- Prepare coaching and professional-learning materials

## Who it's for
Classroom teachers first — plus special educators, instructional coaches, and school administrators.
You don't need to be technical to use it.

## How you use it
Ask in plain language — e.g., *"Make me a 5th-grade fractions lesson aligned to my standards"* — and
the right assistant takes it from there. Two doors in, both written for non-technical readers:

- **On Claude** (Claude Code or the Cowork desktop app — same plugin; or claude.ai in the
  browser): **[implementation/claude/README.md](implementation/claude/README.md)** — the full
  experience, including the setup wizard and your personal requirements map.
- **On ChatGPT**: **[implementation/gpt/web/README.md](implementation/gpt/web/README.md)** — one
  file to drag in, plus an optional Reference Pack with the verified Florida data.

For the curious: **[docs/END_TO_END_WALKTHROUGH.md](docs/END_TO_END_WALKTHROUGH.md)** is a
technical validation log of a real start-to-finish run (shell commands and all — not a
getting-started guide).

## Under the hood (for the curious or technical)
You don't need any of this to use TOS — but here's how it's built:
- **A coordinator** (`skills/core/teacher-core`) reads your request and sends it to the right
  specialized skill.
- **Specialized skills** do the work (lesson planning, assessment design, special-education support,
  and so on), grouped under `skills/` as `core/`, `educator/`, `operations/`, and small
  single-purpose `atoms/`.
- **Shared engines** under `shared/` give every skill one source of truth for standards,
  differentiation, and quality.
- **A quality check** runs before anything is called "done," and an **automated consistency checker**
  (`tools/sync_check.py`) keeps the shared rules each skill carries identical to the originals.

## Verified standards (Florida)

A wrong standard code — or a real code quoted wrongly — is the most damaging mistake this system
could make, so it is checked by code, not by eye.

```bash
# Does every standard this artifact cites actually exist, and does it fit the grade band?
python3 tools/verify_standards.py --input my-artifact.json

# Is this restatement of a standard faithful to the official text?
python3 tools/verify_standards.py --compare MA.3.NSO.1.1 --text "Read and write numbers to 10,000."
```

- **Fully offline.** It reads a committed corpus of 6,583 Florida standards (B.E.S.T. / NGSSS,
  including access points) — no network, no account, no API key.
- **Honest about what it knows.** A code that is absent from an authoritative corpus is reported as
  `not_found` and blocks; a code absent from a *best-effort* corpus (social studies, ELD) is
  advisory, because a parser gap must never be reported as a fabricated standard. CCSS and NGSS are
  **scheme-only**: structure is checked, existence is not.
- **Checked against CPALMS, code by code — the whole corpus.** Every subject and grade has been
  checked against **CPALMS**, Florida's official standards site, in both directions, including a
  reverse census that catches standards CPALMS has and the corpus lacks. **All 6,574 codes match
  CPALMS's official text exactly** (math 1,127 · ELA 719 · science 1,450 · computer science 560 ·
  social studies 2,713 · ELD 5). Two real CPALMS standards absent from the source documents are
  recorded as provenance-stamped additions, and nine withdrawn computer-science standards as
  `retired` — flagged for review, never counted as verified. Results live in
  `shared/standards/resources/florida/data/overlays/` with the CPALMS URL and check date for every
  entry; the parsed corpus is never overwritten. An adversarial audit re-proved every `confirmed`
  label offline from the stored texts before this paragraph was written
  (`docs/audits/2026-08-13-sweep-completion-audit.md`).
- **What this proves, and what it does not.** Our standards documents were themselves downloaded
  from CPALMS (`sources.json`), so a match proves **parse fidelity** — that our extraction of a
  CPALMS document says what CPALMS's own database says. It is *not* independent corroboration from a
  second authority, and a CPALMS-side error would be invisible to it. Florida's administrative rule
  documents remain the legal source of record.
- **"Verified" means the text actually matches.** The comparison used to accept a 97 % similarity
  score — about three characters of slack on a typical standard, enough to let a changed number or a
  deleted "not" pass as verified. It now requires the two texts to be **the same text**, ignoring
  only whitespace. There is no similarity band, no prefix allowance, and no minimum-length rule;
  anything short of equality is recorded as needing review, never as verified.
- **Limits, stated plainly.** Verification is against CPALMS, which is also where the source
  documents came from — so a match proves parse fidelity, not independent corroboration, and a
  CPALMS-side error would be invisible. Currency decays from the check date (`checked_at` per
  entry): CPALMS revised two benchmarks and retired nine standards in the window this work covers.
  The live, generated breakdown is `ledger/cpalms-run-manifest.json`
  (`python3 tools/cpalms_verify.py --manifest`); trust it over any number written in prose,
  including this paragraph. Full residual-risk statements: `docs/audits/`.

Maintainers refreshing the verification (needs network):
`python3 tools/cpalms_verify.py --subject math --grades K,1,2,3,4,5 --out report.json` then
`--apply report.json` to review, `--write` to record. Nothing is ever applied without that review.

## Learn more
- **[docs/END_TO_END_WALKTHROUGH.md](docs/END_TO_END_WALKTHROUGH.md)** — a real teacher, start to
  finish (best place to begin).
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — how the pieces fit together.
- **[docs/QUALITY_MODEL.md](docs/QUALITY_MODEL.md)** — how outputs are checked for quality.
- **[protocol-layer/quality-gates.md](protocol-layer/quality-gates.md)** — the rules every output
  must pass before it's considered ready.
- **[CLAUDE.md](CLAUDE.md)** — conventions for developers working in this repo.

## What these words mean (quick glossary)
- **Skill** — one focused AI assistant (e.g., the lesson planner).
- **Coordinator (`teacher-core`)** — the skill that decides which other skill handles your request.
- **Quality gates** — a checklist every output must pass before it's considered ready.
- **Quality Ledger** — a running log of those quality decisions, so there's a record.
- **Drift guard (`tools/sync_check.py`)** — an automated check that keeps each skill's copy of the
  shared rules identical to the originals.
- **Decision support** — you get a strong draft to review and adjust; you, the educator, always make
  the final call.
