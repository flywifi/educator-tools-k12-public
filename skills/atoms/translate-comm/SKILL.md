---
name: translate-comm
description: "Render a family communication into a target home language with advisory flags. Use this atom when family-communication or parent-comm needs to provide a translation of a school message. ADVISORY ONLY — always flag that a fluent speaker should review. Do NOT use for certified translation of legal documents."
---

# translate-comm

Translates a school communication (email, note, announcement) into a target language. Always advisory — flags that a fluent speaker or certified translator must review before sending. Never used for legal/IEP documents.

## Input

```json
{
  "text": "Dear families, our school will host a Math Night on Thursday from 6-7 PM. Please join us for activities and refreshments!",
  "source_language": "en",
  "target_language": "es",
  "formality": "warm"
}
```

## Output

```json
{
  "tool": "translate-comm",
  "translated_text": "Estimadas familias, nuestra escuela organizará una Noche de Matemáticas el jueves de 6 a 7 PM. ¡Les invitamos a unirse para actividades y refrigerios!",
  "source_language": "en",
  "target_language": "es",
  "advisory": "This is a machine-assisted translation. A fluent Spanish speaker should review before distribution.",
  "human_review_required": true
}
```

## Do NOT use this atom for
- Certified translation of legal documents (IEPs, 504 plans, due process)
- Replacing a qualified interpreter for parent conferences
- Translation without the advisory flag

## Pipeline note
Follows `references/method.md` at the Generation step (translation). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — ALL translations must be reviewed by a fluent speaker before distribution to families.
