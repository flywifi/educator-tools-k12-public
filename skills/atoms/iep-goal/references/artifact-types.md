# Artifact Types — atom-iep-goal

## IEP annual goal draft

The single artifact produced by this atom is **one draft IEP annual goal** — a structured JSON
object in the standard SMART format (condition + behavior + criterion) with a short-term objective.

**Required fields:**
- `goal`: `{condition, behavior, criterion, timeframe, full_text}`
- `short_term_objective`: mid-year benchmark
- `measurement_method`: how progress will be tracked
- `standard_alignment`: the aligned FL B.E.S.T. standard
- `plop_used`: the baseline used to write the goal
- `placeholders`: list of `[Student]`, `[Date]` tokens to fill
- `human_review_required: true`
- `legal_notice`: must be preserved in all output

**Not produced by this atom:** full IEP documents, BIPs, or goals without a PLOP baseline.
