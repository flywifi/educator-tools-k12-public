# artifact-types.md
## Artifacts produced by presentation-builder

The skill first produces a **slide outline** (content + structure), then renders a **.pptx** via the
`pptx` skill. Both carry the metadata block.

### Instructional slide deck (primary)
- **Purpose:** present a lesson's content for whole-class or small-group instruction.
- **Required elements:** a title slide; an objective slide (the cited standard's goal in student
  language); a gradual-release flow (hook → model → guided → independent → closing) with **one idea
  per slide**; visuals/models; embedded checks for understanding; a closing/recap slide.
- **Render with:** a `.pptx` rendering skill (e.g., a `pptx` skill, if one is available in the host environment).

### Review / warm-up deck
- **Purpose:** activate prior knowledge or review before an assessment.
- **Required elements:** short item-per-slide prompts with reveal-answer slides; aligned to the
  target standards.

### Family / staff briefing deck
- **Purpose:** communicate to parents or colleagues (e.g., curriculum night, PD).
- **Required elements:** plain-language slides; no jargon (or defined); no real student data.

## Validation (extends `shared/quality/verification-checklists.md`)
- One idea per slide; readable text size and contrast; visuals support (not decorate) the point.
- Objective + at least one check for understanding present; aligned to a real cited standard.
- Reading level matches the band; alt text provided for images (accessibility).
