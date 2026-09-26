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
- Consumers: teacher-facing setup docs and the per-vendor pack builder (lands with R5-D;
  install pages cite the matrix row they depend on). Edit the matrix, then regenerate — never
  fork a claim.
- Freshness: `updated` is gated by sync_check check 24 (dated manifests). The weekly vendor
  watcher and its source registry land with R5-F (see this README's tail once it does).
