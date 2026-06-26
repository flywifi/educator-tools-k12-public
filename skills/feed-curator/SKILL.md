---
name: feed-curator
description: "Keep the education-feeds catalog (shared/feeds/feeds.json) accurate so the feed self-updater never works off broken links. Use whenever someone wants to add, check, fix, clean up, or find more RSS/Atom feeds — e.g. 'validate our feeds', 'this OCPS link is dead', 'find Orange County Public Schools news feed', or 'add Monarch Learning Academy'. It runs tools/seed_curator.py to validate every feed (dead links, redirects, staleness, mislabels), discover candidates by polite RSS autodiscovery, AUTO-APPLY only mechanically-safe repairs (remove a confirmed 404/410, follow a verified 301/302), log every change to ledger/feeds-change-log.json for audit/revert, and propose everything riskier for human approval. Authoritative-first: only tier 'canonical' / authority 'primary' confirms a change. Do NOT use it to generate lessons or to harvest feed items (that is tools/feeds_update.py); it is NOT an evasive scraper — it crawls only public pages, respects robots.txt, and reports blocked hosts."
---

# feed-curator

The **librarian** for the education-feeds catalog. The feed self-updater (`tools/feeds_update.py`) is
only as good as its address book; this skill keeps `shared/feeds/feeds.json` accurate, well-labeled, and
free of link-rot so teachers get current information from live sources.

> **Ethics and boundaries (read first).** Crawl only **public** pages, respect `robots.txt`, and back
> off rather than bypassing protections. Never fabricate a feed URL, a label, or a "verified" status.
> When a host is blocked by network/egress policy, **report the blocked host** — do not route around it.

## What this skill does
- **Validate** every feed via the F2 currency engine — dead (404/410), unreachable, stale, superseded,
  plus static **label checks** (`category` / `authority` / `tier` / `purpose` sanity) and a redirect
  probe. Output: a catalog-health report.
- **Discover** candidate feeds by **RSS autodiscovery** from an authoritative page (parses the
  `rel=alternate` feed links), tagged with provenance — candidates are proposals, never auto-added.
- **Propose** a single human-reviewable change set (add / remove / repair / relabel), each entry tagged
  `safe_repair`.
- **Apply** — auto-apply **only mechanically-safe repairs** (remove a confirmed 404/410, follow a
  verified 301/302); everything else needs human approval. **Every** change — auto or approved — is
  appended to `ledger/feeds-change-log.json` and is reversible with `--revert`.

## How it works — the unified pipeline
Follow the shared pipeline in `references/method.md`
(`Request → Routing → Protocol Enforcement → Generation → Validation → Quality Gates →
Approval/Certification → Release`). The domain work runs the tools:

```bash
python3 tools/seed_curator.py --validate                  # catalog-health report
python3 tools/seed_curator.py --discover-from PAGE_URL     # RSS autodiscovery candidates
python3 tools/seed_curator.py --propose                   # dry-run change set (no writes)
python3 tools/seed_curator.py --apply                     # auto-apply SAFE repairs (writes + logs)
python3 tools/seed_curator.py --log                       # the audit trail
python3 tools/seed_curator.py --revert ENTRY_ID           # undo a logged change
```

- **Authority** — only `tier: canonical` / `authority: primary` confirms a change; `news_teacher_student`
  is secondary (discovery-only) and the `product_updates` layer is OFF unless a teacher opts in. Never
  treat a secondary feed as a canonical source.
- **Conflicts** — when sources disagree, emit a decision record + minority report via
  `shared/context/sot_resolver.py`.

## Real-world scope (test data)
- **Public — Orange County Public Schools (OCPS).** District 48 (Orange County, FL); newsroom at
  `ocps.net` (a Finalsite site). OCPS feeds enter the catalog as `tier: canonical` candidates and are
  validated/repaired here before the updater harvests them.
- **Private — Monarch Learning Academy (Orlando, FL).** A real PK–8 private Christian school (College
  Park, 1914 Edgewater Dr, Orlando FL 32804). The first private-school example: cataloged
  `scope: school`, `authority: secondary`, with any site news/feed discovered and human-approved, never
  assumed.

## Artifacts
See `references/artifact-types.md` for the artifact types this skill produces and their specs.

## Output: always emit the metadata block
Every report/proposal ends with the metadata block from `protocols/metadata-schema.md`, including the
decision and `human_review_required: true` — curation output is decision support, and catalog edits
beyond mechanically-safe repairs are human-approved. No real student data; public feed metadata only.
