# Harvesting real school data (token-free, offline parsing)

## Dependencies — what you actually need

**The reliable workflow (save EDS page → parse `.html` → stamp MSIDs → query) needs NOTHING but
Python 3.8+.** It is pure standard library. No `pip install`, ever.

| If you do this | You need |
|---|---|
| Save the EDS page + `msid_lookup.py` (`.html`) + `schools.py` query | **nothing** (stdlib) |
| Read an `.xlsx` MSID file (only if FLDOE ships one) | `openpyxl` |
| Live `--fetch` / `ocps_resources.py` crawl (FLDOE blocks bots anyway) | `requests`, `beautifulsoup4` |

**If anything dependency-related misbehaves, run the doctor first** (also pure stdlib, always runs):

```bash
python tools/doctor_env.py          # full report + verdict
python tools/doctor_env.py --json   # paste this back to Claude if stuck
```

It finds every Python install on your machine (the common Windows trap is having one under your
user profile AND one in a shared/all-users location), tells you which one runs the tools, whether
`pip` installs into that same one, and the exact fix. **Golden rule when two Pythons exist:** install
with `python -m pip install <pkg>` (binds pip to the python that runs the tools), never bare `pip`.


The school indexes here are **curated seeds**; real FLDOE Master School IDs are stamped in by
parsing the authoritative FLDOE source **offline** with `tools/msid_lookup.py` — no live network,
no model tokens.

## The MSID source is a saved web page, not a download

FLDOE does **not** publish the Master School ID as a file. The authoritative list is an interactive
app — the **Education Data System (EDS)**:

> https://eds.fldoe.org/EDS/MasterSchoolID/Selection.cfm

It renders every Florida school as an HTML list with `DIST`/`SCHL` numbers in the links
(`...Schooldisplay.cfm?DIST=48&SCHL=1401` → MSID `481401`). The reliable workflow:

1. **Open that EDS page in a browser** and **Save it** (`Ctrl+S` → "Webpage, HTML Only").
2. **Parse it offline** — inspect first, then apply:

```bash
# 1. INSPECT (no writes): see detected schools + a match preview like "192/206 would match"
python3 tools/msid_lookup.py --inspect --district 48 --msid-file "C:\path\to\SavedEDSPage.html"

# 2. APPLY: stamp real MSIDs into canonical-sources/schools/ocps/schools.json
python3 tools/msid_lookup.py --match --district 48 --apply --confirm --msid-file "C:\path\to\SavedEDSPage.html"
```

One saved EDS page covers **all 67 districts at once** (it lists all ~7,180 FL schools), so you can
stamp every district from a single file: `--district 48,59,49,35,05,64,53` or omit `--district` for all.

`--msid-file` also accepts `.xlsx`/`.csv` if a future year ships a file. Matching is fuzzy but
threshold-gated: exact normalized-name match first, else Jaccard overlap ≥ `--threshold` (0.65);
anything below stays a placeholder and is reported UNMATCHED — **never fabricated**.

## Optional: the all-in-one local runner

`tools/local_harvest.py` chains the steps for all 7 Central FL districts + writes `HARVEST_REPORT.md`
and (with `--push`) commits the results. Its `--fetch` step is best-effort (FLDOE blocks bots), so
in practice pass the saved EDS page via the per-district `msid_lookup.py` commands above — that path
is the dependable one. The runner's other steps (matching, reporting, push) are token-free:

1. `msid_lookup.py` — stamp real 6-digit MSIDs onto every district's `schools.json`
   (fuzzy name match, threshold-gated — unmatched names reported, never silently wrong).
3. `ocps_resources.py --fetch` — crawl OCPS public pages → `districts/ocps/resources.json`.

Then it writes `HARVEST_REPORT.md` (match rates + gaps) and, with `--push`, commits and
pushes everything to the current branch. **That push is the report-back channel:** the
next Claude session reads the updated JSON + report with zero tokens spent harvesting.

## Options

```bash
python3 tools/local_harvest.py                 # all 7 districts, write report, don't push
python3 tools/local_harvest.py --district 48   # OCPS only
python3 tools/local_harvest.py --no-resources  # MSID matching only, skip the page crawl
python3 tools/local_harvest.py --district 48 --push
```

## What's authoritative

- **School list + MSID + open/closed:** FLDOE Master School ID file.
- **Magnet/choice programs + district resources:** OCPS public pages.
- Every record keeps `source` + `verified`; nothing is marked verified until the harvest
  confirms it against the authority. `human_review_required: true` on programmatic output.

## Individual tools (if you want to run a step by hand)

```bash
python3 tools/msid_lookup.py --fetch
python3 tools/msid_lookup.py --match --district 48              # report match rate (dry-run)
python3 tools/msid_lookup.py --match --district 48 --apply --confirm
python3 tools/ocps_resources.py --fetch                        # then --check to view offline
```
