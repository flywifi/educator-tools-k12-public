<!-- last_reviewed: 2026-08-11 | owner: standards-maintainer -->
# RUNBOOK — resuming the CPALMS standards verification

**Read this before touching `tools/cpalms_verify.py` or any `*.cpalms.json` overlay.**

This job is long — thousands of codes, hours of polite network time — so it **spans sessions**. A
session that picks it up may have none of the conversation that started it. This file is what that
session reads instead. Everything here is decided, verified, or cited; none of it needs to be
re-derived.

---

## 0. The one thing to understand first

**The report file is not the state. The committed overlay is.**

Verification writes a report (`--out <path>`), and that path normally lives in a session scratchpad
whose directory name embeds a **session UUID**. It does not survive the session. The durable record
is `shared/standards/resources/florida/data/overlays/<subject>.cpalms.json`, which is committed and
pushed.

So Phase V derives its work list from the overlay: **codes already verified there are skipped**.
That is why a fresh session can resume with no report at all, and why re-running a finished scope
costs nothing instead of thousands of redundant requests.

---

## 1. What is already decided — do not re-ask

| Decision | Detail |
|---|---|
| **What `confirmed` means** | Normalized EQUALITY (whitespace-insensitive) and an untruncated card — no prefix rule, no similarity band, no length floor (deleted 2026-08-13; see §2.11). It used to mean "within a 0.97 similarity ratio" — ~3 characters on a median statement, which let 100% of changed numeric bounds and 93.9% of *deleted* negations pass as verified (2026-08-11 audit). The fuzzy band is now `near_match`: a review signal, never a verification. |
| **Only `confirmed` is verified** | The overlay records EVERY disposition with `needs_review: true` — that is what stops a `not_on_cpalms` or `near_match` code being re-fetched from CPALMS on every run forever. `verified`, `needs_review` and `remaining` are three different numbers and the manifest asserts they sum to the corpus. |
| **Human approval per write** | `--apply <report>` is a dry-run; `--apply --write` needs explicit human approval **in that session**. |
| **Census additions** | Codes CPALMS has and the corpus lacks are recorded as `cpalms_addition` via `--include-additions`, opt-in at the human gate. Approved as the standing policy (`547d87a`, `608fa99`). |
| **The parsed corpus is never mutated** | `data/<subject>.json` is parse output. Verification lands in the overlay so parse provenance and verification provenance stay independently auditable. |
| **Branch** | Develop and push on the feature branch. **Never push to `main`.** No PR unless explicitly asked. |
| **Overlay is the §6 origin form** | Mutation checks compare an artifact's citation against the overlay's CPALMS text, not the parse text. |
| **Counts are generated, never typed** | See §3. A typed count is how `STATE.md` came to understate the job by 1,574 codes. |

## 2. Non-obvious constraints (each one cost a real debugging session)

1. **Sweep one grade at a time in the census.** CPALMS silently truncates large result sets. A
   multi-grade `--enumerate` returns a short list and reports real standards as absent — this
   produced 182 phantom "absent" access points in science. The census now sweeps per grade and
   unions the results (`abe1f45`). Do not widen the scope to "save time"; a wrong finding costs far
   more than the extra sweeps.
2. **Access points are a different endpoint.** `.AP.` / `.In.` / `.Su.` / `.Pa.` codes are served by
   `GetSearchAccessPoint`, not `GetSearchStandard`, and their provenance URLs resolve under
   `PreviewAccessPoint`, not `PreviewStandard` (`3e801fb`, `6a15803`). Routing is automatic by code
   shape — but if you add a code form, check both.
3. **`--codes` reports are only unapplyable WITHOUT `--subject`.** `run_apply` rejects a report
   with no `subject`, but `run_verify` stamps the subject from `--subject` regardless of `--codes`,
   so `--codes X --subject math` produces a fully applyable report whose `grades` field reads
   `"all"` and which appends a scope entry claiming grades=all. Use `--codes` for probing only —
   and never with `--subject` if you are not applying it. *(This entry previously stated the
   safety property as absolute. It is not; the runbook was written from memory rather than from
   the code, which is the same mistake that produced the census defect below.)*
4. **One report file per subject+grade chunk. Never reuse one.** `--resume` restores the report's
   rows but does **not** re-derive scope from the CLI flags you pass this time. Reusing a report
   across scopes silently mixes them.
5. **A `skipped_robots` summary means: delete the report and stop.** Those rows are written into
   `report["rows"]`, so a later `--resume` treats every one of them as *done* and skips it forever.
   Delete the file and restart the chunk once robots access is available again.
6. **`checked_at` is compared as a string.** `_now()` emits `Z`-form UTC only. Do not introduce an
   offset-form timestamp anywhere in the overlay path.
7. **The census runs into the SAME file as the forward report.** `run_enumerate` loads an existing
   `--out` and adds `census`/`census_diff` to it; `run_apply` reads additions from the one report
   it is handed. A census written to a separate file leaves `corpus_missing` empty, so
   `--include-additions` silently finds nothing and every census finding is dropped. `--apply` now
   refuses rather than no-ops, but write them to one file in the first place.
8. **Grade SPANS are expanded for the sweep, not for the scope. PROVEN LIVE 2026-08-11.**
   `social_studies --grades 912` (sweeping 9,10,11,12): corpus scope 1,599, census returned
   **exactly 1,599**, `cpalms_absent = 0`, 16 benchmark + 13 AP pages run to exhaustion, no errors.
   `--grades 68` likewise returned `cpalms_absent = 0`. Truncation does **not** bite at the largest
   scope in the corpus. **"K12" is NOT a span** — it labels cross-cutting practice standards
   (`MA.K12.MTR.*`, `ELA.K12.EE.*`), 5-7 per subject, and is deliberately left unmapped so the
   census aborts rather than sweeping a whole subject.
   Never "fix" a span by passing `9,10,11,12` yourself: the corpus labels those codes `912`, so
   scoping on the individual grades matches **zero** corpus codes and the tool aborts (by design —
   otherwise the whole census would read as additions).
9. **Census additions are diffed against the WHOLE corpus, not the scope.** A code the census
   returns that sits in the corpus under a different grade label is a scope mismatch, not an
   addition. Diffing against scope alone made `corpus_missing` 554 on the `68` probe when the true
   answer was 1 — and `--include-additions` would have rewritten 553 real standards as census
   stubs. `out_of_scope_in_corpus` reports that surplus separately, and a surplus that dwarfs the
   scope warns loudly, because it means the grade scoping is wrong.
10. **A census that errored writes no `census_diff`.** It records `census_meta` for diagnosis and
   exits non-zero. An empty census is a lie (it claims every code in scope is absent from CPALMS);
   an absent one is detectable.
11. **`confirmed` is EQUALITY now — there is no tolerance left to lean on.** The corpus statement
   and the CPALMS card must be the same text, ignoring only whitespace (CPALMS's HTML drops spaces
   after punctuation and around bullets). No similarity band, no prefix rule, no minimum length.
   A truncated card can only support a prefix claim, so it routes to `near_match`, never
   `confirmed`. If a sweep suddenly produces many `statement_differs` rows, suspect the CORPUS
   first — run `--scan-parse-defects` — before assuming CPALMS changed.
12. **The overlay is write-LOCKED per subject.** `--apply --write` and `--reclassify --write` take
   `overlays/.<subject>.cpalms.lock` across the whole read-modify-write. Atomic writes prevent a
   torn file; they do nothing about two runs each reading the same overlay and the second erasing
   the first's entries. A second writer is refused and told which pid holds the lock. A lock older
   than an hour is reported as stale **with the command to remove it** — it is never auto-broken,
   because auto-breaking is the lost update with extra steps. Different subjects lock
   independently, so parallel per-subject sweeps are fine.
13. **`renumbered` requires exact text AND uniqueness.** It is a disposition — the row stops being
   retried and a citation gets pointed at a different code — so it demands the same evidence as
   `confirmed`. A close-but-inexact single candidate is recorded as `ambiguous` with the candidate
   named, which carries `needs_review` and is never a verification.

## 3. Find out what is left — never guess, never read a number from prose

```bash
python3 tools/cpalms_verify.py --manifest     # offline, deterministic, ~1s
```

Reports three totals bound by `verified + needs_review + remaining == corpus` (asserted, not
hoped). **`needs_review` is not coverage** — those codes were reached and judged but not verified,
and they still need a human. A sweep is finished when `remaining` AND `needs_review` are both 0,
not when `remaining` alone hits 0.

Writes `ledger/cpalms-run-manifest.json`: verified vs remaining **per subject and per grade**, by
set difference over committed state, stamped with `anchor_commit` and per-corpus `corpus_sha256`. Staleness is detected via the **sha256 values only** — `anchor_commit` is the HEAD at generation time and lags the commit containing the manifest by exactly one, on every clean run, by construction; comparing it to HEAD false-positives always. **This file is authoritative over any count written in prose anywhere in
this repo, including in this runbook.** Regenerate it after every overlay write.

## 4. Run one chunk

```bash
SUBJ=math; GRADE=6                                   # one subject, ONE grade
REPORT="$PWD/.reports/$SUBJ-$GRADE.json"             # scratch; NOT committed — see §4a
mkdir -p "$(dirname "$REPORT")"

# forward verify (network, polite, resumable; overlay-verified codes are skipped automatically)
python3 tools/cpalms_verify.py --subject $SUBJ --grades $GRADE --out "$REPORT"

# if the run was interrupted, resume the SAME file — and make a missing file loud:
python3 tools/cpalms_verify.py --subject $SUBJ --grades $GRADE --out "$REPORT" \
        --resume --require-resume

# reverse census for that ONE grade — INTO THE SAME FILE (see §2.7). run_enumerate merges into an
# existing --out; a separate file silently orphans every finding.
python3 tools/cpalms_verify.py --subject $SUBJ --grades $GRADE --enumerate --out "$REPORT"
```

Useful flags: `--ignore-overlay` (deliberate re-verification / currency refresh — not for normal
runs), `--limit N` (pilot), `--checkpoint-every N` (default 10; also flushed on SIGTERM/SIGINT).

Expect ~3.1–5.8 s per code (a randomized 1.5–3.0 s delay precedes every fetch). Budget accordingly
and prefer more, smaller chunks over one long run.

## 4a. Reports are not committed — the overlay is the record

Earlier revisions of this runbook committed a "verified but unapplied" report to
`ledger/in-flight/`. That convention is **withdrawn**. It existed because the overlay could only
record successes, so an unattended session had nowhere durable to put anything else. The overlay now
records **every disposition** with `needs_review`, which makes the report redundant the moment
`--write` runs — and removes the pending-file bookkeeping, the retention problem, and a livelock in
which unresolved rows were re-sliced and re-fetched on every firing.

Reports stay out of git. They are session-scoped scratch; the overlay is the durable record; the
manifest is the answer to "what is left".

## 5. The done-chain for a chunk

1. `--apply <report>` — dry-run. Read the review queue.
2. **Present the queue to a human and get approval.** This is a gate, not a formality.
3. `--apply <report> --write` (add `--include-additions` only if the census found real additions
   and the human approved them — the dry-run now previews them, which it previously could not).
4. `python3 tools/cpalms_verify.py --manifest` — regenerate the work manifest.
5. `python3 tools/sync_check.py` — must exit 0. **Run this before `git add`, not after.**
6. `python3 tools/metrics.py` — regenerate `docs/METRICS.md` (never hand-edit it; check 16 enforces
   freshness).
7. Update `STATE.md` / `changes/CHANGELOG.md` if the chunk closes a subject or a phase.
8. Commit, push with `git push -u origin <branch>`, confirm CI green.
9. **No session links** in any commit message, file, or PR body — ever.

When the manifest shows 0 remaining **and 0 needs_review**: delete the standing Routine (§7).
`remaining` alone reaching 0 does not mean the work is done — it means nothing is left *unseen*.

## 6. Open findings — known, do not re-litigate

- **D-J — RESOLVED 2026-08-13.** It was never a source-document problem: the Social Studies `.doc`
  is UTF-8 and the parser decoded it as latin-1, then stripped non-ASCII, destroying 324 apostrophes
  and 147 smart quotes. The same parser also emitted the whole table row as `statement`, so **52 %
  of the corpus carried document furniture** — and that superset is why the verification comparator
  could not test equality, which is where every tolerance in this tool came from. The parse is
  fixed, the corpus regenerated under `tools/parse_diff.py`, and the tolerances DELETED: no
  similarity band, no prefix rule, no `MIN_CONFIRM_CHARS`, and `renumbered` now requires exact text
  plus uniqueness. Full write-up: launch-readiness audit §10. The `e.g.,` half of D-J was
  misdiagnosed — see §10.3; that one is a CPALMS revision, not a parse loss.
- **Two genuine corpus↔CPALMS divergences remain**, both recorded `statement_differs` /
  `needs_review`: `SS.4.E.1.1` ("social and ethnic" → "demographic") and `SS.5.G.2.1` (CPALMS added
  "(e.g., "). The corpus matches the committed source document in both cases; CPALMS has revised
  them. Do not "fix" the corpus to match — the corpus reflects its source, and the overlay serves
  CPALMS's text to citations.
- The residual risks in `docs/audits/2026-08-10-launch-readiness-audit.md` §4 — originally seven;
  §4.1's two-source claim was retracted in-place and §4.5 and §4.6 are recorded closed there, so
  four remain live. Read §4 itself rather than the count. Plus the two
  correction notes (§6 on the wrong counts, §7 on what `confirmed` used to mean).
- **A4/A5/A6/NEW-8 — RESOLVED 2026-08-11.** The card parser now slices the fragment per card, so a
  regex cannot read across a card boundary: cross-card bleed and positionally-zipped dates are
  structurally impossible, markup is stripped before it reaches `statement_verified`, and
  conflicting duplicate cards are `ambiguous` rather than first-wins. All four were latent — 0
  occurrences in 788 live cards — and the new parser is byte-identical to the old one on every
  committed fixture and on all 788. Two rules came out of it and are worth knowing:
  **(a)** if the exact code is absent AND any card failed to parse, the row is `fetch_failed`, never
  `not_on_cpalms` — "we could not read the response" is not "this standard does not exist", and
  `not_on_cpalms` is the blocking state that reads as fabricated (D-K);
  **(b)** paging stops on a page with **no card markers**, never on "no cards we could parse" —
  otherwise unparseable markup silently truncates a census and every unreached code reads as absent
  from CPALMS, which is D-H arriving through the fix meant to prevent silent loss.
- **The sweep COMPLETED 2026-08-13: all 6,574 codes verified, and SS + ELD absences now BLOCK.**
  Both subjects crossed the coverage threshold, so the old "SS absences stay advisory" rule no
  longer holds — absence is evidence because the corpus is fully corroborated. What this runbook
  is now for: **re-verification** (currency decays; CPALMS revised 2 benchmarks and retired 9
  standards within days), using the same chunk procedure with `--ignore-overlay` for the scope
  being refreshed. The completion audit is `docs/audits/2026-08-13-sweep-completion-audit.md`.

## 6a. Source refreshes — when the DOCUMENT changes, not the parse

The corpora are the parse of exactly one document per subject. When Florida publishes a newer one,
that is a **source refresh**, not a repair, and it is the one operation allowed to move the code set.

```bash
# 1. drop the new document in, then stage a regeneration
python3 tools/parse_fl_standards.py --out /tmp/new --no-index
# 2. gate it, DECLARING every code that may move — the sets must match exactly
python3 tools/parse_diff.py --old shared/standards/resources/florida/data --new /tmp/new \
        --expect-removed CODE1 CODE2 ...
```
`--expect-removed` / `--expect-added` turn a blind override into a checked assertion: an undeclared
code moving still aborts, and so does a declared code that did **not** move (a stale expectation).

Three rules learned the hard way (2026-08-13, computer science + social studies):

1. **Confirm every moved code against CPALMS first**, individually. Both refreshes were justified
   only because CPALMS agreed: 9/9 withdrawn codes returned `not_on_cpalms`, and 6/6 + 15/15 revised
   statements matched CPALMS exactly.
2. **A withdrawn standard is `retired`, never `not_on_cpalms`.** Left as `not_found` it resolves as
   BLOCKING with guidance calling the code fabricated — accusing a teacher of inventing a benchmark
   Florida published. Record retirements in the subject overlay with their evidence.
3. **Withdrawn side content goes to `data/withdrawn/<subject>.withdrawn.json`, not back into the
   corpus.** Florida removed the illustrative `Remarks` from 94 SS benchmarks; they are kept there
   with the sha256 of the document they came from, reachable via `fl_lookup.py --withdrawn`, and
   never served as current. Folding them into corpus rows would break `parse_diff`'s "verbatim in
   the source" proof and leave the next refresh without a clean baseline.

## 7. Currency re-verification — repo code, not a Routine (final form, 2026-08-14)

The sweep is complete, so nothing "continues" — what remains is drift detection: CPALMS keeps
moving, and the oldest-verified entries should be re-checked periodically. Two earlier forms of
this section described a platform Routine; both suffered the same structural weakness — the
Routine's prompt was mutable state on a third-party control plane, reachable only through a tool
that may or may not be connected, and invisible to every gate in this repo (hence the deleted
"byte-identical embedded copy" hack). The mechanism now lives **in the repo**, where it is
versioned, CI-tested, and cannot be orphaned by a disconnected session:

- **`tools/currency_recheck.py`** — the driver. Preflights `tools/audit_overlays.py` (a red
  durable record is never re-verified on top of); re-verifies the ~200 oldest-`checked_at`
  in-corpus codes of the single oldest subject (`--ignore-overlay`, one subject per report);
  runs one per-grade census spot-check of the least-recently-censused scope (stateless rotation
  via `scopes[].generated_at`); writes a `summary.md` verdict. It can only detect: no `--apply`,
  no `--write`, no overlay/corpus/repo mutation, reports land outside the repo tree (§4a —
  reports are scratch). "Zero drift found" is printed as the deliverable.
- **`.github/workflows/currency-recheck.yml`** — runs it — **weekly (Mondays 09:23 UTC;
  owner-enabled 2026-08-14)** plus manual dispatch. The `schedule:` block is the enable switch:
  commenting it back out disables the cadence, as a reviewable commit. `permissions: contents: read`, single-flight concurrency, reports
  uploaded as a 90-day artifact, summary rendered on the run page.

**Exit codes are tri-state on purpose** — a throttled runner must never masquerade as a verdict:

| exit | meaning | what to do |
|---|---|---|
| 0 | zero drift — the deliverable | nothing |
| 1 | drift found (or census drift) | read `summary.md`; handle per §4a/§5 — human-gated, exactly like a sweep finding |
| 2 | preflight red / usage | fix the `audit_overlays` findings first; re-verifying on a bad record compounds damage |
| 3 | environment blocked (robots refusal, >10% transient fetches, census could not conclude) | no conclusion was drawn; try the desktop path below |

**Desktop fallback (first-class, not a consolation):** GitHub-runner IPs may be throttled by
CPALMS's hosting — that is exit 3, untestable until the first real dispatch. The identical run
from any clone: `python3 tools/currency_recheck.py` (stdlib-only; add `--workdir ~/tmp/currency`
to keep reports somewhere findable). Local scheduling, if wanted, is one crontab line:
`23 9 * * * cd <clone> && python3 tools/currency_recheck.py`.

**The retired Routine.** `trig_01BdmNu2xWDxc3CAxDBvV1Gy` ("CPALMS standards sweep — next chunk")
was **deleted from the claude.ai Routines panel on 2026-08-14** (by the owner, after the workflow's
first live run came back zero-drift). Nothing platform-side remains; this workflow is the whole
mechanism.

During the sweep, every subject's span census was validated live per grade (an earlier claim
that only social studies had been was wrong and is retracted).

## 8. Two rules that produced everything above

1. **No design change ships without an adversarial pass.** The in-flight convention (§4a) was
   invented *during* execution, after the audit had already run, written into this runbook, and
   armed on a scheduled Routine — all in one turn. Six defects followed, including a census path
   that silently dropped every finding. If a convention is invented mid-execution, **execution
   stops** and it goes through falsification first.
2. **This runbook is written from the code, not from memory.** Every procedural claim must cite the
   function or commit that makes it true. Two entries in §2 were wrong precisely because they were
   written from recollection while the code said something else — §2.3's safety property does not
   exist, and §2.7's census path silently dropped findings.

## 9. Why this file is committed

`.gitignore` excludes `HARVEST_HANDOFF.md` — this repo has a convention that handoff files are not
committed. This runbook knowingly breaks that convention. The exclusion is exactly what left a fresh
session with nothing to read, while hard-won rules like §2.1 existed only inside commit messages.
The old exclusion stays; this file is committed on purpose.
