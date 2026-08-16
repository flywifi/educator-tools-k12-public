<!-- last_reviewed: 2026-08-16 | owner: macos-maintainer -->
# macOS support + `mac-lint` — maintainer notes & findings log

Home for the repo's macOS cross-platform work: the `mac-lint` static guard and a **living log** of
macOS findings to grow as testing continues. The *hands-on, on-a-Mac* runbook is deliberately kept
**out of the repo** (it's a personal tester checklist); this file is the repo-side record — the tool,
the confirmed defects, their status, and how to turn a new finding into a guard or a fix.

## The `mac-lint` guard (`tools/mac_audit.py`)
Static AST checks over first-party Python (`tools/`, `shared/`, `skills/`) that codify the macOS
defects we fixed, so a Linux-only CI can't let a Mac regression slip back in:

1. **bare-interpreter** — a child process spawned by the *name* `"python3"`/`"python"` instead of
   `sys.executable` — as a literal argv **or via a file-local variable holding one**. On a macOS
   venv/pyenv the bare name can resolve to a **different** interpreter (often the Xcode CLT stub
   `/usr/bin/python3`, which lacks the venv's deps) → split-brain failure mid-workflow; under a
   no-shell-PATH GUI/MCP launch it's simply "not found".
2. **encoding** — `open()`/`io.open()` in text mode, or `.read_text()`/`.write_text()` with no
   `encoding=`. The default is locale-dependent, so a non-UTF-8 locale (`LC_ALL=C`) breaks on a
   non-ASCII byte.

Known limitations (kept deliberately, to preserve zero false positives on a hard gate):
`Path.open()` and other attribute-call opens on untyped receivers are not detected (add
`encoding=` anyway); string-command spawns (`subprocess.run("python3 …", shell=True)`) are
**bandit's** beat (security_scan gates `shell=True` at HIGH). An unparseable `.py` used to be
skipped with a `[note]`; since 2026-08-16 it is a **finding** — a file that cannot be parsed cannot
run, and a note plus a green exit hid a real SyntaxError during that very round.

Run it:
```bash
python3 tools/mac_audit.py            # report; exit 1 on findings
python3 tools/mac_audit.py --json
```
It is also enforced as **`tools/sync_check.py` check 19** (hard gate). It no longer degrades to a
`[note]` when the module cannot be imported — since 2026-08-16 every guard that crashes is a
failure, because a guard that cannot run is not a guard that found nothing (checks 12–20). Escape hatch for an intentional case: put
`# mac-audit: ignore` on **any line of the offending call** (multi-line calls included — end-of-call
placement works).

### Adding a new check (as testing reveals new patterns)
1. Add a detector inside `_check_file()` in `tools/mac_audit.py` (walk the AST; append
   `{"file","line","check","issue"}`), and make sure `scan()` surfaces it.
2. Fix every existing violation first (run `python3 tools/mac_audit.py` until clean).
3. It's already wired into `sync_check` check 19 — no further wiring needed; a new check class starts
   gating automatically once `scan()` returns it and the tree is clean.
4. Add a throwaway-injection test to your verification (inject a violation → guard fires → revert).

## Findings log (update as you test)
Confirmed macOS defects and status. Status vocabulary — **RESOLVED** (correction landed AND
validated where it runs) · **OPEN** (identified, not yet corrected) · **UNTESTED** (correction
landed but never validated on the target surface — per QG §49, completing an action is not proof
it worked). UNTESTED is not RESOLVED: say which one it is. OPEN/UNTESTED items need real Mac
hardware to observe (see the on-Mac runbook you keep outside the repo).

| ID | What | Status | Where / guard |
|---|---|---|---|
| D1 | Legacy-office parser couldn't find a normally-installed Mac LibreOffice (PATH-only discovery) | **RESOLVED** | `shared/docintel/parsers/libreoffice_parser.py` reuses `shared/office/office_authoring.py` `_find_soffice()` |
| D2 | Child processes spawned by bare `python3` (split-brain on a Mac venv) | **RESOLVED + guarded** | 6 sites → `sys.executable`; mac-lint *bare-interpreter* |
| D3 | ~10 text opens without `encoding=` (locale-dependent) | **RESOLVED + guarded** | 5 files; mac-lint *encoding* |
| D4 | Cross-platform docs framed the `python3` caveat as Windows-only | **RESOLVED** | `docs/DEPLOYMENT_SURFACES.md` cross-platform section |
| D5 | Hardcoded `/tmp` in a workflow example | **RESOLVED** | `skills/operations/standards-updater/` uses portable relative paths |
| D6 | Bare `python` in a harvest doc | **RESOLVED** | `canonical-sources/schools/HARVESTING.md` → `python3` |
| E1 | PEP 668 `externally-managed-environment` install break | **UNTESTED** — fix landed, awaits on-Mac validation | `tools/deps_preflight.py --install <capability>` installs into the managed `.harvest-venv` (wheels-only, never system Python); `--python-path` exposes the venv interpreter for F2/F3. Verify the exact error text on a Mac. |
| E2 | Homebrew tools invisible under a GUI/MCP PATH | **OPEN** — partly fixed (soffice=D1) + doc'd | MCP absolute-path guidance in `docs/DEPLOYMENT_SURFACES.md`; a general binary resolver is a follow-up |
| E3 | Stale right-click Gatekeeper guidance (Sequoia) | **OPEN** — doc'd; verify on-device | `docs/DEPLOYMENT_SURFACES.md` (System Settings flow) |

### New finding template (append below as you test)
```
### <short title>  (YYYY-MM-DD, macOS <ver> / <arch>)
- What:        <observed behavior>
- Where:       <file:line or surface/step>
- Why/How:     <root cause + mechanism>
- Severity:    Blocker | Major | Minor | Doc
- Class:       interpreter/PATH | packaging | permissions | filesystem/encoding | rendering | shell | code-correctness | claude-surface
- Source:      <authoritative URL backing the claim — register it (see Sources & freshness below)>
- Action:      <fix + whether a new mac-lint check applies>
- Status:      RESOLVED | OPEN | UNTESTED   (UNTESTED = correction landed, not yet validated on the target surface)
- Catchable:   <what in the process should have caught this earlier>
```

### D-NEW1 — convert() reported "ok" for a conversion that produced nothing  (2026-07-16, Linux container / adversarial audit)
- What:        `office_authoring.convert()` returned `{"status":"ok","out":…}` naming a PDF that did not exist (LibreOffice install without the Writer component).
- Where:       `shared/office/office_authoring.py` `convert()`
- Why/How:     soffice --headless exits 0 even when it prints "Error: source file could not be loaded", so `check=True` never trips and the output was never verified — a fake success on any missing-component/filter/profile failure (plausible on macOS Homebrew installs).
- Severity:    Major
- Class:       rendering
- Source:      https://bugs.documentfoundation.org/show_bug.cgi?id=148275
- Action:      **Fixed** — convert() now verifies the output file exists and returns `status:error` with soffice's output when it doesn't. No new mac-lint check (behavioral, not a static pattern).
- Status:      RESOLVED (probe re-run and flipped in the 2026-07-16 remediation round)
- Catchable:   a negative-control probe (component missing → convert must report error) run before shipping convert()

### D-NEW2 — LegacyOfficeParser mislabeled a silent conversion failure as an empty "native" parse  (2026-07-16, Linux container / adversarial audit)
- What:        On the same exit-0 soffice failure, `parse()` returned `extraction_method:"native"`, 0 blocks, and diagnostics with no failure marker.
- Where:       `shared/docintel/parsers/libreoffice_parser.py` `parse()`
- Why/How:     the missing/empty converted txt was treated as empty text rather than as the failure signal it is (tdf#148275 again — the exit code is not the truth).
- Severity:    Minor
- Class:       rendering
- Source:      https://bugs.documentfoundation.org/show_bug.cgi?id=148275
- Action:      **Fixed** — missing/empty txt now returns the `convert_failed` diagnostics path.
- Status:      RESOLVED (probe re-run and flipped in the 2026-07-16 remediation round)
- Catchable:   same negative-control probe as D-NEW1 — the parser inherits convert()'s failure surface

### 2026-07-16 remediation round (adversarial audit of the 24h window — 34 probes)
All confirmed findings fixed in this round; probes re-run and flipped:
- **C2** `deps_preflight --install` exited 0 on a failed install → now exits 1 (system-binary no-op
  stays 0; bare `--install` stays 2).
- **E3** one naive `last_checked` date crashed the whole `source_currency` run → naive datetimes are
  now interpreted as UTC midnight (`_parse_dt`), never a crash.
- **C5** `scrape_feed` pointed at a requirements file that never existed → repointed to
  `tools/requirements-scraper.txt` (bs4). `--install-all` also dedupes shared requirements files.
- **B1/B3** check 20 prefix-match bypasses (deep-path/sibling/suffix; uppercase scheme) → exact-page
  matching per RFC 3986 + IGNORECASE (see "Sources & freshness").
- **A1/A2/A4/A5** mac-lint: variable-held argv detected; `io.open` covered; ignore-pragma works on
  any line of the call; unparseable files skipped with a `[note]`.

### MCP server entries (added 2026-08-15 — all UNTESTED until run on a real Mac)
- **M1 — UNTESTED**: `.mcpb` one-click install of `tos-tools` via Settings → Extensions
  (bundle staged by `tools/build_mcpb.py`; staged-tree stdio probe passes on Linux CI).
- **M2 — UNTESTED**: stdio spawn under Claude Desktop's near-empty GUI PATH using
  `mcp_server.py --print-config desktop` output (absolute command + explicit env.PATH — the E2
  workaround, applied).
- **M3 — UNTESTED**: the stdlib server on the Xcode CLT stub `/usr/bin/python3` (design target:
  stdlib-only, Python ≥3.10; the stub qualifies on paper).
- **M4 — UNTESTED (added 2026-08-16)**: `.mcp.json`'s `${TOS_PYTHON:-python3}` /
  `${CLAUDE_PROJECT_DIR:-.}` expansions resolving in a real Claude Code session — the substitution
  syntax is documented, but only a live run proves the default branch is taken when the vars are
  unset. Set `TOS_PYTHON` to `python3 tools/deps_preflight.py --python-path` output to pin the
  shared managed venv (the stdio leg is stdlib, so the shared one is the right answer here; the
  hosted leg would need `--python-path mcp_server`). Pin the
  managed venv interpreter (the E1/E2 answer for a Mac).
- **M5 — UNTESTED (added 2026-08-16)**: the `.mcpb` `platform_overrides.win32` branch. It exists
  to keep Windows working and is unobservable on a Mac; what a Mac *can* confirm is that the
  darwin path still launches with plain `python3` after the manifest moved to
  `manifest_version 0.3`.
- **M6 — OPEN, not fixable here (added 2026-08-16)**: the plugin manifest (`plugin.json`) has no
  per-OS command and no `${VAR:-default}` form, so Door 1 launches with a bare `python3` and does
  not start on a Windows box with a python.org Python. Documented workaround (user-scope
  `claude mcp add`) in `implementation/mcp/README.md`; `mac_audit`'s json-launcher check exempts
  this one launcher by name *only while that workaround stays documented*.

## Sources & freshness (keeping the research citations verifiable)
Every authoritative source behind the macOS findings is registered in
**`canonical-sources/registries/macos-sources.json`** (Apple, Python/PEPs, Homebrew, Git, Claude Code
docs, BSD/GNU; `authority: secondary` marks community material whose claims must be verified
on-device). The registry is freshness-tracked by the existing engine:

```bash
python3 tools/source_currency.py --summary --domain macos-sources    # fetch + classify (needs network)
python3 tools/source_currency.py --offline --summary --domain macos-sources   # age-only triage
python3 tools/source_currency.py --update-baselines --domain macos-sources    # after human re-review
```

Sources older than the policy's `stale_age_days` (180) — or moved/404/superseded — are flagged for
re-verification, so "is this still the current guidance?" is a command, not an archaeology dig.

**The trigger rule (enforced):** citing an external URL in a maintainer-class doc (this file,
`CLAUDE.md`, `docs/DEPLOYMENT*.md`, any `MAINTAINER.md`) requires registering it in a
`canonical-sources/registries/*.json` source registry (or `tools/url-provenance.json`) —
**`sync_check.py` check 20** hard-fails on an undeclared citation, the doc-side analog of the
code-side URL-provenance check 13. So adding a finding with a `Source:` line *is* the trigger: the
gate won't go green until the source is registered and thereby freshness-tracked.
Matching is **exact-page** (per RFC 3986, https://www.rfc-editor.org/rfc/rfc3986): a citation is
declared only if it equals a registered URL after normalization (scheme/host case-insensitive,
± trailing slash) or adds only a `#fragment`/`?query` to a registered page. A registered *root*
does **not** bless deeper pages — each distinct page cited must be registered, because each page is
what goes stale.
Gotcha: `state.last_checked` must be a full timezone-aware ISO timestamp (a bare date crashes the
age math in `source_currency`).

## Where these lessons live (component-local docs)
The macOS knowledge is folded into the docs a maintainer of each area actually reads:
- `CLAUDE.md` → "Local setup (macOS / cross-platform)" — the developer setup essentials.
- `docs/DEPLOYMENT_SURFACES.md` → cross-platform notes (python3/CLT, PEP 668 venv, Gatekeeper, MCP PATH).
- `docs/DEPLOYMENT.md` → "Optional capabilities & deps" — the managed-venv install + `brew` system bins.
- `shared/office/README.md` → soffice single-resolver rule + the `--install office_authoring` command.
- `shared/docintel/README.md` → the `libreoffice_parser` reuses `_find_soffice()` (Mac) note.
- `skills/educator/presentation-builder/MAINTAINER.md` → office-render install command.
- `tools/README.md` → `deps_preflight --install/--python-path`; `mac_audit` under Guards & CI.
- `tools/requirements-*.txt` headers → the managed-venv install line.
- `canonical-sources/registries/macos-sources.json` → the cited authoritative sources, freshness-tracked
  (see "Sources & freshness" below; enforced by check 20).
- The on-Mac hands-on runbook is kept **outside this repo** (personal tester checklist).
