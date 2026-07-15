# Arm: `oss_parsers` — dedicated open-source document parsers (ingestion track)

For the **ingestion/parsing axis (7)** only. These are the best-in-class engines TOS's `docintel`
is measured against — not to claim supremacy over, but to reach parity and add an honesty edge.

Candidates (with the public numbers gathered in `docs/COMPETITIVE_LANDSCAPE.md`):
- **Docling** (IBM DS4SD; DocLayNet layout + TableFormer tables) — strong table extraction.
- **Marker** — PDF → clean Markdown/JSON, layout detection, RAG-oriented.
- **Unstructured** — multi-format enterprise extraction + OCR.

## Run mode
**Scriptable if installed.** Unlike the hosted arms, these can run headless in a venv — so their
results can be reproduced, not just cited. If not installed in the benchmark environment, the arm
falls back to **public-leaderboard citation** (with the source URL + date in `meta.json`), which is
weaker evidence and must be labeled as such.

## Per-corpus-doc protocol
1. Run each engine and TOS `docintel` on the same `benchmarks/corpus/` document.
2. Score: text-recovery, table-fidelity (TEDS / GriTS), i18n-preservation (do foreign characters
   survive?), container recursion (are nested/embedded docs found?).
3. **Honesty metric (the docintel differentiator):** for each doc, does the engine report what it
   could NOT recover (a capability gap / low-confidence flag), or does it silently drop or
   hallucinate content? docintel's `retrieval_state` + `capability_gaps` make this explicit; score
   whether each competitor does the same.

## The wrap-vs-build decision this arm informs
If a dedicated engine wins raw extraction (expected on PDF tables), the honest move is to register
it as a `docintel` parser tier — the registry already selects by capability
(`shared/docintel/orchestration.py`), so TOS can *compose* best-in-class parsing under its
provenance/governance layer. Record the decision with the measured numbers; don't presume it.

## Evidence required
The engine's actual output file per corpus doc (scriptable runs) OR a cited leaderboard row with
source URL + date (fallback), plus `meta.json` with engine version. No evidence → `unrun`.
