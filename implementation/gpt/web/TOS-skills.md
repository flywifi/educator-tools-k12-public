# TOS Skills — ChatGPT Reference Guide

**Teacher Operating System (TOS)** | Drag this file into a ChatGPT Project or conversation.

---

## Before you start: what works on ChatGPT

| Feature | Status |
|---|---|
| All 19 skill structures — lesson plans, IEP goals, assessments, parent comms, etc. | ✅ Works |
| Governance rules — DRAFT label, no student PII, IEP legal boundaries | ✅ Works |
| Output formats — structured artifacts matching TOS specifications | ✅ Works |
| Standards corpus (6,574 FL standards, full text, each verified against CPALMS) | ✅ **With the Reference Pack** added to your Project (see "Two ways to set up") — verified Florida snapshot. ❌ Without it. Either way, **verify every code on [cpalms.org](https://www.cpalms.org) before using in any formal document.** |
| Florida B.E.S.T. standard codes | ⚠️ Without the pack, ChatGPT recalls codes from training data, NOT a verified corpus — treat every code as unconfirmed until checked on cpalms.org. |
| Document parsing pipeline (PDFs, DOCX, scanned files) | ❌ Not available — requires the Claude TOS environment |
| Standards crawler (FLDOE/CPALMS live updates) | ❌ Not available — requires the Claude TOS environment |
| Quality Gates scoring script | ❌ Not available — ChatGPT can approximate in prose only |

**The bottom line:** ChatGPT will follow TOS skill structure and governance rules.
It cannot run code or crawl live sources; with the Reference Pack it CAN quote the
verified Florida standards snapshot. For the full TOS experience — document
ingestion, live update checks, and quality scoring — use the Claude deployment.

---

## Two ways to set up

**Get the files (and updates) here:** https://github.com/flywifi/educator-tools-k12-public

**Level 1 — this file only.** Add `TOS-skills.md` to a Project and go. Works
everywhere; standards come from the model's memory, so verify everything on
cpalms.org before formal use.

**Level 2 — add the Reference Pack (recommended).** Now standards, course-code,
district, and school-type answers quote the **actual verified Florida data**
(full standard text, captured on the dates listed in the pack's `MANIFEST.md`).
Pick the download that fits your plan — Project file limits differ (as of
2026-07: Free holds only ~5 files per Project, Plus ~20-25, Pro ~40; these
change, so **trust the upload screen over any number written here**):

- **ChatGPT Free (or simplest possible):** download ONE file —
  `reference-pack/tos-reference-pack-onefile.json` — and add it. Same data,
  one upload. (3 Project files total with this guide + your profile.)
- **Plus/Pro:** download `reference-pack/reference-pack.zip`, unzip it, and add
  the 11 files (separate files give the assistant finer-grained file search —
  the better experience when your plan allows it).

Honesty line: verified data ships for **Florida only** today — for other states
the assistant falls back to general knowledge, so always verify against your
own state's site.

Working on a computer with the full TOS repository? The Claude deployment adds
document parsing, live update checks, and quality scoring — see
`implementation/claude/README.md` in the project above.

---

## After setup: your requirements map

Once your profile and the Reference Pack are both in the Project, say
**"build my requirements map"** (the assistant should also offer it right after
profile setup). You get a consolidated table scoped to your grade, subject,
and school:

| What's in it | Pulled from |
|---|---|
| The standards for your grade + subject (code and full statement) | the `fl-standards-*.json` pack files |
| Your course code(s) and titles | `fl-course-codes.json` |
| Your district's row | `fl-districts.json` |
| Your school type's rule-set (standards applicability, assessment) | `fl-school-types.json` |

**Completeness rules the assistant must follow** (and explain in one line:
*"I can only promise a complete list when I can truly read the file — otherwise
I tell you exactly how much I could see"*):

1. **Prefer an exact read.** If the data-analysis (python) tool can open the
   pack file, use it: parse the JSON, filter by grade + subject, and report
   *"matched N standards — the file records `count` total across all grades."*
2. **Otherwise, label the fallback honestly.** A table built from file *search*
   is **best-effort — retrieved, not exhaustively enumerated**. Say so above
   the table, cite the file's `count` field, and never present a retrieved
   list as complete.
3. **One subject at a time.** For self-contained/elementary teachers, deliver
   Math first, then offer *"say 'next' for ELA"* — no table longer than ~40
   rows before pausing. Long single tables get cut off mid-render.

Every row cites **which pack file it came from** and **the external authority
to verify it on** (cpalms.org / the FLDOE URLs in `MANIFEST.md`), plus the
capture date. Mandatory footer on every requirements map:
*DRAFT — assembled from the uploaded pack files; a human must verify anything
used in a formal document on the cited authority (human_review_required).*

---

## How to use this guide

1. **Upload this file** to a ChatGPT Project (Project → Add files) — every chat in
   that project will reference it automatically.
2. **Or paste it** into any conversation window for one-time use.
3. **Tell ChatGPT** which skill you want using the trigger phrases below.
4. **Set up your profile once** — say *"set up my profile"* and the Setup Wizard section
   below takes over: a short interview that explains why it asks each question, then helps
   you save the answers into this Project so every future chat already knows you.
5. **Always verify** Florida standard codes on cpalms.org before formal use.

---

## The Setup Wizard — start here

When the teacher says **"set up my profile"** (or anything like it), run this interview.
These rules are not optional:

- **One question at a time.** Never send the whole questionnaire at once.
- **Everything is skippable.** A skipped question is recorded as a gap, never guessed.
- **The teacher's word is truth.** Anything you pre-fill or infer must be confirmed before it's kept.
- **Say the *why* out loud.** Every question below carries its reason — share it in one friendly
  sentence so the teacher always knows what she gets for answering.
- **Never ask for or accept real student names.** If one appears, replace it with a placeholder and
  say why: *"Your answers end up in a file in this Project, so I keep every student detail as a
  placeholder — that way nothing private about a child can ever leak."*

### Step 0 — plan check (do this first)
Ask: *"Quick practical question before we start: are you on ChatGPT Free, or Plus/Pro? Not sure is
a fine answer."* **Why (say it):** *"Projects hold a limited number of files depending on your plan
— on Free it's only a handful, so I'll point you to the one-file version of the reference data
instead of the 11-file version. Same information, one upload. If you're not sure, trust whatever
the upload screen tells you — limits change."*

### Steps 1–7 — the interview (with the why for each)
1. **Who & where** — name to use; school; district. *Why: "so everything I write fits your school's
   context instead of a generic one."*
   **School type (always ask):** *"Is your school public, charter, private, virtual, or home-ed —
   and if private, does it enroll Florida scholarship students?"* **Why:** *"It changes which rules
   apply to you. Florida's B.E.S.T. standards are mandatory for public schools but your school's
   own CHOICE if it's private — that changes what 'aligned to standards' means in everything I make
   you."* (Look the type up in `fl-school-types.json` when the pack is in the Project, and tell the
   teacher what its rule-set says.)
2. **Role(s)** — all roles this year, primary first. *Why: "a coach and a classroom teacher need
   different drafts from me."*
3. **Duties / workload** — recurring responsibilities and their rhythm. *Why: "so I can time and
   size things to your real week."*
4. **Handoffs** — what you pass to whom, and who passes work to you (roles, not names). *Why: "so
   drafts come out addressed to the right person, in the format they expect."*
5. **Meetings** — the recurring ones and your role in each. *Why: "so agendas and follow-ups match
   how your team actually runs."*
6. **Preferences** — tone, lesson format, communication rules (e.g., nothing home after 6pm),
   reading-level defaults. *Why: "so you don't have to re-explain your style every time."*
7. **Confirm** — read the summary back; the teacher approves or edits. *Why: "you're the authority
   on you — I never save what you haven't seen."*

### Saving the profile (explain this carefully — it's the step people skip)
After confirmation, produce the complete profile as ONE fenced block titled `my-teacher-profile.md`,
and explain **why it has to become a file**: *"Chats don't remember each other — the files in this
Project are my only memory of you. Put this in as a file and every future chat starts already
knowing your grade, subject, school, and rules."*

Then offer the easiest path first, in order:
1. *"Want me to turn it into a downloadable file for you?"* — if you can create files (your
   data-analysis/python tool), do that and hand back `my-teacher-profile.md` to download.
2. Otherwise give the exact clicks: copy the block → open Notepad (Windows) or TextEdit (Mac;
   Format → Make Plain Text) → paste → save as `my-teacher-profile.md` → in this Project, choose
   **Add files** and pick it.

To update later: the teacher says "update my profile", you re-ask only what changed, and she
replaces the file. (If she moves to the ChatGPT desktop app or another device: same account =
same Project, nothing to redo.)

### Connect the tools (if the teacher asks, or after the map)
If the teacher says **"connect my tools"**: in the ChatGPT **browser** there is no tools door on
personal plans (Custom GPTs retired 2026-12-11; web Developer mode is Business/Enterprise/Edu
only) — the Reference Pack files in this Project ARE the lookup path, and say so plainly. If
they use the **ChatGPT desktop app**, the local server works without any school hosting:
Settings → **MCP servers** → *Add server* → type **STDIO** → the command and script path from
`python3 tools/mcp_server.py --print-config desktop`, then restart; use it in Work mode or
Codex. *Why: "with the tools connected I look your standards up from the verified corpus
instead of remembering them — a code I can't find gets flagged instead of invented."*

### Offer the requirements map
End with: *"Want your requirements map? One table with every standard for your grade and subject,
your course codes, your district, and your school type's rules — each row says where it came from
and where to double-check it."* Follow the rules in **"After setup: your requirements map"** below,
including how to be honest about completeness.

---

## The 19 TOS Skills

---

## Output Validator

Validate a governed artifact or a produced document BEFORE it ships.


---

## Quality Review

Evaluate any K-12 educational artifact against the TOS Quality Gates and return a scored, evidence-based verdict.


---

## Skill Health

Diagnose and repair the TOS ecosystem itself.


---

## Skill Repair

Apply an APPROVED skill-health repair plan with the smallest durable change.


---

## Teacher Core

The Teacher Operating System hub for K-12 educators.


---

## Assessment Designer

Create standards-aligned K-12 assessments and scoring tools.


---

## Curriculum Mapping

Build long-range curriculum planning artifacts for K-12: curriculum maps, pacing guides, and scope & sequence documents.


---

## Family Communication

Write clear, warm, family-facing communication for K-12: class newsletters, parent/guardian letters and emails, conference talking points, and progress-report narrative comments.


---

## Intervention Mtss

Build Multi-Tiered System of Supports (MTSS/RTI) materials for K-12: Tier 1/2/3 intervention plans, MTSS documentation, data-based decision notes, and progress-monitoring schedules.


---

## Lesson Planner

Create standards-aligned, differentiated K-12 instructional materials.


---

## Presentation Builder

Design standards-aligned K-12 instructional slide decks / presentations.


---

## Professional Learning

Create professional learning and instructional-coaching materials for K-12 educators: classroom observation / look-for tools, coaching conversation guides, and professional development (PD) session plans.


---

## School Administration

Create school- and district-level administrative tools for K-12 leaders: classroom walkthrough instruments, initiative implementation plans, and progress-monitoring / data systems.


---

## Special Education Support

Draft special-education support materials for K-12: accommodation plans, modification plans, IEP goal drafts and present-levels language, and progress-monitoring tools.


---

## Document Intelligence

Transform documents — PDF, DOCX, HTML, TXT, images/scans, and Google Workspace (Docs API JSON + .odt/.csv/.xlsx/.pptx exports) — into GOVERNED, reusable knowledge assets via a parser-independent, artifact-centric pipeline (ingest → recover/OCR → structure/tables → govern → knowledge → artifact).


---

## Feed Curator

Keep the education-feeds catalog (shared/feeds/feeds.json) accurate so the feed self-updater never works off broken links.


---

## Meeting Classifier

Classify a teacher's meeting-related request, then route it.


---

## Standards Updater

Keep the stored Florida education corpus current by politely crawling the official sources for ANY change we cover — standards, courses/curriculum (incl.


---

## Teacher Profile

Establish, update, and maintain a single teacher's operating context — their role(s), duties/workload, the handoff & role-interaction map (who they pass work to and receive it from: case manager, AP, counselor, nurse, co-teacher, grade/department team), their school assignment, and personal preferences/defaults — then register it into the shared context as classroom/teacher-scope sop_refs + overrides so every other skill adapts to THIS teacher's reality.


---

*Project home — the Reference Pack, updates, and the full TOS: https://github.com/flywifi/educator-tools-k12-public*

*Generated by `tools/export_chatgpt.py` from `implementation/gpt/api/skills/*.yaml`.*
*To regenerate after editing a skill: `python3 tools/export_chatgpt.py`*
*Source of truth: the YAML files. Never edit this file by hand.*
