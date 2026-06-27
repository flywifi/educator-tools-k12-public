# rubric.md
## Quality Gates — 0-5 dimension descriptors
Scoring detail for `quality-review` (from `protocols/quality-gates.md` §§24-31). Weights in
parentheses. General scale: 0 critical failure · 1 major · 2 significant · 3 acceptable · 4 strong ·
5 exemplary. Score each dimension with **evidence quoted from the artifact**.

---

### 1. Integrity (25%) — highest priority
Honest, transparent, no fabrication; assumptions and uncertainty disclosed.
- **5** no concerns; fully transparent. **4** minor doc gaps. **3** correctable weaknesses.
  **2** needs remediation. **1** serious concerns. **0** fabrication (citation/standard/result) —
  **automatic Rejected**.

### 2. Safety (2%)
No harm; **no real student PII** (placeholders only); no unsafe or legal-overreach guidance.
- **0** real PII, unsafe content, or a legal/eligibility determination presented as final →
  **automatic Rejected**. Higher scores = appropriate boundaries + human-review notes present.

### 3. Governance (10%)
Protocols followed; metadata complete; decision recorded; standards cited with framework+version.
- **5** fully compliant. **3** acceptable with gaps. **0** approval without evidence / falsified
  records → critical.

### 4. Accuracy (20%)
Facts, calculations, and **standards** correct, current, correctly coded, and verifiable.
- **5** no known inaccuracies. **3** minor, correctable. **2** significant. **0** incorrect/fabricated
  standard or fabricated statistic → critical.

### 5. Alignment (15%)
Objectives ↔ instruction ↔ assessment ↔ standards cohere.
- **5** complete alignment. **3** acceptable. **2** significant gaps. **0** assessment measures
  something other than the objective.

### 6. Educational Quality (15%)
Instructionally effective: clear measurable objectives, sound design, differentiation, appropriate
cognitive load, meaningful checks for understanding.
- **5** highly effective. **3** acceptable. **2** weak. **0** instructional-design failure.

### 7. Accessibility (3%)
Readable, usable, audience-appropriate; UDL applied; reading level matches the band.
- **5** no barriers. **3** acceptable. **2** significant barriers. **0** unusable for the audience.

### 8. Professional Quality (3%)
Organized, clear, consistent formatting.
- **5** exceptional. **3** acceptable. **1** major problems. **0** unusable presentation.

### 9. User Intent (7%)
The requested deliverable, scope, audience, and constraints were met.
- **5** fully satisfies. **3** generally. **2** meaningful gaps. **0** wrong deliverable produced.

---

## Composite & decision
`Composite = Σ(score × weight)` → Approved ≥4.0 · Conditionally Approved 3.0-3.99 · Remediation
Required 2.0-2.99 · Rejected <2.0. **Any 0, or a critical failure, forces Rejected.** Use
`scripts/score.py` to compute — do not eyeball the arithmetic.
