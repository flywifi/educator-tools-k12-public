# conflict-protocol.md
## Conflict Protocol
Version: 1.0 (reconstructed from the Quality Gates references; approved)
Derived from: QG §43 (gate conflict resolution + authority hierarchy), §41 (multi-gate
interaction), §38.5 (escalation conditions), §75 (escalation decision model).

> **Status note.** Reconstructed from the Quality Gates references and approved for use (v1.0).

---

## 1. Purpose

Conflicts are normal: a request may contradict a standard, two standards may pull different ways,
a persona's ask may collide with a constraint, or two quality gates may disagree. This protocol
gives a **deterministic way to resolve conflicts** so outcomes are consistent and auditable rather
than ad hoc.

## 2. The authority hierarchy (QG §43.3)

When two requirements conflict, the higher one wins:

```
integrity  >  safety  >  governance  >  accuracy/alignment  >  user preference  >  presentation
evidence   >  opinion
```

Concretely (QG §43.3): integrity > presentation · safety > convenience · governance > preference ·
evidence > opinion. Mirrors the gate execution order (QG §20.2).

## 3. Common conflict types & resolution

| Conflict | Resolution |
|---|---|
| User request vs. safety/legal (e.g., asks for real student data) | Safety/Integrity wins → refuse the unsafe part, offer a compliant alternative |
| User request vs. standard accuracy | Accuracy wins → cite the correct standard; explain the adjustment |
| Standard vs. standard (two plausible alignments) | Pick the best-aligned (Alignment gate), log the other as an assumption |
| Persona preference vs. governance requirement | Governance wins → comply, explain why |
| Presentation polish vs. integrity | Integrity wins (QG §43.2 — a polished but untrustworthy artifact is rejected) |
| Gate vs. gate (e.g., Professional PASS, Integrity FAIL) | Higher-priority gate prevails (Integrity) |

## 4. Procedure (QG §43.4)

1. Identify the conflict explicitly.
2. Review the evidence on each side.
3. Apply the authority hierarchy (§2) and the **canonical source-of-truth resolver** (§4a) when the
   conflict is between *sources* (which standard/rule/SOP governs).
4. If unresolved or high-stakes → **escalate** (do not silently pick a side).
5. Document the conflict and resolution in the artifact metadata `rationale` **and**, when sources
   disagreed, attach the decision record + minority report (§4a; `protocols/metadata-schema.md`).

## 4a. Canonical source-of-truth resolution + minority report

When the conflict is about **which source decides** (a standard, course rule, mandate, or operating
norm), resolve it through the canonical resolver so the path to the decision is auditable and the
losing-but-meaningful alternative is preserved — never buried in prose.

- **Source roles first.** `shared/context/source-roles.json` declares, per claim type, which sources are
  *allowed to prove it* and at what rank, and which sources must **not** (e.g., a recurring classroom
  practice never proves a compliance mandate). The resolver ranks candidates by source role, then by the
  context's `authority_precedence` scopes as a fallback.
- **One decision, with a minority report.** `shared/context/sot_resolver.py`
  (`resolve(claim, claim_type, candidates, context)`) emits a decision record
  (`shared/context/decision.schema.json`): `decision_log` (chosen interpretation + why it won),
  `conflicts`, `failed_to_merge` (canon vs current practice / provisional update — never blended), and
  `residual_uncertainty`. Policy: `shared/context/minority-report.md`.
- **Hard rules.** Fabrication is never a source (an invented code/citation is excluded and can never win
  — a critical failure under QG §37); canon is never silently rewritten; repeated practice is not
  promoted to doctrine just because it recurs; the meaningful alternative is kept when it would change
  downstream work.
- **A minority report is required** (not optional) whenever the disagreement changes which standard/rule
  applies, who is responsible, what scope is in force, or how a policy is read (full triggers in
  `minority-report.md`).

## 5. Escalation

Escalate to the user when the conflict involves IEP/504/eligibility, safety, legal determinations,
or anything needing real student data — consistent with assumptions-protocol.md §4 and QG
escalation levels (§74). The resolver sets `escalate: true` on these claim types
(`iep_504_requirement`, `eligibility_scholarship`, `graduation_promotion_requirement`,
`compliance_mandate`) whenever they are contested or low-confidence, so the hand-off to a human is
explicit in the decision record.

## 6. Validation

Phase A wires conflict handling into pipeline step 5 (Quality Gates) via `quality-review`, which
applies the hierarchy and records the resolution. Source-vs-source conflicts are resolved through
`shared/context/sot_resolver.py`, whose decision record (with minority report) is attached to the
artifact metadata (`protocols/metadata-schema.md`).
