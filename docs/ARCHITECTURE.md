# ARCHITECTURE.md
## Teacher Operating System (TOS) — Architecture
Governance document (Quality Gates §2.1). Authoritative description of how the ecosystem is built.

---

## 1. What this is

TOS is a **hub-and-spoke ecosystem of Claude Agent Skills** that generate, validate, differentiate,
govern, and improve K–12 educational artifacts. It is delivered as multiple installable skills that
share one governed core, so it *feels* like a single "Teacher Operating System" while remaining
modular and testable.

## 2. The three layers

```
skills/        the capabilities (hub + spokes + governance skill)
shared/        the cross-cutting engines (Standards, Differentiation, Quality, Context, Connectors, Students, DocIntel, Records)  [canonical]
protocols/     the governance rule sets (the 6 protocols)                       [canonical]
```

- **Hub:** `skills/teacher-core/` — mission, personas, the unified pipeline, and **routing**.
- **Governance skill:** `skills/quality-review/` (Phase A) — executes the Quality Gates Protocol.
- **Spokes (Phase A+):** `lesson-planner`, `assessment-designer`, `presentation-builder`, then the
  expansion set (curriculum-mapping, special-education-support, intervention-mtss,
  family-communication, professional-learning, school-administration).

## 3. The unified pipeline

`Request → Routing → Protocol Enforcement → Generation → Validation → Quality Gates →
Approval/Certification → Release`. Canonical definition: `shared/method/method.md`.

## 4. Progressive disclosure (why it's decomposed)

A Skill loads in three levels: name+description (always), `SKILL.md` body (when triggered, target
<500 lines), bundled resources (on demand). The charter's huge surface can't fit one file, so it is
split into focused skills that pull detail from `references/` and the shared core on demand.

## 5. The two-copy / sync model

`shared/` and `protocols/` are the **single source of truth**. For portability, each skill carries
**synced copies** of the cross-cutting references it needs (`references/method.md`,
`references/quality-gates.md`, …). The mapping lives in `tools/sync_manifest.json`; the drift guard
`tools/sync_check.py` guarantees the copies never diverge from canon. (Pattern: an invariants-based
drift guard — assert invariants, not textual diffs.)

## 6. Dependency order

`skill architecture → shared engines + protocols → capability skills → integration → hardening →
advanced` (Charter dependency model). Quality Gates depends on the other five protocols (QG §3.3).

## 7. Repository map

```
skills/ shared/ protocols/ tools/ examples/ .github/workflows/
CLAUDE.md README.md STATE.md TOS_ECOSYSTEM_BUILD_OUTLINE.md
ARCHITECTURE.md QUALITY_MODEL.md SECURITY_AND_SAFETY.md ROUTING_MODEL.md CHANGE_MANAGEMENT.md
```

## 8. AI systems (Phase E2)

The ecosystem's "AI" is layered deliberately:
- **Generation** is the LLM following a capability skill (analysis → standards → differentiation →
  generation). The skill constrains and grounds it; it never invents standards/citations.
- **Evaluation is LLM-as-judge, made auditable.** `quality-review` is the LLM applying the 9-dimension
  rubric *with evidence*; the **deterministic aggregator** `quality-review/scripts/score.py` then
  computes the weighted composite, thresholds, and critical-failure override — so the *judgment* is
  the model's but the *arithmetic and the verdict rule* are reproducible and not hand-waved.
- **The charter's "AI Artifacts" category** lives here as an internal concern (the judge + the
  scoring tool + the metrics), not as a teacher-facing skill.
- **Analytics** (`tools/metrics.py`) reads the ledger + registry to render `METRICS.md` — closing the
  loop from generation → gate → ledger → metrics.

This keeps the powerful-but-fuzzy part (LLM judgment) separable from the parts that must be
deterministic (weights, thresholds, overrides, drift, packaging).

See `TOS_ECOSYSTEM_BUILD_OUTLINE.md` for the full build plan and `STATE.md` for live status.
