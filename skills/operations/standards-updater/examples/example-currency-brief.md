# Example — Florida currency brief (illustrative sample)

> Worked example of the `currency-brief` artifact (see `references/artifact-types.md` and
> `references/updater-method.md` → "Change intelligence"). **Illustrative sample content** — confirm
> every specific on the cited primary source before acting. Public/official data only; no PII.

**Run scope:** monthly · Florida · all coverage vectors
**Recency policy applied:** new ≤ 90 days · forward-looking ≤ 730 days (per `sources.json → monitoring_policy`)

## Confirmed changes (primary-source verified)

### 1. State Board rule edit — FAC 6A-1.09441
- **Source class:** `official_register` / `official_primary` — flrules.org (Florida Administrative Code).
- **Verified on:** `https://flrules.org/gateway/ruleNo.asp?ID=6A-1.09441` (primary).
- **Published:** sample-date · **Effective:** sample-date (within the forward-looking window).
- **Confidence:** high (rule text states the change directly).
- **Impact dimension(s):** graduation · assessment.
- **Why it matters:** a change to this rule can shift assessment/credit requirements that feed diploma
  designations — review pacing guides and graduation-requirement guidance, and re-check affected
  `resources/florida/admin/` documents.
- **Recommended action:** verify the adopted text, then refresh the corresponding stored documents +
  `sources.json` hashes; no standards codes change without CPALMS confirmation.

### 2. Statute with a future effective date — FL Statutes Title XLVIII (ch. 1000–1013)
- **Source class:** `official_legislative` — leg.state.fl.us.
- **Verified on:** the official statute text (primary).
- **Published:** older than 90 days, **but** flagged because its **effective date is inside the
  ≈2-year forward-looking window**.
- **Confidence:** medium (clear text; scope/effect still needs interpretation for our corpus).
- **Impact dimension(s):** courses/curriculum · policy/compliance.
- **Why it matters:** forward-looking mandates can require course or pacing updates before they take
  effect — surface now so districts are not surprised at the effective date.

## Gaps (not included in results — discovery only / unconfirmed)
- A secondary summary (association newsletter) describes a possible assessment-window change, but the
  **primary FLDOE source could not be confirmed** at run time → recorded as a gap, **excluded from
  results** until verified on the primary source (per the verification rule).

## Metadata (per `protocols/metadata-schema.md`)
```yaml
artifact_type: currency-brief
reviewer: standards-updater (self-check) then quality-review
decision: null            # set by quality-review; this is decision support, not a final ruling
date: <ISO-8601 at run time>
standards_set: FL-BEST / NGSSS (Florida)
confirmed_changes: 2
gaps: 1
human_review_required: true
assumptions:
  - Sample/illustrative content; specifics must be confirmed on the cited primary source.
  - No standards code is changed without CPALMS verification.
```
