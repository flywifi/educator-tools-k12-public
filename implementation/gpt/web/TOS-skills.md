# TOS Skills — ChatGPT Reference Guide

**Teacher Operating System (TOS)** | Drag this file into a ChatGPT Project or conversation.

---

## Before you start: what works on ChatGPT

| Feature | Status |
|---|---|
| All 29 skill structures — lesson plans, IEP goals, assessments, parent comms, etc. | ✅ Works |
| Governance rules — DRAFT label, no student PII, IEP legal boundaries | ✅ Works |
| Output formats — structured artifacts matching TOS specifications | ✅ Works |
| Standards corpus (6,583 FL standards, full text) | ✅ **With the Reference Pack** added to your Project (see "Two ways to set up") — verified Florida snapshot. ❌ Without it. Either way, **verify every code on [cpalms.org](https://www.cpalms.org) before using in any formal document.** |
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

**Level 1 — this file only.** Add `TOS-skills.md` to a Project and go. Works
everywhere; standards come from the model's memory, so verify everything on
cpalms.org before formal use.

**Level 2 — add the Reference Pack (recommended).** Download the 11 files in
`implementation/gpt/web/reference-pack/` and add them to the same Project
(the pack uses 11 of your ~20 Project file slots; this file and your profile
use 2 more). Now standards, course-code, district, and school-type answers
quote the **actual verified Florida data** (full standard text, captured on the
dates listed in the pack's `MANIFEST.md`). Honesty line: verified data ships for **Florida only**
today — for other states the assistant falls back to general knowledge, so
always verify against your own state's site.

Working on a computer with the full TOS repository? The Claude deployment adds
document parsing, live update checks, and quality scoring — see
`implementation/claude/README.md`.

---

## After setup: your requirements map

Once your profile and the Reference Pack are both in the Project, say
**"build my requirements map"** (the assistant should also offer it right after
profile setup). You get ONE consolidated table scoped to your grade, subject,
and school:

| What's in it | Pulled from |
|---|---|
| Every standard for your grade + subject (code and full statement) | the `fl-standards-*.json` pack files |
| Your course code(s) and titles | `fl-course-codes.json` |
| Your district's row | `fl-districts.json` |
| Your school type's rule-set (standards applicability, assessment) | `fl-school-types.json` |

Every row cites **which pack file it came from** and **the external authority
to verify it on** (cpalms.org / the FLDOE URLs in `MANIFEST.md`), plus the
snapshot date. Mandatory footer on every requirements map:
*DRAFT — assembled from the uploaded pack files; a human must verify anything
used in a formal document on the cited authority (human_review_required).*

---

## How to use this guide

1. **Upload this file** to a ChatGPT Project (Project → Add files) — every chat in
   that project will reference it automatically.
2. **Or paste it** into any conversation window for one-time use.
3. **Tell ChatGPT** which skill you want using the trigger phrases below.
4. **Set up your profile once** — say *"set up my profile"*, answer the short interview,
   then save the `my-teacher-profile.md` file the assistant gives you into this same
   Project. Every future chat starts already knowing your grade, subject, and school.
5. **Always verify** Florida standard codes on cpalms.org before formal use.

---

## The 29 TOS Skills

---

## Teacher Core

TOS routing hub.

**Always provide:** request
**Optional:** grade · subject · artifact type hint · teacher context · force minority report

**Do not use for:** teacher_core to produce the actual artifact — it routes only.

---

## Lesson Planner

Design and produce standards-aligned K-12 lesson plans, unit plans, pacing guides, daily agendas, warm-ups, and exit tickets.

**Say something like:**
- "write me a lesson plan"
- "plan a unit on"
- "make a pacing guide"

**Always provide:** grade · subject · topic
**Optional:** artifact type · lesson duration minutes · standards · learning objectives · differentiation profiles · materials

**Do not use for:** lesson-planner to write IEP goals, accommodation plans, or progress-monitoring tools (use special-education-support).

---

## Assessment Designer

Design standards-aligned formative and summative assessments, rubrics, and performance tasks for K-12.

**Say something like:**
- "write me a quiz"
- "create a test on"
- "make a rubric for"
- "create a unit test"

**Always provide:** grade · subject · topic
**Optional:** assessment type · item count · item types · standards · bloom levels · dok levels

**Do not use for:** assessment-designer for IEP progress-monitoring measures (use special-education-support).

---

## Special Education Support

Generate IDEA-compliant IEP goal drafts, accommodation and modification plans, behavior support plans, transition planning documents, and progress notes for K-12 special education professionals.

**Say something like:**
- "write an IEP goal for"
- "draft accommodations for"

**Always provide:** request_type · grade
**Optional:** disability category · domain · subject · standards · present level of performance · annual goal focus

**Do not use for:** this skill to determine eligibility, make placement decisions, or produce legally binding documents.

---

## Family Communication

Draft family-facing communications for K-12 educators: parent emails, classroom newsletters, conference notes, progress updates, behavior notes, celebration messages, and permission forms.

**Say something like:**
- "write a parent email about"
- "draft a newsletter for"

**Always provide:** communication_type · grade
**Optional:** subject · key points · topic summary · tone · reading level target · language

**Do not use for:** family-communication to produce legally required special education notices (Prior Written Notices, Procedural Safeguards) — those require the district's official forms.

---

## Meeting Classifier

Classify an educator meeting from contextual clues and route it to the right TOS skill.

**Say something like:**
- "what kind of meeting is this"
- "classify this meeting"
- "Never determines IEP or 504 eligibility from meeting context"
- "Never interprets legal status of a meeting"

**Always provide:** meeting_context
**Optional:** participants · trigger document · grade · subject · output format · force minority report

**Do not use for:** meeting-classifier to produce meeting artifacts (use the routed skill).

---

## Quality Review

Score any TOS-generated K-12 artifact against the full 9-dimension Quality Gates rubric.

**Say something like:**
- "review this artifact"
- "does this pass quality gates"
- "run quality gates on"
- "does this meet the rubric"

**Always provide:** artifact · artifact_type
**Optional:** scoring mode · dimension focus · standards to verify · original request · rubric version · promote failures to eval

**Do not use for:** quality-review to score student work (it reviews educator-generated artifacts).; it to determine IEP eligibility or make legal determinations.

---

## Curriculum Mapping

Build standards-based curriculum maps, pacing guides, scope and sequence documents, and standards-alignment matrices for K-12.

**Say something like:**
- "map the curriculum for"
- "create a pacing guide for the year"
- "standards coverage map"
- "year-at-a-glance"

**Always provide:** grade · subject
**Optional:** artifact type · time period · total instructional days · standards · course name · existing units

**Do not use for:** curriculum-mapping to write individual lesson plans (use lesson-planner).

---

## Intervention Mtss

Design Tier 1, Tier 2, and Tier 3 MTSS/RTI intervention plans, progress-monitoring protocols, and data-review meeting tools for K-12.

**Say something like:**
- "write a Tier 2 intervention plan"
- "create an MTSS plan for"
- "progress monitoring schedule"

**Always provide:** tier · concern_area · grade
**Optional:** subject · student profile description · current performance data · intervention frequency per week · intervention duration minutes · intervention setting

**Do not use for:** intervention-mtss to write IEP goals (use special-education-support).

---

## Presentation Builder

Build structured slide deck outlines, speaker notes, and (when office_authoring capability is available) real .pptx files for K-12 professional and instructional contexts.

**Say something like:**
- "make a slide deck about"
- "build a presentation on"
- "create slides for"
- "I need a PowerPoint on"

**Always provide:** topic · audience
**Optional:** grade · subject · slide count · duration minutes · output format · standards

**Do not use for:** presentation-builder to write lesson plans (use lesson-planner).

---

## Professional Learning

Design professional learning artifacts for K-12 educators: instructional coaching guides, classroom observation look-fors, PD session plans, collaborative inquiry protocols, and lesson study frameworks.

**Say something like:**
- "write a coaching guide for"
- "create observation look-fors"
- "professional learning plan on"

**Always provide:** artifact_type · topic
**Optional:** grade band · subject · participant role · duration minutes · session count · desired outcomes

**Do not use for:** professional-learning to produce formal evaluation rubrics or conduct teacher performance ratings (those are HR/administrative).

---

## School Administration

Generate school and system-level administrative artifacts: classroom walkthrough instruments, initiative implementation plans, data-review meeting agendas, professional communication templates, school improvement planning tools, and policy explanation documents for K-12 school leaders.

**Say something like:**
- "create a walkthrough observation tool"
- "build an implementation plan for"
- "school improvement plan component"
- "meeting agenda for the leadership team"

**Always provide:** artifact_type · topic
**Optional:** grade band · subject area · audience · walkthrough focus areas · implementation phases · timeline

**Do not use for:** school-administration to write individual teacher formal evaluation instruments (those are HR/district functions).

---

## Document Intelligence

Parse, extract, and structure content from education-sector documents: PDFs, DOCX, HTML pages, and scanned images.

**Say something like:**
- "read this PDF and extract"
- "parse this document"
- "what does this say"
- "extract the standards from this file"

**Always provide:** document_source
**Optional:** document type · extraction goal · page range · output format · ocr enabled · ocr language

**Do not use for:** document-intelligence to make educational decisions from a document — it extracts and structures content, it does not interpret or apply it.

---

## Output Validator

Validate TOS-generated JSON artifacts against their JSON Schema and a governance rule catalog (no fabrication, no real PII, metadata block present, human_review_required: true, standard codes verified).

**Say something like:**
- "validate this artifact"
- "check the schema"
- "does this JSON conform"
- "governance check"

**Always provide:** artifact
**Optional:** schema type · validation mode · standards to verify · promote to eval · strict mode · pii scan depth

**Do not use for:** output-validator to score pedagogical quality (use quality-review).

---

## Feed Curator

Manage the TOS RSS/Atom feed catalog: validate existing feeds for health (dead links, redirects, stale content, wrong labels), discover new feed candidates from authoritative education sources, propose a human-reviewable change set, and apply only mechanically-safe repairs automatically.

**Say something like:**
- "validate the feed catalog"
- "find new education feeds"
- "check which feeds are dead"
- "curator status"

**Always provide:** action
**Optional:** seed url · discovery topic · proposal file · audit log entry id · feed id · tier filter

**Do not use for:** feed-curator to harvest or process feed items (use tools/feeds_update.py for that).

---

## Standards Updater

Crawl, detect, verify, and report on changes to Florida K-12 standards corpora: B.E.S.T., NGSSS, CTE frameworks, Florida Statutes Title XLVIII (ch.1000-1013), State Board rules (FAC 6A), FAST/B.E.S.T./EOC assessment fact sheets, graduation requirements (s.1003.4282 F.S.), and WIDA/ELD standards.

**Say something like:**
- "check if standards have changed"
- "crawl FLDOE for updates"
- "currency brief"
- "crawl CPALMS"

**Always provide:** action
**Optional:** state · report path · out dir · max retries · saturation n · checkpoint path

**Do not use for:** standards-updater to write lesson plans or assessments.

---

## Teacher Profile

Initialize, manage, and query the TOS teacher operating context: role, grade band, subject, school, district, student demographics, local constraints, collaboration network, and system preferences (offline tier, retrieval mode, feed update mode).

**Say something like:**
- "set up my TOS profile"
- "update my profile"
- "what's in my profile"
- "change my school"

**Always provide:** action
**Optional:** field name · field value · reset scope · preference updates · teacher context

**Do not use for:** teacher-profile to generate lesson plans, assessments, or IEP documents (route those to the appropriate skill).

**On ChatGPT:** ChatGPT cannot run the TOS profile script, so the profile lives in your Project instead: say "set up my profile" and answer the short interview (role, grade, subject, school/district, class context, preferences — placeholders only, never real student names). The assistant then returns ONE complete file in a fenced block titled my-teacher-profile.md. Save that block as a file and add it to this same Project. Any chat that can see my-teacher-profile.md treats it as your registered profile (teacher-stated facts still outrank everything else). To change it, say "update my profile" and replace the file.

---

## Skill Health

Diagnose and audit the TOS ecosystem itself.

**Say something like:**
- "is the ecosystem healthy"
- "why did this skill fail"
- "audit the skills"
- "diagnose the environment"

**Always provide:** action
**Optional:** skill name · traces dir · artifact · artifact schema · tos check groups · tos check timeout

**Do not use for:** skill-health to author lessons, assessments, or IEP documents (wrong skill).; it to score classroom artifacts (use quality-review).

---

## Skill Repair

Apply an approved skill-health repair plan with the smallest durable change.

**Say something like:**
- "apply the repair plan"
- "fix the broken skill"
- "patch this skill"
- "run the approved fixes"

**Always provide:** action
**Optional:** repair plan · skill name · confirmation acknowledged · snapshot before · stop on first failure

**Do not use for:** skill-repair to diagnose issues (use skill-health first).

---

## Activity Generate

Generate ONE complete learning activity for a given objective, grade, and subject.

**Say something like:**
- "generate an activity for"
- "what's a good activity for this objective"
- "create a classroom activity about"
- "design one activity for"

**Always provide:** objective · grade · subject
**Optional:** activity type · dok level · duration minutes · grouping · materials available · standard

**Do not use for:** atom-activity-generate to write a complete multi-activity lesson (use lesson-planner).

---

## Assessment Item

Generate ONE assessment item with its answer key.

**Say something like:**
- "write a multiple choice question about"
- "create a short answer question for"
- "make a constructed response item on"
- "write one test question about"

**Always provide:** topic · grade · subject · item_type
**Optional:** standard · bloom level · dok level · include answer key · include distractor analysis · point value

**Do not use for:** atom-assessment-item to write a full assessment (use assessment-designer).

---

## Differentiate

Apply ONE differentiation profile to a piece of educational content.

**Say something like:**
- "differentiate this for ELL students"
- "modify this for my IEP students"
- "make a gifted version of"
- "adapt this for below-grade readers"

**Always provide:** content · differentiation_profile · grade · subject
**Optional:** learning target · ell proficiency level · output format · preserve item count

**Do not use for:** atom-differentiate to write student-specific IEP goals (use atom-iep-goal or special-education-support).

---

## Iep Goal

Write ONE SMART IEP annual goal following the IDEA-compliant three-part formula: Condition + Behavior + Criterion.

**Say something like:**
- "write an IEP goal for"
- "draft an annual goal"
- "IEP reading goal"
- "behavior goal for IEP"

**Always provide:** domain · grade · present_level_of_performance · legal_notice_acknowledged
**Optional:** annual goal focus · measurement criterion · measurement tool · condition · standard · progress monitoring frequency

**Do not use for:** atom-iep-goal to write lesson plan objectives (use atom-objective-write).; it to determine eligibility or make placement decisions.

---

## Misconception

Identify 2-5 common student misconceptions for a given topic, grade, and subject.

**Say something like:**
- "what misconceptions do students have about"
- "common mistakes on"
- "why do students struggle with"
- "what errors do students make on"

**Always provide:** topic · grade · subject
**Optional:** count · standard · include instructional remedy · include assessment probes · source type

**Do not use for:** atom-misconception to diagnose an individual student's specific misconception (that requires looking at the student's actual work).

---

## Objective Write

Write 1-3 measurable SWBAT (Students Will Be Able To) learning objectives for a given grade, subject, and standard.

**Say something like:**
- "write learning objectives for"
- "SWBAT for"
- "what's the learning target"
- "write objectives for this standard"

**Always provide:** topic · grade · subject
**Optional:** standards · bloom level · count · lesson context · include assessment suggestion

**Do not use for:** atom-objective-write to write the full lesson plan (use lesson-planner).

---

## Parent Comm

Draft ONE parent/guardian communication: email, text-home note, or brief letter.

**Say something like:**
- "write a parent note about"
- "draft an email to parents"
- "text home about"
- "quick parent communication"

**Always provide:** communication_purpose · grade
**Optional:** subject · key points · tone · medium · reading level target · language

**Do not use for:** atom-parent-comm for legally required IDEA notices (Prior Written Notice, Procedural Safeguards) — use district official forms.

---

## Quality Check

Run ONE quality gate check on an artifact excerpt and return pass/fail/warn with a score, explanation, and corrective action.

**Say something like:**
- "quick check on the safety of this"
- "does this pass the governance gate"
- "check the integrity of this"
- "is this educationally sound"

**Always provide:** artifact_excerpt · dimension
**Optional:** artifact type · original request · standards claimed · include corrective action

**Do not use for:** atom-quality-check as a substitute for the full quality-review (use quality-review to get the composite score and Approved/Rejected verdict).

---

## Reading Level

Estimate the reading level of a text passage (up to ~500 words).

**Say something like:**
- "what reading level is this"
- "check the readability of"
- "reading level check"
- "Flesch-Kincaid for this passage"

**Always provide:** passage
**Optional:** grade context · purpose · output format · flag accessibility issues

**Do not use for:** atom-reading-level to assess student reading ability or generate Lexile scores for student placement (those require standardized assessments).

---

## Standards Match

Look up Florida B.E.S.T.

**Say something like:**
- "what standards cover"
- "find the standard for"

**Always provide:** topic · grade · subject
**Optional:** standards corpus · max results · keyword override · include related standards · strand filter

**Do not use for:** atom-standards-match to write lesson plans or assessments — it returns codes only.

---

*Generated by `tools/export_chatgpt.py` from `implementation/gpt/api/skills/*.yaml`.*
*To regenerate after editing a skill: `python3 tools/export_chatgpt.py`*
*Source of truth: the YAML files. Never edit this file by hand.*
