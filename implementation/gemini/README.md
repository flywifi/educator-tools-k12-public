<!-- last_reviewed: 2026-11-25 | owner: repo-maintainer -->
# TOS on Google — Antigravity and Gemini in the browser

| You use… | Get this | Time |
|---|---|---|
| **Antigravity** (the desktop app) or the **Antigravity CLI** (`agy`) | The **TOS plugin**: every skill, the TOS review rules, and the verified-standards tools | ~3 min |
| **Gemini in the browser**, including a Gem your school assigns in Classroom | The **Gem pack**: reduced mode, no tools | ~5 min |
| **Gemini CLI** | Google stopped serving it to individual, AI Pro and AI Ultra accounts on 2026-06-18. Use the Antigravity CLI with the plugin below. | — |

> Always true: everything is a **draft for your review** · verified standards data is
> **Florida** · never type real student names — the tools neither need nor keep them.

## Antigravity: install the TOS plugin

Antigravity needs a personal Google account (18+). School Google Workspace accounts don't
include Antigravity plans.

1. Download **`tos-antigravity.zip`** from the newest release on the GitHub Releases page
   (`https://github.com/flywifi/educator-tools-k12-public/releases`) and unzip it somewhere
   permanent.
2. **In the app:** type `/plugin`, open **Installed**, choose *install from a local directory*,
   and pick the unzipped folder. **In a terminal:** `agy plugin install <that folder>`.
3. Test it: *"Use the tos-tools verify_standard_codes tool to check MA.3.NSO.1.1 and
   MA.3.NSO.9.99."* The first is a real Florida code; the second is flagged as not real.

The tools need Python 3.10 or newer. On Windows, the current python.org installer (the Python
install manager) includes the `python3` command the plugin starts; with an older install, open
the plugin's `mcp_config.json` and change `"python3"` to `"python"`.

Privacy: check Antigravity's Settings › Account › Telemetry before any classroom use.

## Gemini in the browser: the Gem pack

1. Download **`tos-gem-pack.zip`** from the same release and unzip it.
2. Create a Gem. Paste the contents of `gem-instructions.md` into its **Instructions** box and
   add the pack's data file as the Gem's knowledge, as the pack's `README.md` describes.
3. No tools run in a Gem, so every standards code is checked against the attached file, and a
   code that isn't in it is marked unverified.

---

Maintainers: the packs are built by `python3 tools/build_teacher_pack.py --zip` and attached to
each release by `.github/workflows/frozen-build.yml`; support status per product lives in
`shared/platforms/platform-matrix.json`.
