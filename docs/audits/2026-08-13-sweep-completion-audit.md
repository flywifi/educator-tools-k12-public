<!-- last_reviewed: 2026-08-13 | owner: standards-maintainer -->
# Sweep-completion adversarial audit — full Florida corpus vs CPALMS (2026-08-13)

Scope: the completed verification of **all 6,574 Florida standards** against CPALMS, the two
admitted census additions, the nine recorded retirements, the withdrawn-Remarks sidecar, and the
two trust-threshold crossings (ELD, social studies). Discipline as before: every pass names what
was checked; findings carry RESOLVED / OPEN; the audit closes in a residual-risk statement, never
an all-clear. **This audit ran before the coverage claim below was written anywhere in prose.**

## 1. Pass results

**A3 — offline re-proof of every `confirmed` label.** The strongest check available: for all
6,574 corpus codes, the stored corpus statement was re-compared against the stored CPALMS
statement under the whitespace-insensitive equality predicate — proving the label from the texts,
not trusting the classifier that wrote it. **6,574/6,574 equal. 0 missing entries, 0 label/text
disagreements, 0 entries missing id/url/statement/date.**

**A1 — manifest identity and staleness.** `verified 6,574 + needs_review 0 + remaining 0 ==
corpus 6,574`. Every subject's `corpus_sha256` matches the live corpus file. (`anchor_commit` lags
HEAD by one commit **by construction** — the manifest is generated before the commit that contains
it; the sha256s are the real staleness check.) Overlay entries beyond the corpus are exactly the
expected 14: 5 `cpalms_addition` (3 prior D-K admissions + 2 admitted today at the human gate) and
9 `retired` — none counted as coverage.

**A4 — mutation re-judgement on real shipped pairs.** 37 randomly sampled confirmed pairs;
84 injected mutations (numeric drift, deleted negation / truncation, verb→"master"):
**84/84 rejected, 0 wrongly confirmed**; identity control 37/37 confirm unmutated.

**A5 — end-to-end gate battery.** Nine cases through `validate_outputs`: verified codes in three
subjects pass silently; both admitted additions warn (`standard_needs_review`); a retired CS code
warns (`standard_retired`); fabricated codes in math, **post-flip SS**, and **post-flip ELD** all
block. 9/9 as designed.

**A6 — provenance integrity.** 0 cpalms_ids claimed by more than one code (no cross-card bleed).
URL routing by code shape: **one finding, resolved below.**

**A8 — retired/withdrawn hygiene.** 0 withdrawn Remarks leaked back into corpus rows; 0 retired
codes still in the corpus; 9/9 retired entries carry `needs_review`.

## 2. Findings

| # | Finding | Status |
|---|---|---|
| S1 | **69 SS access-point URLs still pointed at `PreviewStandard`** — all checked 2026-08-09, i.e. written *before* the A2-prior routing fix. The fix corrected new writes, but overlay-as-resume never re-fetches verified codes, so shipped rows kept the wrong path. | **RESOLVED** — URLs recomputed from the stored (genuine, AP-endpoint) ids under the overlay lock, marked `url_repaired`; one repaired URL spot-checked live (detail endpoint returns the code). Lesson recorded: a fix to a *writer* does not repair what it already wrote. |
| S2 | D-H recurrence through grade-span expansion (15 real APs reported absent by the SS 912 census). | **RESOLVED** pre-audit (`e433d33`): per-expanded-grade sweeping + two probes; re-run reconciled 1,599/1,599. |

## 3. What "verified" means here — the claim this audit authorizes

Every one of the 6,574 codes in the committed Florida corpus carries a CPALMS overlay entry whose
stored CPALMS text is **equal** (whitespace-insensitively) to the corpus statement, with a CPALMS
id, a shape-correct preview URL, and a check date. The comparison has no similarity band, no
prefix rule, and no length floor.

**And what it does not mean:** agreement proves *parse fidelity* to documents that themselves came
from CPALMS — not independent corroboration (audit §10.1 of 2026-08-10 stands). A CPALMS-side
error is invisible. The FLDOE rule documents remain the legal source of record and remain
unexamined. The census is strong evidence of completeness, not proof (it reconciled exactly for
every scope, which truncation would have made impossible — but that is induction). The two
additions and nine retirements carry `needs_review`/warnings, not silent equivalence. The §6
comparator remains a detector, not a judge: `human_review_required` stays unconditional.

## 4. Residual risk

1. Single-source lineage (unchanged, §10.1): CPALMS is both the source of the documents and the
   verification target.
2. Currency decays from today: CPALMS revises standards (two revisions and nine retirements were
   found *this session*). The overlay records `checked_at` per code; re-verification is a rerun,
   and the standing Routine exists for it.
3. Census completeness is inductive (exact reconciliation ≠ proof), now with the added caveat that
   S2 showed a clean census can be *silently smaller than the truth* when a query exceeds CPALMS's
   paging cap — the per-grade rule is the mitigation, enforced by probes.
4. S1's class — records written before a fix and never revisited — may exist in other fields; the
   A3 re-proof covers text/state/provenance-presence for all rows, but any future writer fix
   should include a sweep over shipped rows.
