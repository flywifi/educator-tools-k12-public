# ccss.md
## CCSS Adapter — Common Core State Standards (ELA & Math)
Framework: `CCSS-ELA`, `CCSS-Math` · Version: 2010 · Coverage: K–12.
Adapter for `standards-framework.md`. Phase 0 ships the coding scheme + structure + representative
anchors; full enumeration is a later data task.

---

## 1. Coding scheme

**Math** — `CCSS.MATH.CONTENT.<grade>.<domain>.<cluster>.<standard>`
e.g., `CCSS.MATH.CONTENT.3.NF.A.1` = Grade 3, Number & Operations—Fractions, cluster A, std 1.
High-school math is organized by **conceptual category** instead of grade:
`CCSS.MATH.CONTENT.HSA.REI.B.3` (HS Algebra → Reasoning with Equations & Inequalities).
Also: **Standards for Mathematical Practice** `CCSS.MATH.PRACTICE.MP1`–`MP8` (K–12).

**ELA/Literacy** — `CCSS.ELA-LITERACY.<strand>.<grade>.<number>`
e.g., `CCSS.ELA-LITERACY.RL.5.1` = Reading: Literature, Grade 5, standard 1.
Strands: **RL** (Reading: Literature), **RI** (Reading: Informational), **RF** (Reading:
Foundational Skills, K–5), **W** (Writing), **SL** (Speaking & Listening), **L** (Language).
Bands 6–12 add literacy in **History/SS, Science & Technical Subjects** (RH, RST, WHST).

## 2. Grade → band mapping

K,1,2 → **K-2** · 3,4,5 → **3-5** · 6,7,8 → **6-8** · 9,10,11,12 → **9-12**
(CCSS often groups high school as 9-10 / 11-12; both roll up into 9-12.)

## 3. Math domains by band (anchors)

- **K-2:** Counting & Cardinality (K), Operations & Algebraic Thinking, Number & Operations in Base
  Ten, Measurement & Data, Geometry.
- **3-5:** OA, NBT, **Number & Operations—Fractions (NF)**, MD, Geometry.
- **6-8:** Ratios & Proportional Relationships (6–7), The Number System, Expressions & Equations,
  **Functions (8)**, Geometry, Statistics & Probability.
- **9-12 (categories):** Number & Quantity, Algebra, Functions, Modeling, Geometry, Statistics &
  Probability.

## 4. Representative anchors (examples; not exhaustive)

| Code | Band | Statement (abridged) |
|---|---|---|
| `CCSS.MATH.CONTENT.K.CC.A.1` | K-2 | Count to 100 by ones and tens. |
| `CCSS.MATH.CONTENT.3.NF.A.1` | 3-5 | Understand a fraction 1/b as one part of a whole partitioned into b parts. |
| `CCSS.MATH.CONTENT.6.RP.A.3` | 6-8 | Use ratio and rate reasoning to solve real-world problems. |
| `CCSS.MATH.CONTENT.HSA.REI.B.3` | 9-12 | Solve linear equations and inequalities in one variable. |
| `CCSS.ELA-LITERACY.RF.1.3` | K-2 | Know and apply grade-level phonics in decoding words. |
| `CCSS.ELA-LITERACY.RL.5.1` | 3-5 | Quote accurately from a text when explaining and drawing inferences. |
| `CCSS.ELA-LITERACY.W.8.1` | 6-8 | Write arguments to support claims with clear reasons and evidence. |
| `CCSS.ELA-LITERACY.RI.11-12.7` | 9-12 | Integrate and evaluate multiple sources of information. |

## 5. Verification notes

Validate the **strand/domain + grade + cluster** parts of a code against this structure; record
`version: 2010`. CCSS is widely adopted but **states adapt/rename it** — when a user names a state,
prefer the state set via `state-standards-model.md`.
