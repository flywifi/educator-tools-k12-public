# run_ingest.ps1 — local one-click ingester (Windows PowerShell).
#
# 1. Drop ALL your saved source files (saved HTML pages, .xls/.xlsx exports, etc.) into the
#    source_inbox\ folder this creates.
# 2. Run:  .\tools\run_ingest.ps1            (preview: add -DryRun ; auto-push: add -Push)
#
# It parses what it recognizes (NCES PSS, AISF, CPALMS course exports), DEDUPLICATES private
# schools across sources, catalogs EVERY file (parsed or not) at base level in
# canonical-sources\registries\ingested-sources.json (with its URL — so unparsed sources become
# candidate reference/verify seeds for later), and rebuilds the offline index. Pure Python, no tokens.

param([switch]$DryRun, [switch]$Push)
$ErrorActionPreference = "Stop"

# repo root = parent of this script's folder (tools\)
$repo  = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$inbox = Join-Path $repo "source_inbox"
if (-not (Test-Path $inbox)) { New-Item -ItemType Directory -Path $inbox | Out-Null }

# pick a python launcher
$py = (Get-Command python -ErrorAction SilentlyContinue) ?? (Get-Command python3 -ErrorAction SilentlyContinue)
if (-not $py) { Write-Host "Python not found on PATH. Install Python 3.8+ and retry."; exit 1 }

$files = Get-ChildItem $inbox -File
if ($files.Count -eq 0) {
  Write-Host ""
  Write-Host "Inbox is empty. Drop your saved source files into:" -ForegroundColor Yellow
  Write-Host "    $inbox"
  Write-Host "then re-run:  .\tools\run_ingest.ps1"
  exit 0
}

Write-Host "Ingesting $($files.Count) file(s) from $inbox ..." -ForegroundColor Cyan
$args = @("tools/ingest_sources.py", "--inbox", $inbox)
if ($DryRun) { $args += "--dry-run" }
& $py.Source @args

if ($Push -and -not $DryRun) {
  Write-Host "`nCommitting + pushing updated data..." -ForegroundColor Cyan
  git add canonical-sources/schools/private canonical-sources/registries/ingested-sources.json canonical-sources/references/fl-course-codes.json
  git commit -m "data: local source ingest ($(Get-Date -Format yyyy-MM-dd))" 2>$null
  $branch = (git rev-parse --abbrev-ref HEAD).Trim()
  git push -u origin $branch
}

Write-Host "`nDone. Offline index rebuilt. (source_inbox is gitignored — your raw files are not committed.)" -ForegroundColor Green
