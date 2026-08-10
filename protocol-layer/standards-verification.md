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

1. Resolve each cited code against `shared/standards/` — mechanically:
   `python3 tools/verify_standards.py --input <artifact.json>` (or pass codes directly). The
   resolver also returns the registry `statement` (the origin form for the §6 mutation check).
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

## 5. Validation — the resolver (delivered)

The promised helper exists as **one shared tool**, `tools/verify_standards.py` (not per-skill
copies — shared engines are the source of truth; per-skill duplication is what the two-copy rule
exists to avoid). It is wired into pipeline step 2 via `tools/validate_outputs.py`
(`unresolvable_standard`, blocking) and into the `quality-review` Accuracy gate. Fully offline,
stdlib-only; resolves against the committed FL corpus
(`shared/standards/resources/florida/data/`, 6,500+ codes) and validates CCSS/NGSS coding schemes.

**Honest-degradation states** (severity follows evidence strength — a verification result must
never itself be fabricated):

| State | Severity | Meaning |
|---|---|---|
| `resolved` | clean | exact hit in the enumerated FL corpus (statement returned = §6 origin form) |
| `not_found` | **blocking** | absent from a complete enumerated corpus — the fabricated-code case (§11.4) |
| `not_found_low_confidence` | advisory | absent from a best-effort/partial corpus (SS `.doc` parse; ELD) — verify on CPALMS |
| `malformed` | **blocking** | violates its own framework's coding scheme |
| `scheme_valid_unenumerated` | advisory | CCSS/NGSS structure valid; existence not checkable offline (adapters are scheme-only) |
| `unknown_framework` | advisory | matches no known scheme; register school frameworks in `shared/standards/frameworks/` |

Negative control: `examples/known-bad/fabricated-standard.known-bad.json` must FAIL validation
(enforced by `tools/validate_examples.py` check 1b); the resolver's own `--self-test` (28 probes +
a shape audit over every committed corpus code) runs in CI.

**CPALMS verification loop** (`tools/cpalms_verify.py`) — upgrades a best-effort corpus to
authoritative. Phase V queries CPALMS's free, keyless search-fragment endpoint (registered:
`cpalms-search-fragment-endpoint` in `canonical-sources/registries/fldoe-data-sources.json`) one
polite request per code and classifies honestly (`confirmed / statement_differs / renumbered /
not_on_cpalms / ambiguous / fetch_failed`); Phase A applies a **human-reviewed** report as an
overlay (`data/overlays/<subject>.cpalms.json`) — the parse corpus is never mutated, and nothing
is auto-applied. Once a subject's overlay coverage reaches 98%, the resolver drops its
low-confidence treatment: absence becomes blocking evidence again, and the CPALMS-verified
statement becomes the §6 origin form.

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

**Mechanical check (do not judge this by eye):**
```bash
python3 tools/verify_standards.py --compare <CODE> --text "<the artifact's restatement>"
```
It resolves the code, uses the CPALMS-verified statement (or the registry statement) as the origin
form, and reports flags per category with evidence; exit 1 when any mutation is detected. The
comparator is deliberately **separate** from the corpus-vs-CPALMS verification comparator, which
must tolerate appended clarifications — reusing that one here misses value drift and caveat
stripping (audit finding F5, 2026-08-09). It is a **detector, not a judge**: flags are evidence for
the Accuracy gate; the human review requirement is unchanged.

**Origin-form rule:** an artifact states a mutated standard in the **registry's origin form**, not
the form encountered in a secondary source. Treatment on review: a mutation found by
`quality-review` is an Accuracy deficiency → Remediation (QG §25); a mutation that changes **what
the standard requires** (value drift, scope broadening) is treated like a mis-coded standard (§4).
The comparison target is always on disk — no fetch is needed to run this check.
