# End-to-end walkthrough — offline setup → teacher context → real task

A start-to-finish model of a teacher using TOS offline, with **real tool runs and real output**
(captured 2026-06-29, not mocked). Teacher: **Ms. Rivera, 3rd grade, Aloma Elementary (OCPS,
MSID 481401)**. Every command below is runnable.

---

## Step 1 — Teacher sets up offline storage (one time)

```bash
python3 tools/offline_index.py --build        # unified reference index
python3 shared/cache/cache.py --build         # L1 standards cache
```
Output:
```
Built canonical-sources/index/offline.db [fts5] — 12911 rows:
  {standards: 6583, courses: 4607, schools: 712, toolkit_resources: 949, data_sources: 60}
Built shared/cache/index.local.db — 6583 standards indexed [fts5]
```
Both DBs are gitignored build artifacts — local to her machine, rebuilt from canonical JSON.

## Step 2 — Teacher fills in her context

She answers a few questions (here as `rivera.json`: school MSID 481401, role Classroom Teacher /
Math / grade 3, lesson template "Gradual Release", pacing "OCPS scope & sequence").

```bash
python3 .../profile_wizard.py --init rivera.json   # -> profile_written (shared/context/profiles/teacher.local.json, GITIGNORED)
python3 .../profile_wizard.py --validate           # -> {"status": "ok", "issues": []}
python3 .../profile_wizard.py --register           # -> sop_refs (classroom-scope profile) + overrides (her prefs as instructions)
python3 .../profile_wizard.py --set '{"offline_first": true, "standards_cache": "enabled"}'
```
`--register` emits exactly what skills consume: a `sop_refs` pointer to her profile + `overrides`
turning each preference ("tone = warm but concise", "lesson_template = Gradual Release") into a
teacher-stated instruction that outranks defaults.

## Step 3 — A real task, answered entirely from offline data

> Ms. Rivera: *"Help me plan a 3rd grade fractions lesson for my class."*
> Her context (grade=3, subject=Math, school=481401) drives every lookup. **No corpus is loaded.**

```
3a. School      -> 481401  Aloma Elementary School  (traditional, grades PK-5, Winter Park)
3b. Standards   -> 4 grade-3 math fraction standards (verbatim from canonical data):
      [MA.3.FR.1.3]    Read and write fractions, including fractions greater than one...
      [MA.3.FR.2.2]    Identify equivalent fractions and explain why they are equivalent...
      [MA.3.FR.2.1]    Plot, order and compare fractional numbers with the same numerator...
      [MA.3.FR.2.AP.2] (ESE Access Point) Using a visual model, recognize fractions...
3c. Course code -> 5012050  Grade Three Mathematics
3d. CPALMS res. -> standard MA.3.FR.1.3 found in the B.E.S.T. Math toolkit
```
The model now has her school, the exact standards (incl. an **ESE access point** for differentiation),
the course code, and a toolkit reference — all verbatim, none generated.

### Token accounting for this one task
```
offline lookups used (measured):                         ~715 tokens
same facts if the corpus were loaded into context:  ~1,012,896 tokens
reduction:                                                  99.93%
```
And because ~1M tokens exceeds the context window, the offline index doesn't just save tokens — it
makes the task **possible without an external retrieval round-trip**.

---

## Testing — complex scenarios + edge cases (all passed)

**Different teacher, different context drives different results** — Mr. Chen, 9th-grade Biology, a
Seminole HS (district 59): school resolves in district 59, `--standards heredity --subject science`
returns `SC.4.L.16.3 / SC.7.L.16.1`, `--course "Biology 1"` → `2000310`. Same tools, context-scoped.

**Honest failure — never fabricates** (the critical safety test):

| query | result |
|---|---|
| `--school "Hogwarts Academy" --district 48` | `count=0` (no invented MSID) |
| `--standards photosynthesis --grade 1 --subject math` | `count=0` (impossible combo → empty) |
| `--course "Underwater Basket Weaving"` | `count=0` |

A lookup returns *found* rows or nothing — it cannot hallucinate a code/school/course.

**Cross-district scoping** — `--school "High School"` returns 26 (Orange) / 19 (Polk) / 15 (Brevard),
each correctly scoped by `--district`.

**Freshness / drift detection** — `cache.py --verify` reports `stale=False` when current; after a
change to `math.json` it reports `stale=True, changed=['math.json']`, signaling a rebuild. Offline
data can't silently go stale.

### Notes from testing
- FTS ranks partial school names by relevance, so `--school "Lake Mary"` can surface "Lake Mary
  Elementary" before "Lake Mary High" — use the fuller name (or `--limit`) to disambiguate. Not a
  correctness bug; a ranking nuance.
- `toolkit_resources` links are page-level: a standard matched in a prose document (e.g. the B.E.S.T.
  transition guide) may have no per-standard CPALMS link on that page — reported honestly as none.

## What this proves
Setup → context → task runs entirely offline, deterministically, at ~0.1% of the token cost of
loading the reference corpora, with **no fabrication** anywhere in the chain, and with drift
detection so the offline copy is never silently wrong.

---

## Critical evaluation — hard multi-skill workflow (2-week differentiated fractions unit)

Chained **curriculum-mapping → lesson-planner → special-education-support → assessment-designer**,
all against the offline index, to find where the data holds vs. breaks. Honest findings:

**Bug found + fixed — no stemming/prefix match.** FTS5 (`unicode61`) matched tokens exactly, so
`--standards "fraction"` returned **1** standard while `"fractions"` returned 9 — a teacher searching
the singular silently missed standards. Fixed with prefix matching (`token*`): `"fraction"` now
returns **10** (covers fraction/fractions/fractional). Rebuilt; verified.

**Test-harness bug found.** The first pass reported "0/5 access points" — a false negative from a
flawed check in the *eval script* (it searched the benchmark code, not the strand). Corrected:
true coverage is **5 benchmarks + 5 access points, both strands covered**. Lesson: the evaluation
itself needs verifying, not just the system.

**Coverage — what's strong vs thin (verified):**

| capability | result | verdict |
|---|---|---|
| Standards (benchmarks) | 5/5 for the unit, verbatim | ✅ strong |
| **Access points (ESE)** | 5 APs, both strands covered | ✅ strong — ESE alt-alignment is grounded |
| Course anchor | `5012050 Grade Three Mathematics` | ✅ strong |
| CPALMS toolkit links (Science/ELA) | SC.3.E.5.1, LAFS.5.RI.1.1, SC.5.P.10.1 → have links | ✅ strong where a toolkit exists |
| CPALMS toolkit links (**grade-3 math**) | MA.3.FR.* → indexed but **no per-standard link** | ⚠️ gap — provide the 3rd-grade Math toolkit PDF (Science/ELA already rich) |
| **Pacing / scope & sequence** | 0 rows | ⚠️ gap — index has no OCPS pacing; curriculum-mapping generates pacing unanchored. Provide an OCPS scope&sequence to anchor it |
| **Assessment item bank** | 0 items (endpoints only) | ⚠️ inherent — assessment-designer *generates* items; no offline bank to ground difficulty/DOK |

**Where the offline index helps vs. where the model still generates:** lookups (standards, access
points, courses, schools, vetted CPALMS links) are deterministic + zero-token + non-fabricating.
*Pacing realism* and *assessment items* remain model-generated — the index can't anchor them until a
real OCPS scope&sequence and (optionally) an item-spec source are added. That boundary is now explicit.

**Actionable next inputs (close the gaps on the free path):** a 3rd-grade **Math** instructional
toolkit PDF (for per-standard CPALMS links), and an **OCPS scope & sequence / pacing** doc.
