# Competitive landscape — document tooling (dated observations)

**What this is:** a dated snapshot of what the comparison arms in `benchmarks/` can do for
document work, so the benchmark measures against reality instead of assumptions. **Every claim here
is an observation "as of" a date, not a permanent fact** — these products change fast. Re-verify
before citing. Sources are linked inline with an accessed date; this doc is not scanned by the
code-URL provenance guard (`tools/url-provenance.json`), which by design covers only URLs hardcoded
in `tools/*.py` / `shared/**/*.py`.

_Snapshot date: 2026-07-15._

## Native AI assistants (the "AI alone" arms)

| Capability (as of 2026-07) | Claude | ChatGPT | Gemini |
|---|---|---|---|
| Per-file upload size | ~500 MB | ~512 MB | ~100 MB |
| Files per chat / project | ~20/chat | ~10/chat, Project persistence | ~10/chat |
| Reads uploaded files | multimodal PDF < 100 pp (charts/graphics read, not just OCR); text-only for very large | **Advanced Data Analysis = real Python sandbox** that can exhaustively read an uploaded file | native file read + Workspace reach |
| Generates documents | artifacts; exports | Canvas (rewrite length/reading-level, export PDF) | Workspace-native Docs/Slides/Sheets |
| Standards grounding | model memory only (no verified corpus) | model memory only | model memory only |
| Auditable gated decision | none native | none native | none native |

Sources (accessed 2026-07-15): file-limit + capability comparisons —
datastudios.org "ChatGPT vs Claude for File Upload"; onefileapp.com "AI File Upload Limits Compared (2026)";
Anthropic support "What kinds of documents can I upload to Claude"; Zapier "Claude vs ChatGPT (2026)".

**The load-bearing gap for all three:** standards come from the model's memory, so a cited code can
be plausible-but-wrong, and there is no recorded, deterministic verdict. This is exactly the axis-1
(grounding) and axis-2 (governance) territory where TOS resolves codes against a committed corpus
(returning *empty* rather than inventing) and emits an auditable `score.py` decision. ChatGPT's
Python sandbox is the one native path that can *actually* read a file exhaustively — relevant to the
completeness/enumeration comparison and captured in the `chatgpt` arm.

## Dedicated open-source parsers (Phase B, ingestion axis)

| Engine | Strength (as of 2026) | Notes |
|---|---|---|
| **Docling** (IBM DS4SD) | ~97.9% complex-table accuracy in one sustainability-report benchmark; DocLayNet layout + TableFormer | strongest reported table extraction |
| **Marker** | PDF → clean Markdown/JSON, layout detection | RAG-oriented |
| **Unstructured** | multi-format enterprise extraction + OCR + NLP | broad format coverage |
| **Public leaderboards** | one evaluated 21 parsers over 100 synthetic pages / 451 tables | significant spread between tools |

Sources (accessed 2026-07-15): procycons.com "PDF Data Extraction Benchmark" (Docling/Unstructured/
LlamaParse); ertas.ai "PDF Parsing Accuracy Benchmark"; firecrawl.dev "Best PDF Parsers 2026";
arxiv 2603.18652 "Benchmarking PDF Parsers on Table Extraction."

**Honest read for TOS:** `shared/docintel/` is stdlib-first with OCR and advanced tables *staged*;
it will not out-parse Docling/Marker on raw PDF tables today. Its measurable edge is **honesty** —
`retrieval_state` (visibility ≠ extraction) and explicit `capability_gaps` instead of silent drops —
and **governance/provenance** wrapping. Phase B tests parity + that honesty edge, and informs the
wrap-vs-build decision (register a best-in-class engine as a `docintel` parser tier).

## Consumer education-AI tools (generation arm)

Tools a teacher actually compares TOS to — MagicSchool, Diffit, SchoolAI, Khanmigo, and a long tail
of "AI lesson plan generator" sites. Common advertised features (as of 2026): standards alignment to
CCSS/NGSS/state codes, tiered/ELL/IEP differentiation, one-click lesson/quiz generation.

Sources (accessed 2026-07-15): creolestudios.com "Top AI Lesson Plan Generators 2026";
schoolai.com; edusageai.com; github topics `lesson-plans` / `ai-in-education`.

**What the benchmark must actually measure (not assume):** whether an attached standard code
*exists and matches* the grade/subject (many tools label plausibly without a verified corpus), and
whether any recorded/auditable verdict exists. These are TOS's hypothesized differentiators — the
`ed_tools` arm tests them with evidence, and records honestly where a consumer tool wins on polish
or breadth.

## Evaluation methodology we borrow (for fairness)

The blind, multi-run, evidence-quoted judging in `benchmarks/README.md` follows RAG-evaluation
practice — **faithfulness/groundedness** scoring (is every claim supported by the cited source?)
from RAGAS / DeepEval / LLM-as-judge literature (accessed 2026-07-15: futureagi.com "RAG Evaluation
Metrics 2026"; arxiv 2505.04847 "Benchmarking LLM Faithfulness in RAG"). Axis-1's fabricated-
citation rate is a domain-specific groundedness metric: instead of an LLM judging support, we
resolve every cited standard code against the committed corpus — a harder, non-judgmental check.
