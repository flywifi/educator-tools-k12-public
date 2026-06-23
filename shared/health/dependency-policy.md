# Dependency & capability policy (canonical)

TOS is **stdlib-by-default**; optional dependencies are **capability-gated extras** that only earn their
place when they beat baseline Claude (fidelity, real artifacts, or a new modality). Manifest:
`tools/dependencies.json`. Preflight: `shared/health/capabilities.py` (`health.py --capabilities`).

## Tiers
- **builtin** — Python stdlib; always on.
- **local_optional** — a local library/binary/font; **activates when installed**, reports an honest gap
  when not (Parser/OcrEngine/Transcriber registries). No secrets, no network. *On by default if present.*
  Examples: PyMuPDF/pdfplumber (PDF), Tesseract (OCR), python-pptx/docx/openpyxl (Office authoring),
  LibreOffice+poppler (render/convert), faster-whisper+ffmpeg (transcription), fonts.
- **cloud_optional** — an external SaaS API (Azure, fal, Nutrient, Firecrawl). **OFF by default.**
  Enabled only when a deployment **opts in** AND an **API key is present in the environment**. May send
  data off-site, so it is bound by the privacy rules below.

## The "better than baseline" test
A dependency is added only if it does something the chat model cannot do well unaided: open a 200-page
scanned PDF with tables, produce a real editable `.pptx`, transcribe an audio file, render a slide to an
image for QA, or read every script/font. If baseline Claude already does it, we don't add a dep.

## Secrets (cloud tier)
- API keys come from the **environment only** (e.g. `AZURE_SPEECH_KEY`, `FAL_KEY`, `NUTRIENT_API_KEY`,
  `FIRECRAWL_API_KEY`). **Never** commit a key; `*.env`/secrets files are git-ignored. The preflight
  reports only whether a key is *configured* (boolean) — never its value.
- Default off. A deployment turns a provider on via `cloud_providers` in its feature-flags file.

## Privacy boundary (cloud tier) — non-negotiable
Cloud doc/image/voice APIs can exfiltrate student **PII/ePHI**. The cloud tier is therefore:
- governed by `shared/students/student-data-policy.md` (minimum-necessary; never send more than needed);
- subject to the **connector restriction model** — a district can deny a provider, or restrict which
  evidence may be sent (`restricted_evidence` + reason); high `privacy_sensitivity`;
- always `human_review_required`. When in doubt, prefer a **local_optional** path over cloud.

## Supply chain — "auto-updated AND scanned"
- **Pin** per-capability requirements (`tools/requirements-{docintel,scraper,office,media,cloud}.txt`).
- **Auto-update** via `.github/dependabot.yml` (weekly PRs for pip + GitHub Actions).
- **Scan** every PR via `tools/security_scan.py` in CI — `pip-audit` (known CVEs in the pins) + `bandit`
  (unsafe/malicious code patterns); the job fails on findings, so a risky bump can't merge.
- **Select for provenance** — prefer well-maintained, widely-used libraries.

## Fonts (read all documents)
Install Google **Noto** (core + CJK + color-emoji) for full Unicode coverage, plus the OSS
**metric-compatible** MS substitutes **Liberation** (Arial/Times/Courier), **Carlito** (Calibri), and
**Caladea** (Cambria) — the real MS core fonts are proprietary. The preflight reports font coverage per
script and flags a gap ("this doc uses Calibri/CJK we don't have; glyphs may substitute") instead of
silently rendering tofu.

## Per-deployment flags
In the connector feature-flags file:
- `optional_deps`: `{ "<capability>": "allow" | "deny" }` — a district can forbid a local capability.
- `cloud_providers`: `{ "<provider>": "available" | "disabled" | "not_installed" }` — opt in to a cloud
  provider (default `not_installed`); reuses the connector state vocabulary.
