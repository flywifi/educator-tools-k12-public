# florida-best.md
## Florida Standards Adapter — B.E.S.T. + NGSSS (populated state set)
Canonical source for the Standards Engine (`standards-framework.md`). Florida is the first fully
populated state via the pattern in `state-standards-model.md`.

> **Staying current (read this first).** These coding schemes are stable, but the *content* changes.
> The **live canonical authority for Florida standards is CPALMS — `www.cpalms.org`** (the official
> FLDOE standards repository), with assessment materials at **`www.fldoe.org`** and EL/WIDA at
> **`wida.wisc.edu`**. The files indexed in `resources/florida-2025-26.md` are a **dated 2025–26
> snapshot**; when verifying a standard or pulling the newest rubric/fact sheet, prefer CPALMS/FLDOE
> over the snapshot. Never invent a code — confirm it on CPALMS (`protocols/standards-verification.md`).

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

## Coding schemes (verified against the official 2025–26 documents)

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
`SC.K12.CTR.1.1` … `SC.K12.CTR.6.1`.

**English Language Development (ELD)** — `ELD.K12.ELL.<area>.<n>`, areas: LA, MA, SC, SS, SI
(language of Language Arts, Math, Science, Social Studies, and Social/Instructional). WIDA-aligned.

**Social Studies** — `SS.<grade>.<strand>.*` (per `SocialStudies_StandardsandAccessPoints`; confirm
benchmarks on CPALMS).

## Access points (Special Education) — important
Florida publishes **Access Points** for students with significant cognitive disabilities, embedded in
the same documents:
- B.E.S.T. (Math/ELA): `…​.AP.<n>` (e.g., `MA.K.NSO.1.AP.1`, `ELA.K.F.1.AP.1a`).
- NGSSS (Science): `.In.` (Independent), `.Su.` (Supported), `.Pa.` (Participatory) — e.g.,
  `SC.K.L.14.In.1`.
These are the canonical hooks `special-education-support` should reference for FL alignment.

## Grade → band mapping
K, 1, 2 → **K-2** · 3, 4, 5 → **3-5** · 6, 7, 8 → **6-8** · 9-12 → **9-12** (HS math by course = `912`).

## Verification & provenance
- Verify every cited FL code on **CPALMS** (live). Record `standards_set` (e.g., `FL-BEST-Math`) +
  the code in artifact metadata.
- Snapshot provenance + assessment/rubric/accommodation resources: `resources/florida-2025-26.md`.
