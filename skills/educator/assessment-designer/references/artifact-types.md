# artifact-types.md
## Artifacts produced by assessment-designer

Every assessment maps each item to a cited+verified standard and ships with a key/scoring guide and
the metadata block.

### Formative assessment
- **Purpose:** quick, low-stakes check during instruction.
- **Required elements:** 1-5 items on one objective; answer key; a data-use/reteach note.

### Summative assessment
- **Purpose:** measure learning at the end of a unit.
- **Required elements:** items across the unit's standards; a blueprint mapping items → standards →
  cognitive level (DOK/Bloom); answer key + point values; accessibility + accommodation notes.

### Rubric
- **Purpose:** criteria-based scoring of complex work.
- **Required elements:** observable criteria; 3-5 performance levels with descriptors; aligned to the
  objective/standard; student-friendly language option.
- **Template:** `assets/templates/rubric-template.md`.

### Performance task
- **Purpose:** applied, transfer-level demonstration.
- **Required elements:** authentic prompt + context; standards; success criteria (paired rubric);
  scoring guidance.

### Item bank
- **Purpose:** a reusable pool of aligned items.
- **Required elements:** items tagged by standard, cognitive level, and difficulty; answer keys.

## Validation (extends `shared/quality/verification-checklists.md`)
- Each item **measures the stated objective/standard** (not just the topic).
- An answer key or scoring guide is present and correct.
- Cognitive levels are balanced (not all recall); no trick/biased items.
- Rubric criteria are observable and leveled; reading level matches the band.

## General assessment templates
- `assets/templates/assessment-template.md` (quiz/test) · `assets/templates/rubric-template.md`.
