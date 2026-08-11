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
| **Human approval per write** | `--apply <report>` is a dry-run; `--apply --write` needs explicit human approval **in that session**. Never write an overlay unattended. |
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
3. **`--codes` reports cannot be applied.** An ad-hoc report has no `subject`, and `run_apply`
   rejects it ("ad-hoc reports cannot be applied"). Use `--codes` for probing only; never build a
   chunk of real work with it.
4. **One report file per subject+grade chunk. Never reuse one.** `--resume` restores the report's
   rows but does **not** re-derive scope from the CLI flags you pass this time. Reusing a report
   across scopes silently mixes them.
5. **A `skipped_robots` summary means: delete the report and stop.** Those rows are written into
   `report["rows"]`, so a later `--resume` treats every one of them as *done* and skips it forever.
   Delete the file and restart the chunk once robots access is available again.
6. **`checked_at` is compared as a string.** `_now()` emits `Z`-form UTC only. Do not introduce an
   offset-form timestamp anywhere in the overlay path.

## 3. Find out what is left — never guess, never read a number from prose

```bash
python3 tools/cpalms_verify.py --manifest     # offline, deterministic, ~1s
```

Writes `ledger/cpalms-run-manifest.json`: verified vs remaining **per subject and per grade**, by
set difference over committed state, stamped with `anchor_commit` and per-corpus `corpus_sha256` so
staleness is detectable. **This file is authoritative over any count written in prose anywhere in
this repo, including in this runbook.** Regenerate it after every overlay write.

## 4. Run one chunk

```bash
SUBJ=math; GRADE=6                                   # one subject, ONE grade
REPORT="$PWD/.local-reports/$SUBJ-$GRADE.json"       # or a scratchpad path; see §0
mkdir -p "$(dirname "$REPORT")"

# forward verify (network, polite, resumable; overlay-verified codes are skipped automatically)
python3 tools/cpalms_verify.py --subject $SUBJ --grades $GRADE --out "$REPORT"

# if the run was interrupted, resume the SAME file — and make a missing file loud:
python3 tools/cpalms_verify.py --subject $SUBJ --grades $GRADE --out "$REPORT" \
        --resume --require-resume

# reverse census for that ONE grade (see §2.1)
python3 tools/cpalms_verify.py --subject $SUBJ --grades $GRADE --enumerate \
        --out "${REPORT%.json}-census.json"
```

Useful flags: `--ignore-overlay` (deliberate re-verification / currency refresh — not for normal
runs), `--limit N` (pilot), `--checkpoint-every N` (default 10; also flushed on SIGTERM/SIGINT).

Expect ~3.1–5.8 s per code (a randomized 1.5–3.0 s delay precedes every fetch). Budget accordingly
and prefer more, smaller chunks over one long run.

## 5. The done-chain for a chunk

1. `--apply <report>` — dry-run. Read the review queue.
2. **Present the queue to a human and get approval.** This is a gate, not a formality.
3. `--apply <report> --write` (add `--include-additions` only if the census found real additions and
   the human approved them).
4. `python3 tools/cpalms_verify.py --manifest` — regenerate the work manifest.
5. `python3 tools/sync_check.py` — must exit 0. **Run this before `git add`, not after.**
6. `python3 tools/metrics.py` — regenerate `docs/METRICS.md` (never hand-edit it; check 16 enforces
   freshness).
7. Update `STATE.md` / `changes/CHANGELOG.md` if the chunk closes a subject or a phase.
8. Commit, push with `git push -u origin <branch>`, confirm CI green.
9. **No session links** in any commit message, file, or PR body — ever.

When the manifest shows 0 remaining: delete the standing Routine (§7).

## 6. Open findings — known, do not re-litigate

- **D-J (OPEN, cosmetic, mitigated)** — the legacy `.doc` parse loses apostrophes and drops `e.g.,`
  markers. Verified codes carry CPALMS's text in the overlay, so artifacts compare against correct
  wording; the fix is a FLDOE source-document refresh, not a code change.
- The seven residual risks in `docs/audits/2026-08-10-launch-readiness-audit.md` §4, and the
  correction note in §6 of that file.
- Social studies is a best-effort parse (low whole-corpus coverage), so its absences stay
  **advisory** by design — a fabricated SS code is not blocked. This is deliberate: a parser gap
  must never be reported as a fabricated standard.

## 7. The standing Routine

A Routine may exist that wakes a fresh session to work the next chunk. Its id is recorded here:

> **Routine id:** `_(recorded when created — see §7 note below)_`

It is scoped to **one chunk per firing**, is forbidden from `--write`, from pushing to `main`, and
from opening or merging a pull request. **Delete it when the manifest reaches 0 remaining.**

## 8. Why this file is committed

`.gitignore` excludes `HARVEST_HANDOFF.md` — this repo has a convention that handoff files are not
committed. This runbook knowingly breaks that convention. The exclusion is exactly what left a fresh
session with nothing to read, while hard-won rules like §2.1 existed only inside commit messages.
The old exclusion stays; this file is committed on purpose.
