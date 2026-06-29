# florida-2025-26.md
## Florida resource catalog — 2025–26 snapshot
Index of the canonical Florida standards & assessment resources provided for this ecosystem, grouped
by type. Pairs with the adapter `../florida-best.md`.

> **Current for 2026–2027 (verified June 2026).** The **standards** (B.E.S.T. Math/ELA, NGSSS
> Science/SS) are unchanged since adoption and remain current. The **2026–27 assessment schedule**
> (`2627StatewideAssessmentSched.pdf`) is included; most other assessment fact-sheets here are the
> 2025–26 cycle, and the live FLDOE pages carry the 2026–27 versions — run `tools/standards_refresh.py`
> to pull the latest.

> **Snapshot vs. live.** This catalogs a **2025–26 snapshot** (104 documents). The **current**
> versions live at the official sources below — always prefer them when standards/assessments change:
> - **Standards (all subjects):** CPALMS — `www.cpalms.org` (search by code or subject/grade).
> - **Assessment (FAST/B.E.S.T./EOC/FCLE): fact sheets, ALDs, test design, reference sheets,
>   accommodations:** FLDOE — `www.fldoe.org` (Accountability → Assessments).
> - **English learners (ELD/ACCESS):** WIDA — `wida.wisc.edu`; FLDOE ESOL pages.
>
> **Stored + refreshable.** The raw files are stored under `florida/` (by category) with
> `florida/sources.json` recording each file's **sha256 + official source**. Run
> `tools/standards_refresh.py --crawl` to crawl the canonical sources for newer documents (compares
> against the stored hashes), then drop in updates, refresh `sources.json`, bump this date, and
> re-verify any cited codes on CPALMS.

---

## 1. Standards & access points (the canonical content)
| Subject | Files |
|---|---|
| Math (B.E.S.T.) | `mathbeststandardsfinal.pdf`, `Mathematics(B.E.S.T.)_StandardsandAccessPoints.doc(.docx)`, `MTR-ClassroomCoachTool.pdf` |
| ELA (B.E.S.T.) | `bestela202511.pdf`, `EnglishLanguageArts(B.E.S.T.)_StandardsandAccessPoints.doc(.docx)` |
| Science (NGSSS) | `Science_StandardsandAccessPoints.doc(.docx)`, `sciencegrade5-Nov2018.pdf`, `sciencegrade8-Nov2018.pdf` |
| Social Studies | `ss202511.pdf`, `SocialStudies_StandardsandAccessPoints_WR.doc` |
| Computer Science | `csstandards202407.pdf`, `ComputerScience_StandardsReportWithoutAccessPoints.doc(.docx)` |
| English Lang. Development | `EnglishLanguageDevelopment_StandardsReportWithoutAccessPoints.doc(.docx)` |
| Gifted / Health / PE | `Gifted_StandardsReportWithoutAccessPoints.doc(.docx)`, `health2023.pdf`, `pe2014.pdf` |

**Access points** (Special Education) are embedded in the Math/ELA/Science StandardsandAccessPoints
documents — see `../florida-best.md` for the coding (`.AP.` / `.In./.Su./.Pa.`).

**Enumerated + queryable:** all standards above are extracted to JSON in `florida/data/` (**6,583
codes** across Math/ELA/Science/CS/SS/ELD) — query with `tools/fl_lookup.py`, re-extract with
`tools/parse_fl_standards.py`.

## 2. Assessment specs → used by `assessment-designer`
- **Achievement Level Descriptors (ALDs):** `AchieveLevelDesc.pdf`, `NGSSSAchievementLevels.pdf`,
  `CivicsALDs.pdf`, `USHistoryALDs.pdf`, `aldsbioeoca.pdf` — what each score level means.
- **Reporting Category Summaries (rcs):** `best-ela-rcs.pdf`, `best-math-rcs.pdf`,
  `Grade5/Grade8-Science-rcs.pdf`, `BIology-rcs.pdf`, `Civics-rcs.pdf`, `USHistory-rcs.pdf`.
- **Test Item Specifications (TIS) / Test Design (TDS):** `CivicsEOCTIS.pdf`, `SCIGR5TIS.pdf`,
  `SCIGR8TSI.pdf`, `SCIBIO1EOCTSI.pdf`; `TDS-FAST-ELA.pdf`, `TDS-FAST-Math.pdf`, `Science-TDS.pdf`,
  `SocialStudies-TDS.pdf`.
- **Cognitive complexity:** `cognitivecomplexity.pdf` — use for the cognitive-balance check.
- **Fact sheets:** `2526BESTEOCFactSheet.pdf`, `2526BESTWritingFactSheet.pdf`, `2526FASTGrd310FS.pdf`,
  `2526FASTK2FS.pdf`, `2526Gr5-8ScienceFactSheet.pdf`, `2526SciSSEOCFactSheet.pdf`, `2526K12FCLEFactSheet.pdf`.
- **Math reference sheets / calculator policy:** `FL_2025-26_FAST-BEST-Mathematics-Reference-Sheets-Packet_Final_508.pdf`,
  `FSACalcRefSheetPolicy.pdf`, `FLMathFormuSuccess.pdf`.

## 3. Writing rubrics & anchor sets → `assessment-designer`, `lesson-planner`
- **Rubrics:** `4-6BESTWritingArgumentationRubric.pdf`, `4-6BESTWritingExpositoryRubric.pdf`,
  `7-10BESTWritingArgumentationRubric.pdf`, `7-10BESTWritingExpositoryRubric.pdf`.
- **Scored anchor sets (exemplars):** `Spring-2025-Grade-{4,6,7,8,9,10}-B.E.S.T.-Writing-Anchor-Set_508_FINAL.pdf`.

## 4. Accommodations & accessibility → `special-education-support`
- `2025-2026_Sp-Su_FL_Accomm_Guide_FINAL_012326_508.pdf` (the accommodations guide),
  `2025-2026 K-2 Progress Monitoring Accommodations Guide_508.pdf`,
  accommodated scripts (`FL_SPSU26_PBT_…`, `SpSu26_FL_CBT_…`), `Alt-Interpretive-Guide.pdf`.

## 5. English learners → `english-learners` / `family-communication`
- `Florida-WIDA-ACCESS-Online-FAQ.pdf`, `ACCESS-Parent-Handout-English.pdf`, `2021WIDATestSessionForms.xlsx`.

## 6. Civic Literacy (FCLE) → `assessment-designer`, `lesson-planner`
- `2526K12FCLEFactSheet.pdf`, `Florida-Civic-Literacy-Exam-K12-FAQ.pdf`, `CivicLiteracyRule-faq.pdf`,
  `FCLESampleItem.pdf`, `SuppGuideFCLE.pdf`.

## 7. Test administration & logistics (reference; not for content generation)
Interpretive guides, TA/TIDE/REI user guides, `K12SAG.pdf`, assessment schedules, coordinator/
administrator checklists, agreements, graduation requirements, comp-adaptive-test FAQs.

---

*Full snapshot = 104 files. Items above name the high-value canonical resources; logistics/admin
files round out the set. When in doubt about currency, go to CPALMS/FLDOE.*
