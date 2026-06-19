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
shared/        the cross-cutting engines (Standards, Differentiation, Quality)  [canonical]
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
`tools/sync_check.py` guarantees the copies never diverge from canon. (Pattern borrowed from the
iMessage Forensic Toolkit's `sync_check.py`.)

## 6. Dependency order

`skill architecture → shared engines + protocols → capability skills → integration → hardening →
advanced` (Charter dependency model). Quality Gates depends on the other five protocols (QG §3.3).

## 7. Repository map

```
skills/ shared/ protocols/ tools/ examples/ .github/workflows/
CLAUDE.md README.md STATE.md TOS_ECOSYSTEM_BUILD_OUTLINE.md
ARCHITECTURE.md QUALITY_MODEL.md SECURITY_AND_SAFETY.md ROUTING_MODEL.md CHANGE_MANAGEMENT.md
```

See `TOS_ECOSYSTEM_BUILD_OUTLINE.md` for the full build plan and `STATE.md` for live status.
