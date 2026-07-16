<!-- last_reviewed: 2026-07-16 | owner: macos-maintainer -->
# macOS support + `mac-lint` — maintainer notes & findings log

Home for the repo's macOS cross-platform work: the `mac-lint` static guard and a **living log** of
macOS findings to grow as testing continues. The *hands-on, on-a-Mac* runbook is deliberately kept
**out of the repo** (it's a personal tester checklist); this file is the repo-side record — the tool,
the confirmed defects, their status, and how to turn a new finding into a guard or a fix.

## The `mac-lint` guard (`tools/mac_audit.py`)
Static AST checks over first-party Python (`tools/`, `shared/`, `skills/`) that codify the macOS
defects we fixed, so a Linux-only CI can't let a Mac regression slip back in:

1. **bare-interpreter** — a child process spawned by the *name* `"python3"`/`"python"` instead of
   `sys.executable`. On a macOS venv/pyenv the bare name can resolve to a **different** interpreter
   (often the Xcode CLT stub `/usr/bin/python3`, which lacks the venv's deps) → split-brain failure
   mid-workflow; under a no-shell-PATH GUI/MCP launch it's simply "not found".
2. **encoding** — `open()` in text mode, or `.read_text()`/`.write_text()` with no `encoding=`. The
   default is locale-dependent, so a non-UTF-8 locale (`LC_ALL=C`) breaks on a non-ASCII byte.

Run it:
```bash
python3 tools/mac_audit.py            # report; exit 1 on findings
python3 tools/mac_audit.py --json
```
It is also enforced as **`tools/sync_check.py` check 19** (hard gate; degrades to a `[note]` if the
module can't be imported, like checks 12–14). Escape hatch for an intentional case: put
`# mac-audit: ignore` on the offending line.

### Adding a new check (as testing reveals new patterns)
1. Add a detector inside `_check_file()` in `tools/mac_audit.py` (walk the AST; append
   `{"file","line","check","issue"}`), and make sure `scan()` surfaces it.
2. Fix every existing violation first (run `python3 tools/mac_audit.py` until clean).
3. It's already wired into `sync_check` check 19 — no further wiring needed; a new check class starts
   gating automatically once `scan()` returns it and the tree is clean.
4. Add a throwaway-injection test to your verification (inject a violation → guard fires → revert).

## Findings log (update as you test)
Confirmed macOS defects and status. **Fixed** items landed in the branch's macOS-fixes commit;
**Open** items need real Mac hardware to observe (see the on-Mac runbook you keep outside the repo).

| ID | What | Status | Where / guard |
|---|---|---|---|
| D1 | Legacy-office parser couldn't find a normally-installed Mac LibreOffice (PATH-only discovery) | **Fixed** | `shared/docintel/parsers/libreoffice_parser.py` reuses `shared/office/office_authoring.py` `_find_soffice()` |
| D2 | Child processes spawned by bare `python3` (split-brain on a Mac venv) | **Fixed + guarded** | 6 sites → `sys.executable`; mac-lint *bare-interpreter* |
| D3 | ~10 text opens without `encoding=` (locale-dependent) | **Fixed + guarded** | 5 files; mac-lint *encoding* |
| D4 | Cross-platform docs framed the `python3` caveat as Windows-only | **Fixed** | `docs/DEPLOYMENT_SURFACES.md` cross-platform section |
| D5 | Hardcoded `/tmp` in a workflow example | **Fixed** | `skills/operations/standards-updater/` uses portable relative paths |
| D6 | Bare `python` in a harvest doc | **Fixed** | `canonical-sources/schools/HARVESTING.md` → `python3` |
| E1 | PEP 668 `externally-managed-environment` install break | **Fixed (mechanism) + doc'd** | `tools/deps_preflight.py --install <capability>` installs into the managed `.harvest-venv` (wheels-only, never system Python); `--python-path` exposes the venv interpreter for F2/F3. Verify the exact error text on a Mac. |
| E2 | Homebrew tools invisible under a GUI/MCP PATH | **Partly fixed (soffice=D1) + doc'd** | MCP absolute-path guidance in `docs/DEPLOYMENT_SURFACES.md`; a general binary resolver is a follow-up |
| E3 | Stale right-click Gatekeeper guidance (Sequoia) | **Doc'd; open on-device** | `docs/DEPLOYMENT_SURFACES.md` (System Settings flow) |

### New finding template (append below as you test)
```
### <short title>  (YYYY-MM-DD, macOS <ver> / <arch>)
- What:        <observed behavior>
- Where:       <file:line or surface/step>
- Why/How:     <root cause + mechanism>
- Severity:    Blocker | Major | Minor | Doc
- Class:       interpreter/PATH | packaging | permissions | filesystem/encoding | rendering | shell | code-correctness | claude-surface
- Action:      <fix + whether a new mac-lint check applies>
```

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
- The on-Mac hands-on runbook is kept **outside this repo** (personal tester checklist).
