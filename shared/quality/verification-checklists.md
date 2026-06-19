# verification-checklists.md
## Verification Checklists
Canonical source. **Validation** (pipeline step 4) is the minimum-correctness pass *before* the
Quality Gates (QG §7.3) — "did we build the thing, completely and consistently?" The gates then ask
"did we build it well?". Capability skills extend these with artifact-specific checks in their own
`references/artifact-types.md`.

---

## Universal validation checklist (every artifact)
- [ ] The requested **deliverable type** is what was produced (no swap — QG §14.4).
- [ ] **Grade band + subject** are set and consistent throughout.
- [ ] At least one **standard** is selected, cited with framework+version, and verifiable
      (`protocols/standards-verification.md`).
- [ ] **Differentiation** is present (UDL by default; tiering/EL/IEP as applicable).
- [ ] **Metadata block** is initialized and `human_review_required: true`.
- [ ] **No real student data** anywhere (placeholders only).
- [ ] **No fabricated** facts, citations, or standards.
- [ ] Internally consistent (objectives match activities match assessment).

## Artifact-family spot checks
- **Lesson/Unit:** objective(s) measurable; activities support the objective; an assessment/check
  for understanding exists; timing is plausible.
- **Assessment/Rubric:** items measure the stated objective/standard; answer key or scoring guide
  present; rubric criteria are observable and leveled.
- **Slide deck / presentation:** one idea per slide; readable contrast/size; speaker support where
  relevant.
- **SpEd / Intervention:** ties to a (placeholder) plan; accommodation vs. modification labeled;
  human-review and legal-boundary notes present.

## Outcome
A passed validation feeds the gates. A failed validation routes to
`protocols/failure-recovery.md` (degrade honestly; never fabricate to fill a gap).
