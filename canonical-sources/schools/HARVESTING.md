# Harvesting real school data (token-free, run locally)

The school indexes in this directory are **curated seeds** with placeholder MSIDs
(`48XXXX`). Real FLDOE Master School IDs and live OCPS resource data are filled in by
running the harvester **on a machine with normal internet** — the Claude Code web
sandbox is behind an allowlist egress policy and cannot reach `ocps.net` / `fldoe.org`.

## One command

```bash
# inside the repo, on your own computer:
python3 tools/local_harvest.py --push
```

That runs three deterministic, **token-free** steps (plain Python, no model calls):

1. `msid_lookup.py --fetch` — download the FLDOE Master School ID file (cached).
2. `msid_lookup.py --match --apply` — stamp real 6-digit MSIDs onto every district's
   `schools.json` (fuzzy name match, threshold-gated — unmatched names are reported,
   never silently wrong).
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
