# state-standards-model.md
## State Standards Adapter (state-agnostic)
Canonical source. How any U.S. state standard set "plugs in" to the Standards Engine without
redesign. Phase 0 ships the **adapter pattern**; specific state corpora are added as a data task.

---

## 1. Why an adapter

States either adopt CCSS/NGSS, adapt+rename them, or maintain their own sets (e.g., Texas **TEKS**,
Virginia **SOL**, Florida **B.E.S.T.**). Rather than special-casing each, every state set maps onto
the common `standard` shape from `standards-framework.md`.

## 2. Per-state adapter definition

To add a state, define:

```yaml
state_adapter:
  framework:        # e.g., TX-Math, VA-ELA, FL-ELA
  state:            # full state name
  version:          # adoption year
  code_pattern:     # regex / description of the native coding scheme
  grade_to_band:    # how native grades map to K-2 / 3-5 / 6-8 / 9-12
  subjects:         # subjects covered
  relationship:     # adopts-CCSS | adapts-CCSS | adopts-NGSS | independent
  source_note:      # where the corpus comes from + licensing note
```

## 3. Examples (patterns, not full corpora)

- **Texas (TEKS):** `framework: TX-Math`, codes like `§111.5(b)(3)(A)` (Ch.111 = Math); largely
  independent of CCSS. `relationship: independent`.
- **Virginia (SOL):** `framework: VA-Math`, codes like `3.2` (grade.standard); `relationship:
  independent`.
- **Florida (B.E.S.T.):** `framework: FL-ELA`, codes like `ELA.3.R.1.1`; `relationship: independent`.

## 4. Selection rule

When the user names a state, prefer that state's set over the national default; record the state
framework + version in metadata. If the state set isn't loaded yet, fall back to the closest
national framework, **log the substitution as an assumption** (assumptions-protocol.md), and tell
the user.

## 5. Verification & licensing

State standards are verified the same way (exist / correctly coded / current / grade-appropriate /
aligned — `protocols/standards-verification.md`). **Licensing caveat:** some state corpora have
usage terms; the `source_note` records provenance, and bundling a full corpus is gated on a
licensing check (see Risk register in the build outline).
