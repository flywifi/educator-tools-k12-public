# quality-gates.md
## Quality Gates — Operational Rubric (skill self-check)
Canonical source. **Synced** into each skill's `references/quality-gates.md`
(see `tools/sync_manifest.json`) — do not edit per-skill copies; edit here and run
`tools/sync_check.py`. The full spec is `protocols/quality-gates.md`; `quality-review` is the
authoritative executor. Every skill self-checks against this before handoff (defense in depth).

---

## The 9 dimensions, scored 0–5, in gate order

Evaluate in this order; **stop early on a critical failure**:

1. **Integrity** (25%) — honest, transparent, no fabrication; assumptions disclosed.
2. **Safety** (2%) — no harm, no real student PII, no unsafe/legal overreach.
3. **Governance** (10%) — protocols followed; metadata complete; decision recorded.
4. **Accuracy** (20%) — facts, calculations, and **standards** correct and verifiable (per the
   context's standards applicability).
5. **Alignment** (15%) — objectives ↔ instruction ↔ assessment ↔ **the applicable standards** cohere
   (context-conditional; see below).
6. **Educational Quality** (15%) — instructionally effective; differentiated; right cognitive load.
7. **Accessibility** (3%) — readable, usable, audience-appropriate; UDL applied.
8. **Professional Quality** (3%) — organized, clear, consistent formatting.
9. **User Intent** (7%) — the requested deliverable, scope, and constraints were met.

0 = critical failure · 1 major · 2 significant · 3 acceptable · 4 strong · 5 exemplary.

### Context-conditional scoring (school type)
Read `standards_applicability` from the context (`shared/context/`) before scoring Accuracy/Alignment:
- **best_ngsss_apply** (public/charter/district-virtual/FLVS) — score against verified FL B.E.S.T./NGSSS codes.
- **school_defined** (private) — score against the school's framework (`shared/standards/frameworks/`);
  an optional FL crosswalk is a plus, not a requirement.
- **parent_selected** (home education) — standards are advisory: score Alignment as
  objective ↔ instruction ↔ assessment coherence; **not citing state codes is NOT a deduction or a
  critical failure**. (Offering optional alignment is a plus.)

Fabricating a code/standard/citation is **always** a critical failure, in every context. The point is:
*absence* of a mandated framework where none applies is correct; *invented* codes never are.

## Composite & decision

`Composite = Σ(score × weight)`.

| Composite | Decision |
|---|---|
| ≥ 4.0 | Approved |
| 3.0–3.99 | Conditionally Approved (minor remediation) |
| 2.0–2.99 | Remediation Required |
| < 2.0 | Rejected |

## Critical failures → Rejected regardless of composite (never override)
Fabricated citation/standard/source/result · real student PII · unsafe or legal-overreach output ·
"approval" without evidence. (Full list: `protocols/quality-gates.md` §6.)

## On not-Approved
- Resolve contradictions with `protocols/conflict-protocol.md` (integrity > safety > governance >
  accuracy/alignment > preference > presentation).
- Recover/degrade honestly with `protocols/failure-recovery.md` — never fabricate to "pass."

## Emit a decision record
Record the outcome in the artifact's metadata block (`protocols/metadata-schema.md`): per-dimension
scores, composite, decision, evidence, rationale, and `human_review_required: true`.

> Reminder: an artifact is decision support, not a final professional/legal determination.
