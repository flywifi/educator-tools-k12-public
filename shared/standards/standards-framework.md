# standards-framework.md
## The Standards Engine
Canonical source. How the ecosystem selects, cites, and verifies standards across **all of K–12**
(scope decision: full K–12, breadth-first via a state-agnostic adapter).

Works with `protocols/standards-verification.md` (the verification rules) and the framework files
in this directory (`ccss.md`, `ngss.md`, `state-standards-model.md`).

---

## 1. Design: state-agnostic adapter

A standard, in any framework, is normalized to a common shape so skills don't hard-code one
framework:

```yaml
standard:
  framework:     # CCSS-Math | CCSS-ELA | NGSS | <STATE>-<SUBJECT>
  version:       # e.g., 2010 (CCSS), 2013 (NGSS), or state adoption year
  code:          # the framework's native code, verbatim
  grade:         # K,1,...,12  (rolls up into a band)
  band:          # K-2 | 3-5 | 6-8 | 9-12
  subject:       # Math | ELA | Science | <subject>
  statement:     # the human-readable expectation
  domain/cluster:# framework-native grouping (optional)
```

Each framework file provides an **adapter**: how to parse its codes, how grades map to bands, and
how to resolve a code to a statement. National frameworks (CCSS, NGSS) ship as first-class adapters;
state sets plug in via `state-standards-model.md`.

## 1a. Standards applicability (context-conditional)

Before selecting standards, read `standards_applicability` from the resolved context
(`shared/context/`). It decides whether — and which — standards apply:

- **`best_ngsss_apply`** (traditional public, charter, district-virtual, FLVS) — select + cite +
  **verify** FL B.E.S.T./NGSSS as in §2–§4.
- **`school_defined`** (private) — use the school's framework registry
  `shared/standards/frameworks/<id>.json` (IB/AP/Cambridge/Montessori/classical/ACSI) as **primary**;
  cite that framework. Optionally **crosswalk** to FL (`shared/standards/crosswalks/`) to show coverage.
- **`parent_selected`** (home education) — standards are **advisory**: state clear learning objectives
  and offer *optional* alignment/crosswalk for the family's reference; do **not** force a mandated
  framework. Absence of state codes here is correct, not a defect.

Independent frameworks: `frameworks.md`. Cross-mapping: `crosswalks.md`. **Never invent a code in any
mode** — verify on the framework's source, or state the objective without a code.

## 2. Selecting standards (pipeline step 3, "Standards Alignment")

1. From the request, determine **subject + grade band** (assume + log if missing — assumptions
   protocol).
2. Choose the **framework**: default CCSS (ELA/Math) and NGSS (Science); use a state set when the
   user names a state (`state-standards-model.md`). **Florida is fully wired** — `florida-best.md`
   (B.E.S.T. Math/ELA, NGSSS Science/SS, CS, ELD) + the `resources/` catalog. The national overlay
   `state-standards-map.md` / `states.json` says which framework each state follows.
3. Select the **most specific aligned standard(s)** for the objective — not merely topically
   adjacent (alignment matters; QG §26).
4. Prefer a small number of well-aligned standards over a long shallow list.

## 3. Citing standards

Always cite **framework + version + code** so the citation is verifiable, e.g.:
`CCSS.MATH.CONTENT.3.NF.A.1 (CCSS-Math, 2010)`. Record citations in artifact metadata
(`standards_set`, `standards_cited`).

## 4. Verifying standards

Follow `protocols/standards-verification.md`: a cited standard must **exist, be correctly coded, be
current, be grade-appropriate, and be genuinely aligned**. A fabricated standard is an automatic
integrity failure (QG §11.4). Never invent a code to fill a gap — correct it or escalate.

## 5. Scope & roadmap

Phase 0 ships the **framework + adapters + representative anchors** spanning K–12 (see `ccss.md`,
`ngss.md`, `state-standards-model.md`). **Exhaustive standard-by-standard enumeration is a later
data task** (Phase B/C) — the engine is designed so adding the full corpus is data entry, not
redesign (QG §97 future-compatibility).
