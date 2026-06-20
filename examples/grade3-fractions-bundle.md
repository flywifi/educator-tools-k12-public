# Teaching Bundle — Grade 3 Fractions (worked orchestration)

> A `teacher-core` **teaching bundle**: one request → several aligned artifacts, one shared standard,
> each gated by `quality-review`. Demonstrates `skills/teacher-core/references/workflows.md`.

**Request (simulated):** "Set me up to teach unit fractions to my 3rd graders tomorrow — a hands-on
lesson, a quick way to grade their explanations, slides, and a note home."

**Shared context (flows to every piece):** Classroom Teacher · Grade 3 (band 3-5) · Mathematics ·
standard `CCSS.MATH.CONTENT.3.NF.A.1` (CCSS-Math 2010) · placeholders only.

## Bundle contents (each gated separately)
| # | Artifact | Skill | Source example | Decision |
|---|---|---|---|---|
| 1 | Lesson plan (hands-on, 45 min) | `lesson-planner` | `skills/lesson-planner/examples/grade3-fractions-lesson.md` | Approved 4.34 |
| 2 | Rubric for explaining 1/b | `assessment-designer` | `skills/assessment-designer/examples/grade3-fractions-rubric.md` | Approved |
| 3 | Slide deck (7 slides) | `presentation-builder` | `skills/presentation-builder/examples/grade3-fractions-slides.md` | Approved |
| 4 | Parent note (below) | `family-communication` | new | Approved |

## Piece 4 — Parent note (plain language, placeholders)
> Hello families — this week in math we're learning **fractions**: how to split a whole into **equal
> parts** and name one part (like 1/4). Ask your child at home: *"If we cut this into 4 equal pieces,
> what is one piece called?"* Thanks for learning with us! Questions? [teacher contact].

## Orchestration notes
- **Consistency:** all four pieces use the *same* verified standard, grade band, and "equal parts"
  vocabulary — the rubric scores exactly what the lesson teaches, the slides present it, the note
  echoes it for home.
- **Order:** lesson first (sets the objective), then rubric + slides built from it, then the note.
- **Gating:** each piece passed `quality-review` independently; the bundle is assembled only after.

## Bundle metadata
```yaml
artifact_type: teaching-bundle
persona: Classroom Teacher
grade_band: "3-5"
subject: Mathematics
standards_set: "CCSS-Math 2010"
standards_cited: ["CCSS.MATH.CONTENT.3.NF.A.1"]
pieces: [lesson-plan, rubric, slide-deck, parent-note]
decisions: "all Approved (see per-piece records + ledger entries qr-2026-0001..0003)"
human_review_required: true
```
