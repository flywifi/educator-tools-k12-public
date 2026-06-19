# conflict-protocol.md
## Conflict Protocol
Version: 0.1 (DRAFTED from Quality Gates references — pending your review)
Derived from: QG §43 (gate conflict resolution + authority hierarchy), §41 (multi-gate
interaction), §38.5 (escalation conditions), §75 (escalation decision model).

> **Status note.** Listed as "complete" in QG §2.1 but not delivered. Faithful reconstruction.

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
3. Apply the authority hierarchy (§2).
4. If unresolved or high-stakes → **escalate** (do not silently pick a side).
5. Document the conflict and resolution in the artifact metadata `rationale`.

## 5. Escalation

Escalate to the user when the conflict involves IEP/504/eligibility, safety, legal determinations,
or anything needing real student data — consistent with assumptions-protocol.md §4 and QG
escalation levels (§74).

## 6. Validation

Phase A wires conflict handling into pipeline step 5 (Quality Gates) via `quality-review`, which
applies the hierarchy and records the resolution.
