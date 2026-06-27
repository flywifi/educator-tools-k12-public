# TOS Skills — ChatGPT Reference Guide

**Teacher Operating System (TOS)** | Drag this file into a ChatGPT Project or conversation.

---

## Before you start: what works on ChatGPT

| Feature | Status |
|---|---|
| All 29 skill structures — lesson plans, IEP goals, assessments, parent comms, etc. | ✅ Works |
| Governance rules — DRAFT label, no student PII, IEP legal boundaries | ✅ Works |
| Output formats — structured artifacts matching TOS specifications | ✅ Works |
| Florida B.E.S.T. standard codes | ⚠️ ChatGPT recalls from training data, NOT a verified corpus. **Always verify every standard code on [cpalms.org](https://www.cpalms.org) before using in any formal document.** |
| Standards corpus search (6,583 FL standards) | ❌ Not available — requires the Claude TOS environment |
| Document parsing pipeline (PDFs, DOCX, scanned files) | ❌ Not available — requires the Claude TOS environment |
| Standards crawler (FLDOE/CPALMS live updates) | ❌ Not available — requires the Claude TOS environment |
| Quality Gates scoring script | ❌ Not available — ChatGPT can approximate in prose only |

**The bottom line:** ChatGPT will follow TOS skill structure and governance rules.
It cannot run code, query the verified standards corpus, or crawl live sources.
For the full TOS experience — including verified standards, document ingestion, and
quality scoring — use the Claude deployment.

---

## How to use this guide

1. **Upload this file** to a ChatGPT Project (Project → Add files) — every chat in
   that project will reference it automatically.
2. **Or paste it** into any conversation window for one-time use.
3. **Tell ChatGPT** which skill you want using the trigger phrases below.
4. **Always verify** Florida standard codes on cpalms.org before formal use.

---

## The 29 TOS Skills

---

## Teacher Core

TOS routing hub.

**Always provide:** request
**Optional:** grade · subject · artifact type hint · teacher context · force minority report

**Do not use for:** teacher_core to produce the actual artifact — it routes only. After receiving the

---

## Lesson Planner

Design and produce standards-aligned K-12 lesson plans, unit plans, pacing guides, daily agendas, warm-ups, and exit tickets.

**Always provide:** grade · subject · topic
**Optional:** artifact type · lesson duration minutes · standards · learning objectives · differentiation profiles · materials

**Do not use for:** lesson-planner to write IEP goals, accommodation plans, or progress-monitoring

---

## Assessment Designer

Design standards-aligned formative and summative assessments, rubrics, and performance tasks for K-12.

**Say something like:**
- "create a unit test", "write 10 multiple choice questions on"

**Always provide:** grade · subject · topic
**Optional:** assessment type · item count · item types · standards · bloom levels · dok levels

**Do not use for:** assessment-designer for IEP progress-monitoring measures (use

---

## Special Education Support

Generate IDEA-compliant IEP goal drafts, accommodation and modification plans, behavior support plans, transition planning documents, and progress notes for K-12 special education professionals.

**Always provide:** request_type · grade
**Optional:** disability category · domain · subject · standards · present level of performance · annual goal focus

**Do not use for:** this skill to determine eligibility, make placement decisions, or produce legally

---

## Family Communication

Draft family-facing communications for K-12 educators: parent emails, classroom newsletters, conference notes, progress updates, behavior notes, celebration messages, and permission forms.

**Always provide:** communication_type · grade
**Optional:** subject · key points · topic summary · tone · reading level target · language

**Do not use for:** family-communication to produce legally required special education notices (Prior

---

## Meeting Classifier

Classify an educator meeting from contextual clues and route it to the right TOS skill.

**Say something like:**
- "Never determines IEP or 504 eligibility from meeting context"
- "Never interprets legal status of a meeting"
- "Ambiguous classification always surfaces a minority report rather than guessing"
- "human_review_required: true on every output"

**Always provide:** meeting_context
**Optional:** participants · trigger document · grade · subject · output format · force minority report

**Do not use for:** meeting-classifier to produce meeting artifacts (use the routed skill). Do NOT use

---

## Quality Review

Score any TOS-generated K-12 artifact against the full 9-dimension Quality Gates rubric.

**Say something like:**
- "run quality gates on", "does this meet the rubric"

**Always provide:** artifact · artifact_type
**Optional:** scoring mode · dimension focus · standards to verify · original request · rubric version · promote failures to eval

**Do not use for:** quality-review to score student work (it reviews educator-generated artifacts).; it to determine IEP eligibility or make legal determinations.

---

## Curriculum Mapping

Build standards-based curriculum maps, pacing guides, scope and sequence documents, and standards-alignment matrices for K-12.

**Say something like:**
- "standards coverage map", "year-at-a-glance", "map all standards for", "pacing calendar"

**Always provide:** grade · subject
**Optional:** artifact type · time period · total instructional days · standards · course name · existing units

**Do not use for:** curriculum-mapping to write individual lesson plans (use lesson-planner). Do NOT

---

## Intervention Mtss

Design Tier 1, Tier 2, and Tier 3 MTSS/RTI intervention plans, progress-monitoring protocols, and data-review meeting tools for K-12.

**Say something like:**
- "progress monitoring schedule"

**Always provide:** tier · concern_area · grade
**Optional:** subject · student profile description · current performance data · intervention frequency per week · intervention duration minutes · intervention setting

**Do not use for:** intervention-mtss to write IEP goals (use special-education-support). Do NOT use

---

## Presentation Builder

Build structured slide deck outlines, speaker notes, and (when office_authoring capability is available) real .pptx files for K-12 professional and instructional contexts.

**Say something like:**
- "I need a PowerPoint on", "design a presentation for my PLC", "build a parent night deck"
- "create a PD presentation about", "slide outline for", "presentation for my principal on"

**Always provide:** topic · audience
**Optional:** grade · subject · slide count · duration minutes · output format · standards

**Do not use for:** presentation-builder to write lesson plans (use lesson-planner). Do NOT use it

---

## Professional Learning

Design professional learning artifacts for K-12 educators: instructional coaching guides, classroom observation look-fors, PD session plans, collaborative inquiry protocols, and lesson study frameworks.

**Say something like:**
- "professional learning plan on"

**Always provide:** artifact_type · topic
**Optional:** grade band · subject · participant role · duration minutes · session count · desired outcomes

**Do not use for:** professional-learning to produce formal evaluation rubrics or conduct teacher

---

## School Administration

Generate school and system-level administrative artifacts: classroom walkthrough instruments, initiative implementation plans, data-review meeting agendas, professional communication templates, school improvement planning tools, and policy explanation documents for K-12 school leaders.

**Say something like:**
- "school improvement plan component", "meeting agenda for the leadership team", "data review"
- "faculty meeting agenda", "write a memo to staff about", "principal walkthrough form"

**Always provide:** artifact_type · topic
**Optional:** grade band · subject area · audience · walkthrough focus areas · implementation phases · timeline

**Do not use for:** school-administration to write individual teacher formal evaluation instruments

---

## Document Intelligence

Parse, extract, and structure content from education-sector documents: PDFs, DOCX, HTML pages, and scanned images.

**Say something like:**
- "extract the standards from this file", "pull the tables from this report", "summarize this"
- "what standards are cited in this file", "extract text from this scanned packet"
- "pdf_hifi: high-fidelity PDF parse with layout and column awareness (requires PyMuPDF/pdfplumber)"
- "ocr: offline OCR for scanned documents (requires tesseract + pytesseract)"

**Always provide:** document_source
**Optional:** document type · extraction goal · page range · output format · ocr enabled · ocr language

**Do not use for:** document-intelligence to make educational decisions from a document — it extracts

---

## Output Validator

Validate TOS-generated JSON artifacts against their JSON Schema and a governance rule catalog (no fabrication, no real PII, metadata block present, human_review_required: true, standard codes verified).

**Say something like:**
- "governance check", "check for PII", "verify the metadata block", "is the standard code"

**Always provide:** artifact
**Optional:** schema type · validation mode · standards to verify · promote to eval · strict mode · pii scan depth

**Do not use for:** output-validator to score pedagogical quality (use quality-review). Do NOT use

---

## Feed Curator

Manage the TOS RSS/Atom feed catalog: validate existing feeds for health (dead links, redirects, stale content, wrong labels), discover new feed candidates from authoritative education sources, propose a human-reviewable change set, and apply only mechanically-safe repairs automatically.

**Say something like:**
- "check which feeds are dead", "curator status", "revert a feed change", "auto-repair feeds"
- "canonical: primary government/standards sources (FLDOE, CPALMS, FL Legislature, WIDA) —"
- "news_teacher_student: curated news on issues affecting teachers and students (secondary)"
- "product_updates: edtech/vendor feeds — OFF by default, opt-in only"

**Always provide:** action
**Optional:** seed url · discovery topic · proposal file · audit log entry id · feed id · tier filter

**Do not use for:** feed-curator to harvest or process feed items (use tools/feeds_update.py for that).

---

## Standards Updater

Crawl, detect, verify, and report on changes to Florida K-12 standards corpora: B.E.S.T., NGSSS, CTE frameworks, Florida Statutes Title XLVIII (ch.1000-1013), State Board rules (FAC 6A), FAST/B.E.S.T./EOC assessment fact sheets, graduation requirements (s.1003.4282 F.S.), and WIDA/ELD standards.

**Say something like:**
- "currency brief", "crawl CPALMS", "check the source URLs", "standards refresh", "is my"
- "document discovery: new/changed files found via crawl_seeds in sources.json"
- "content-change monitoring: sha256 of watch_pages (statute/rule/guidance pages)"

**Always provide:** action
**Optional:** state · report path · out dir · max retries · saturation n · checkpoint path

**Do not use for:** standards-updater to write lesson plans or assessments. Do NOT use it to

---

## Teacher Profile

Initialize, manage, and query the TOS teacher operating context: role, grade band, subject, school, district, student demographics, local constraints, collaboration network, and system preferences (offline tier, retrieval mode, feed update mode).

**Say something like:**
- "change my school", "reset my preferences", "I moved to a new school", "set my grade level"
- "update my subject", "configure TOS for my class", "show my profile", "what does TOS know"
- "preferences --reset clears preferences without deleting identity/role"
- "school_change re-runs school/standards scope questions"

**Always provide:** action
**Optional:** field name · field value · reset scope · preference updates · teacher context

**Do not use for:** teacher-profile to generate lesson plans, assessments, or IEP documents (route

---

## Skill Health

Diagnose and audit the TOS ecosystem itself.

**Say something like:**
- "diagnose the environment", "what needs updating for the new skill", "repair plan"
- "check drift", "run health check", "what's broken", "scan all skills", "impact analysis"

**Always provide:** action
**Optional:** skill name · traces dir · artifact · artifact schema · tos check groups · tos check timeout

**Do not use for:** skill-health to author lessons, assessments, or IEP documents (wrong skill).; it to score classroom artifacts (use quality-review). human_review_required: true

---

## Skill Repair

Apply an approved skill-health repair plan with the smallest durable change.

**Say something like:**
- "run the approved fixes", "apply mechanical fixes", "skill repair dry run", "what would"

**Always provide:** action
**Optional:** repair plan · skill name · confirmation acknowledged · snapshot before · stop on first failure

**Do not use for:** skill-repair to diagnose issues (use skill-health first). Do NOT use it to

---

## Atom Standards Match

Look up Florida B.E.S.T.

**Always provide:** topic · grade · subject
**Optional:** standards corpus · max results · keyword override · include related standards · strand filter

**Do not use for:** atom-standards-match to write lesson plans or assessments — it returns codes only.

---

## Atom Objective Write

Write 1-3 measurable SWBAT (Students Will Be Able To) learning objectives for a given grade, subject, and standard.

**Say something like:**
- "write objectives for this standard", "measurable objectives for", "learning goals for"

**Always provide:** topic · grade · subject
**Optional:** standards · bloom level · count · lesson context · include assessment suggestion

**Do not use for:** atom-objective-write to write the full lesson plan (use lesson-planner). Do NOT use

---

## Atom Activity Generate

Generate ONE complete learning activity for a given objective, grade, and subject.

**Say something like:**
- "create a classroom activity about", "design one activity for", "build an activity for"
- "I need an activity that teaches"

**Always provide:** objective · grade · subject
**Optional:** activity type · dok level · duration minutes · grouping · materials available · standard

**Do not use for:** atom-activity-generate to write a complete multi-activity lesson (use

---

## Atom Assessment Item

Generate ONE assessment item with its answer key.

**Say something like:**
- "make a constructed response item on", "write one test question about", "assessment item for"

**Always provide:** topic · grade · subject · item_type
**Optional:** standard · bloom level · dok level · include answer key · include distractor analysis · point value

**Do not use for:** atom-assessment-item to write a full assessment (use assessment-designer). Do NOT

---

## Atom Differentiate

Apply ONE differentiation profile to a piece of educational content.

**Say something like:**
- "make a gifted version of", "adapt this for below-grade readers", "ELL scaffold for"
- "504 accommodations for this activity", "differentiated version for"

**Always provide:** content · differentiation_profile · grade · subject
**Optional:** learning target · ell proficiency level · output format · preserve item count

**Do not use for:** atom-differentiate to write student-specific IEP goals (use atom-iep-goal or

---

## Atom Quality Check

Run ONE quality gate check on an artifact excerpt and return pass/fail/warn with a score, explanation, and corrective action.

**Say something like:**
- "check the integrity of this", "is this educationally sound", "accessibility check on this"

**Always provide:** artifact_excerpt · dimension
**Optional:** artifact type · original request · standards claimed · include corrective action

**Do not use for:** atom-quality-check as a substitute for the full quality-review (use quality-review

---

## Atom Reading Level

Estimate the reading level of a text passage (up to ~500 words).

**Say something like:**
- "reading level check", "Flesch-Kincaid for this passage", "readability of this text"

**Always provide:** passage
**Optional:** grade context · purpose · output format · flag accessibility issues

**Do not use for:** atom-reading-level to assess student reading ability or generate Lexile

---

## Atom Misconception

Identify 2-5 common student misconceptions for a given topic, grade, and subject.

**Say something like:**
- "why do students struggle with", "what errors do students make on", "misconceptions for"
- "common student errors in", "what do kids get wrong about"

**Always provide:** topic · grade · subject
**Optional:** count · standard · include instructional remedy · include assessment probes · source type

**Do not use for:** atom-misconception to diagnose an individual student's specific misconception

---

## Atom Parent Comm

Draft ONE parent/guardian communication: email, text-home note, or brief letter.

**Say something like:**
- "quick parent communication", "write a note home", "parent email for", "family message about"

**Always provide:** communication_purpose · grade
**Optional:** subject · key points · tone · medium · reading level target · language

**Do not use for:** atom-parent-comm for legally required IDEA notices (Prior Written Notice,

---

## Atom Iep Goal

Write ONE SMART IEP annual goal following the IDEA-compliant three-part formula: Condition + Behavior + Criterion.

**Say something like:**
- "behavior goal for IEP", "communication goal draft", "transition goal for", "SMART IEP goal"

**Always provide:** domain · grade · present_level_of_performance · legal_notice_acknowledged
**Optional:** annual goal focus · measurement criterion · measurement tool · condition · standard · progress monitoring frequency

**Do not use for:** atom-iep-goal to write lesson plan objectives (use atom-objective-write).; it to determine eligibility or make placement decisions.

---

*Generated by `tools/export_chatgpt.py` from `platforms/openai/skills/*.yaml`.*
*To regenerate after editing a skill: `python3 tools/export_chatgpt.py`*
*Source of truth: the YAML files. Never edit this file by hand.*
