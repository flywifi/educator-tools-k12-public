#!/usr/bin/env bash
# run_ingest.sh — local one-click ingester (macOS / Linux).
#
# 1. Drop ALL your saved source files into the source_inbox/ folder this creates.
# 2. Run:  ./tools/run_ingest.sh            (preview: --dry-run ; auto-push: --push)
#
# Parses recognized sources (NCES PSS, AISF, CPALMS course exports), DEDUPLICATES private schools
# across sources, catalogs EVERY file (parsed or not) at base level in
# canonical-sources/registries/ingested-sources.json (with its URL, so unparsed sources become
# candidate reference/verify seeds), and rebuilds the offline index. Pure Python, no tokens.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
INBOX="$REPO/source_inbox"
mkdir -p "$INBOX"

PY="$(command -v python3 || command -v python || true)"
[ -z "$PY" ] && { echo "Python not found on PATH. Install Python 3.8+ and retry."; exit 1; }

DRY=""; PUSH=""
for a in "$@"; do
  [ "$a" = "--dry-run" ] && DRY="--dry-run"
  [ "$a" = "--push" ] && PUSH="1"
done

if [ -z "$(ls -A "$INBOX" 2>/dev/null)" ]; then
  echo
  echo "Inbox is empty. Drop your saved source files into:"
  echo "    $INBOX"
  echo "then re-run:  ./tools/run_ingest.sh"
  exit 0
fi

echo "Ingesting $(ls -1 "$INBOX" | wc -l | tr -d ' ') file(s) from $INBOX ..."
"$PY" tools/ingest_sources.py --inbox "$INBOX" $DRY

if [ -n "$PUSH" ] && [ -z "$DRY" ]; then
  echo; echo "Committing + pushing updated data..."
  git add canonical-sources/schools/private canonical-sources/registries/ingested-sources.json canonical-sources/references/fl-course-codes.json
  git commit -m "data: local source ingest ($(date +%Y-%m-%d))" || true
  git push -u origin "$(git rev-parse --abbrev-ref HEAD)"
fi

echo; echo "Done. Offline index rebuilt. (source_inbox is gitignored — raw files are not committed.)"
