# standards-verification.md
## Standards Verification Protocol
Version: 1.0 (reconstructed from the Quality Gates references; approved)
Derived from: QG §9 (Accuracy gates: "Are standards references valid?"), §25 (Accuracy rubric:
standards accuracy), §11.4 (fabricated standard = automatic integrity failure), §3.3.

> **Status note.** Reconstructed from the Quality Gates references and approved for use (v1.0).
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

## 6. Citation-mutation check (origin-form rule)

A standard can be cited wrongly even when its **code is real and correctly resolved**: the
artifact's *restatement* of the standard drifted somewhere between the registry and the page.
This is the common real-world failure — a benchmark paraphrased from a pacing guide, worksheet
bank, or prior artifact rather than from the framework text itself. When an artifact quotes or
paraphrases a standard's text/benchmark, compare it against the registry text
(`shared/standards/`, `canonical-sources/registries/`) and flag any of these mutations:

| Mutation | Standards example |
|---|---|
| **Value drift** | a benchmark quantity altered ("numbers to 100" restated as "numbers to 1,000") |
| **Unit/denominator swap** | per-problem vs. per-set expectations, digits vs. place values, percent vs. points |
| **Caveat stripping** | a clarification/limitation dropped ("with support", "using visual models", "in familiar contexts") |
| **Hedge removal** | "students explore/begin to" restated as "students master/demonstrate" |
| **Scope broadening** | one grade band/strand/context generalized ("Grade 3 fraction benchmarks" cited as "elementary math standards") |
| **Attribution laundering** | a paraphrase credited to the framework itself (e.g., a district pacing-guide summary presented as the B.E.S.T. benchmark text) |

**Origin-form rule:** an artifact states a mutated standard in the **registry's origin form**, not
the form encountered in a secondary source. Treatment on review: a mutation found by
`quality-review` is an Accuracy deficiency → Remediation (QG §25); a mutation that changes **what
the standard requires** (value drift, scope broadening) is treated like a mis-coded standard (§4).
The comparison target is always on disk — no fetch is needed to run this check.
