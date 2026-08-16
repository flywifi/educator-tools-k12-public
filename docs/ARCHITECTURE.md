<!-- last_reviewed: 2026-08-16 | owner: architecture-maintainer -->
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

- **Hub:** `skills/core/teacher-core/` — mission, personas, the unified pipeline, and **routing**.
- **Governance skill:** `skills/core/quality-review/` (Phase A) — executes the Quality Gates Protocol.
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

## 5a. The standards trust chain (corpus → overlay → resolver → gates)

```
FLDOE rule documents  ──parse──▶  data/<subject>.json        (parsed corpus — NEVER mutated)
                                        │
CPALMS (official site) ──verify──▶ data/overlays/<subject>.cpalms.json
                                        │        (per code: verified statement, CPALMS id + URL,
                                        │         revision date, checked_at; additions/renumberings)
                                        ▼
                          tools/verify_standards.py  (offline resolver + §6 mutation comparator)
                                        │
                    ┌───────────────────┴────────────────────┐
                    ▼                                        ▼
   tools/validate_outputs.py                    skills/core/quality-review
   (`unresolvable_standard`, blocking → CI)     (Accuracy gate, evidence-based)
```

Three rules make this trustworthy:
1. **The parsed corpus is never overwritten.** Verification lands in a separate overlay, so parse
   provenance and verification provenance stay independently auditable.
2. **Severity follows evidence.** Absence blocks where the corpus is corroborated against
   CPALMS above the trust threshold — since 2026-08-13 that is every Florida subject. The
   degradation path survives in code as a safety net: a corpus reverted below the threshold
   degrades to advisory rather than accusing real standards of fabrication
   (`protocol-layer/standards-verification.md` §5).
3. **Verification and mutation detection are different comparators.** Verification must tolerate a
   corpus statement that appends clarifications; the §6 mutation check must not. Sharing one
   comparator misses value drift and caveat stripping (audit finding F5).

`tools/cpalms_verify.py` produces overlays (network, polite, robots-respecting, resumable) in two
phases — verify, then a human-reviewed apply. Nothing is auto-applied.

## 5b. The tool surface (MCP) — the same corpus, callable
The engines above are *documents the model reads*. The same verified data is also exposed as
**eight read-only tools** so an assistant can look a standard up rather than recall it:
`tools/mcp_tooldefs.py` is the single registry (names, JSON Schemas, governance-bearing
descriptions, handlers), and four delivery legs serve it — plugin-shipped stdio, the Claude
Desktop `.mcpb` bundle, a hosted streamable-HTTP endpoint (dormant until someone deploys it),
and a generated OpenAPI document for Custom GPT Actions.

Two architectural rules make that safe rather than merely convenient. **The registry is the
only definition**: the advertised schema is enforced at call time on every leg, and `sync_check`
checks 22 and 23 hold the ChatGPT-side artifacts and the Claude-side derived schema to it, so
the two platforms cannot be told different rules. **The surface is read-only by construction**:
every tool carries `readOnlyHint`, and the excluded operations (index rebuild, overlay writes,
any harvest/crawl path) are listed by name in the registry docstring — the trust chain in §5a
is what the tools serve, never something they can alter.

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
