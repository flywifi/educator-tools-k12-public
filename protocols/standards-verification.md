# standards-verification.md
## Standards Verification Protocol
Version: 0.1 (DRAFTED from Quality Gates references — pending your review)
Derived from: QG §9 (Accuracy gates: "Are standards references valid?"), §25 (Accuracy rubric:
standards accuracy), §11.4 (fabricated standard = automatic integrity failure), §3.3.

> **Status note.** Listed as "complete" in QG §2.1 but not delivered. Faithful reconstruction.
> Works hand-in-hand with `shared/standards/` (the standards engine).

---

## 1. Purpose

Standards alignment is the backbone of educational artifacts, and a **fabricated or incorrect
standard is one of the most damaging failures** the ecosystem can produce — QG makes a fabricated
standard an *automatic integrity failure* (§11.4) and an accuracy failure (§25.5). This protocol
ensures every cited standard is **real, correctly coded, current, and genuinely aligned** to the
artifact.

## 2. What "verified" means

A cited standard is verified when all of the following hold:
1. **Exists** — the code resolves to a real standard in a known framework
   (`shared/standards/`: CCSS, NGSS, or a state set via `state-standards-model.md`).
2. **Correctly coded** — the code matches the framework's coding scheme (e.g., CCSS
   `CCSS.MATH.CONTENT.3.NF.A.1`; NGSS `3-LS1-1`).
3. **Current** — the framework **version** is recorded (metadata `standards_set`), and the code is
   not deprecated in that version.
4. **Grade-appropriate** — the standard's grade matches the artifact's `grade_band`.
5. **Genuinely aligned** — the standard actually matches the objective/assessment, not just topically
   adjacent (this is also checked by the Alignment gate, QG §26).

## 3. Verification procedure

1. Resolve each cited code against `shared/standards/`.
2. Confirm coding, version, and grade.
3. Confirm objective↔standard↔assessment alignment (feeds the Alignment gate).
4. Record the result in the artifact metadata (`standards_set`, `standards_cited`).
5. On failure: do **not** ship an unverifiable standard. Either correct it, or log it as an
   assumption + escalate (assumptions-protocol.md). Never invent a code to fill a gap.

## 4. Failure handling

| Failure | Treatment |
|---|---|
| Code does not exist / cannot be resolved | Integrity automatic failure (QG §11.4) → Rejected |
| Wrong grade / deprecated / mis-coded | Accuracy deficiency → Remediation (QG §25) |
| Topically adjacent but not aligned | Alignment deficiency → Remediation (QG §26) |

## 5. Validation

Phase A adds a `scripts/verify_standards.py` helper per capability skill and wires this protocol
into pipeline step 2 (Protocol Enforcement) and the `quality-review` Accuracy/Alignment gates.
