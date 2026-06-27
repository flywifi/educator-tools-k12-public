# shared/feeds/snapshot/ — the git-shareable feed pack (L7/L8 hand-off)

This directory carries the **portable snapshot** of harvested feed items that moves data from an
open-net **writer** to the egress-blocked TOS **reader** (the OpenCLAW/`crawlkit` model).

- **Writer** (where the internet is open, after `tools/feeds_update.py --update`):
  `python3 tools/feeds_publish.py` writes `feed_items.jsonl` (one row per line, deterministic order)
  and `manifest.json` (row count + sha256 fingerprint), then **commit this directory to git**.
- **Reader** (this repo, offline): `python3 tools/feeds_import.py` verifies the fingerprint and imports
  the rows into the local `feed_items.local.db` with `INSERT OR IGNORE` (dedupe by content hash —
  idempotent). An unchanged snapshot is a no-op; a sha mismatch is refused, never imported.

The pack files (`feed_items.jsonl`, `manifest.json`) are produced by a real publish on an open-net
machine and committed there. Only public feed metadata travels here — never student data. Reads remain
fully offline; no live network is used on the reader.
