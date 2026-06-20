# Standards resources

This folder holds **catalogs** of external standards/assessment resources the ecosystem draws on —
not the raw documents themselves.

## Why catalogs, not binaries
The goal is to "find the most up-to-date canonical information now and as standards change." Bundling
a large static snapshot of state PDFs/DOCs would (a) bloat the repo and (b) go stale — the opposite
of staying current. So instead each catalog records, per resource: **what it is, the subject/grade,
and the official live source** to pull the newest version from.

- **Live sources are authoritative.** CPALMS (`www.cpalms.org`) for Florida standards; FLDOE
  (`www.fldoe.org`) for assessments/ALDs/rubrics/accommodations; WIDA (`wida.wisc.edu`) for ELD.
- **Snapshots are dated.** e.g., `florida-2025-26.md` is the 2025–26 cycle. Add a new dated catalog
  when a new cycle ships; keep old ones for provenance.

## Catalogs
- `florida-2025-26.md` — Florida B.E.S.T. + NGSSS standards, FAST/B.E.S.T./EOC/FCLE assessment specs,
  ALDs, writing rubrics + anchor sets, accommodations, and WIDA/ELD. Adapter: `../florida-best.md`.

## If you want the raw files in-repo
Keep them out of normal git history (they're large). Options: **git-LFS**, attach them as **GitHub
Release assets**, or store them in a separate data bucket and link from the catalog. The catalog
works the same either way — it points at the canonical source.
