# florida-best.md
## Florida Standards Adapter — B.E.S.T. + NGSSS (populated state set)
Canonical source for the Standards Engine (`standards-framework.md`). Florida is the first fully
populated state via the pattern in `state-standards-model.md`. **Current for the 2026–2027 school
year** (verified June 2026): B.E.S.T. (Math/ELA, adopted 2020) and NGSSS (Science/Social Studies)
remain Florida's adopted standards.

> **Staying current (read this first).** The coding schemes below are **current for 2026–2027** and
> stable; the *content* is maintained live. The **canonical authority is CPALMS** — search
> `https://www.cpalms.org/search/Standard`, download `https://www.cpalms.org/downloads` (standards
> PDFs are hosted on the CPALMS CDN `cpalmsmediaprod.blob.core.windows.net`). Subject standards pages:
> FLDOE `https://www.fldoe.org/academics/standards/`. Assessment (FAST/B.E.S.T./EOC):
> `https://www.fldoe.org/accountability/assessments/k-12-student-assessment/`. EL/WIDA:
> `https://wida.wisc.edu/memberships/consortium/fl`. Always prefer these live sources; never invent a
> code — confirm on CPALMS (`protocols/standards-verification.md`). Refresh: `tools/standards_refresh.py`.

## Frameworks (use these in metadata `standards_set`)
| Framework | Subject | System | Live source |
|---|---|---|---|
| `FL-BEST-Math` | Mathematics | B.E.S.T. | CPALMS |
| `FL-BEST-ELA` | English Language Arts | B.E.S.T. | CPALMS |
| `FL-NGSSS-Sci` | Science | NGSSS | CPALMS |
| `FL-SS` | Social Studies | NGSSS/state | CPALMS |
| `FL-CS` | Computer Science | state | CPALMS |
| `FL-ELD` | English Language Development | state (WIDA-aligned) | CPALMS / WIDA |

Relationship to national sets: **Florida does not use CCSS** — B.E.S.T. replaced it (independent
codes). Science/Social Studies are **NGSSS** (Next Generation Sunshine State Standards). When a user
is in Florida, prefer these over CCSS/NGSS.

## Coding schemes (verified against the official documents; current for 2026–27)

**Math (B.E.S.T.)** — `MA.<grade>.<strand>.<standard>.<benchmark>`
- e.g., `MA.K.NSO.1.1` = Kindergarten · Number Sense & Operations · standard 1 · benchmark 1.
- High school by course: `MA.912.<strand>.*`.
- Strands include: NSO (Number Sense & Operations), FR (Fractions), AR (Algebraic Reasoning),
  M (Measurement), GR (Geometric Reasoning), DP (Data Analysis & Probability); HS adds F (Functions),
  T (Trigonometry), C (Calculus), LT (Logic & Theory).
- **Practices:** 7 Mathematical Thinking & Reasoning standards `MA.K12.MTR.1.1` … `MA.K12.MTR.7.1`.

**ELA (B.E.S.T.)** — `ELA.<grade>.<strand>.<standard>.<benchmark>`
- e.g., `ELA.K.F.1.1` = Kindergarten · Foundations · standard 1 · benchmark 1.
- Strands: F (Foundations, K-5), R (Reading), C (Communication), V (Vocabulary).
- **Expectations:** 6 ELA Expectations `ELA.K12.EE.1.1` … `ELA.K12.EE.6.1`.

**Science (NGSSS)** — `SC.<grade>.<body of knowledge>.<standard>.<benchmark>`
- e.g., `SC.K.L.14.1` (Life Science). Bodies: N (Nature of Science), L (Life), P (Physical),
  E (Earth/Space).

**Computer Science** — `SC.<grade>.CS-*` content + 6 Computational Thinking & Reasoning practices
`SC.K12.CTR.1.1` … `SC.K12.CTR.6.1`. *Update:* Florida is establishing a **standalone Computer
Science** framework (separating CS from Science, 2025+) — verify current CS codes on CPALMS before citing.

**English Language Development (ELD)** — `ELD.K12.ELL.<area>.<n>`, areas: LA, MA, SC, SS, SI
(language of Language Arts, Math, Science, Social Studies, and Social/Instructional). WIDA-aligned.

**Social Studies** — `SS.<grade>.<strand>.*` (per `SocialStudies_StandardsandAccessPoints`; confirm
benchmarks on CPALMS).

## Full enumerated standards (queryable) — `resources/florida/data/`
Every Florida standard + access point is extracted from the official documents into JSON by
`tools/parse_fl_standards.py`, so skills can look up exact codes and statements:

| Subject | Codes | Benchmarks | Access points |
|---|---|---|---|
| Math (B.E.S.T.) | 1,127 | 635 | 485 (+7 MTR) |
| ELA (B.E.S.T.) | 719 | 329 | 384 (+6 EE) |
| Science (NGSSS) | 1,450 | 498 | 952 |
| Computer Science | 569 | 562 | — (+7 CTR) |
| Social Studies | 2,713 | 1,432 | 1,281 |
| ELD | 5 | — | — |
| **Total** | **6,583** | | |

Query: `python3 tools/fl_lookup.py --subject math --grade 3 --search fraction`. **Always verify on
CPALMS** before citing. Social Studies is best-effort from a legacy `.doc` — verify there. Re-extract
after a refresh with `tools/parse_fl_standards.py`.

## Access points (Special Education) — important
Florida publishes **Access Points** for students with significant cognitive disabilities, embedded in
the same documents:
- B.E.S.T. (Math/ELA): `…​.AP.<n>` (e.g., `MA.K.NSO.1.AP.1`, `ELA.K.F.1.AP.1a`).
- NGSSS (Science): `.In.` (Independent), `.Su.` (Supported), `.Pa.` (Participatory) — e.g.,
  `SC.K.L.14.In.1`.
These are the canonical hooks `special-education-support` should reference for FL alignment.

## Grade → band mapping
K, 1, 2 → **K-2** · 3, 4, 5 → **3-5** · 6, 7, 8 → **6-8** · 9-12 → **9-12** (HS math by course = `912`).

## Florida assessment program (2026–27) — for `assessment-designer`
- **FAST** (Florida Assessment of Student Thinking) — progress monitoring **3×/year** (PM1/PM2/PM3):
  ELA Reading VPK–grade 10, Mathematics VPK–grade 8.
- **B.E.S.T. EOC** — Algebra 1, Geometry; **B.E.S.T. Writing** grades 4–10.
- **EOC** — Algebra 1, Geometry, Biology 1, Civics, U.S. History.
- **FCLE** — Florida Civic Literacy Exam. **ACCESS for ELLs** (WIDA) for English learners.
- 2026–27 schedule: `https://www.fldoe.org/file/5663/2627StatewideAssessmentSched.pdf` (in the corpus).
- Align items to the cited standard; use the B.E.S.T. writing rubrics + ALDs in `resources/florida/`.

## Verification & provenance
- Verify every cited FL code on **CPALMS** (live). Record `standards_set` (e.g., `FL-BEST-Math`) +
  the code in artifact metadata.
- Stored corpus + per-file sources: `resources/florida/` (+ `sources.json`); catalog
  `resources/florida-2025-26.md`; refresh with `tools/standards_refresh.py`.
- **Currency monitoring:** the `standards-updater` skill watches **all Florida change vectors** —
  standards, courses/curriculum (CTE), pacing/guidance (TAPs, memos), instructional materials,
  assessment, graduation, **legislation** (Statutes Title XLVIII), and **State Board rules** (FAC 6A).
  See `sources.json` (`coverage` / `crawl_seeds` / `watch_pages`).
