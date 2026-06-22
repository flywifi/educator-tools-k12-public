# ngss.md
## NGSS Adapter — Next Generation Science Standards
Framework: `NGSS` · Version: 2013 · Coverage: K–12.
Adapter for `standards-framework.md`. Phase 0 ships the coding scheme + three-dimensional structure
+ representative anchors; full enumeration is a later data task.

---

## 1. Coding scheme (Performance Expectations)

`<grade or band>-<disciplinary core idea>-<number>` e.g., `3-LS1-1`, `MS-PS1-4`, `HS-ESS1-6`.
- **Grade prefixes:** `K`, `1`–`5` (grade-specific); `MS` (middle, 6–8); `HS` (high, 9–12).
- **DCI letters:** `PS` Physical Science · `LS` Life Science · `ESS` Earth & Space Science ·
  `ETS` Engineering, Technology & Applications of Science.

## 2. Three dimensions (every PE braids all three)

- **SEPs** — Science & Engineering Practices (e.g., "Developing and Using Models").
- **DCIs** — Disciplinary Core Ideas (the PS/LS/ESS/ETS content).
- **CCCs** — Crosscutting Concepts (e.g., Patterns; Cause and Effect; Systems).

Skills aligning to NGSS should reflect all three dimensions, not just the content (this is a common
alignment-gate failure, QG §26).

## 3. Grade/band → TOS band mapping

K,1–5 → **K-2 / 3-5** (by grade) · `MS` → **6-8** · `HS` → **9-12**.

## 4. Representative anchors (examples; not exhaustive)

| Code | Band | Performance Expectation (abridged) |
|---|---|---|
| `K-PS2-1` | K-2 | Plan/conduct an investigation comparing effects of pushes and pulls. |
| `3-LS1-1` | 3-5 | Develop models to describe organisms' unique and diverse life cycles. |
| `5-ESS2-1` | 3-5 | Develop a model of interactions among Earth's spheres. |
| `MS-PS1-4` | 6-8 | Develop a model predicting effects of thermal energy on particle motion. |
| `MS-LS2-3` | 6-8 | Develop a model of matter/energy flow in an ecosystem. |
| `HS-ESS1-6` | 9-12 | Apply scientific evidence to construct an account of Earth's history. |
| `HS-LS2-2` | 9-12 | Use mathematical reasoning about factors affecting biodiversity/populations. |

## 5. Verification notes

Validate the **grade/band prefix + DCI letters + number**; record `version: 2013`. Many states adopt
NGSS-derived but renamed standards — when a state is named, prefer `state-standards-model.md`.
