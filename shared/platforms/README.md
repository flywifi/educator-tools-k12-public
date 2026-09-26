<!-- last_reviewed: 2026-09-25 | owner: platforms-maintainer -->
# shared/platforms — the capability matrix and its sources

`platform-matrix.json` is the single store for "what can an individual teacher's account
actually run" — per platform, per surface, per account type, each entry a dated status
(`available` / `unavailable` / `unverified`) with the vendor source URL. It exists because
your decision made plan-gated capabilities **feature flags**, and because the Round-5 audit
found the repo asserting vendor capabilities ("works on Plus") that the vendor had removed.

Rules:
- A status changes ONLY with a vendor source + a fresh `checked` date. `unverified` beats a
  guess; `UNTESTED-live` in a note means vendor-documented but never exercised on a real
  teacher account.
- Consumers: teacher-facing setup docs and `tools/build_teacher_pack.py` (install pages cite
  the matrix row they depend on). Edit the matrix, then regenerate — never fork a claim.
- Freshness: `updated` is gated by sync_check check 24 (dated manifests);
  `tools/platform_watch.py` polls the vendor feeds in `platform-sources.json` weekly
  (detect-only) so a platform change becomes a matrix edit, not a surprise.

`platform-sources.json` lists every machine-readable vendor feed (RSS/Atom/JSON/md-hash) with
what it covers; rows the container cannot poll (help.openai.com is bot-blocked) are
`kind: "manual-agent"` and belong to the quarterly re-audit checklist.
