# Arm: `chatgpt` — ChatGPT (native, no TOS)

The "AI alone" baseline on OpenAI's side: ChatGPT with Projects, the Advanced Data Analysis (Python
sandbox) tool, and Canvas — **without** the TOS `TOS-skills.md` or Reference Pack loaded.

## Run mode
Hosted → manual or subagent. Cannot run headless from this repo.

## Setup (record in `meta.json`)
- A Project or chat with **no TOS files** attached (a separate run of this arm WITH the Reference
  Pack is a distinct, later comparison — keep them apart and label clearly).
- Record the model shown (e.g. the current GPT model), plan tier, and date.

## Per-task protocol
1. Paste the task `prompt` verbatim; attach any `input_files`.
2. Save the response as `results/chatgpt/<task>/output.md`; export any produced file (Canvas doc,
   generated .pptx/.docx) into the same folder.
3. Grounding tasks: `cited-codes.txt` with every standard/course code cited.
4. If the run uses the Python sandbox to read an uploaded file, note that in `meta.json` — it is
   the one native path that can *actually read* a file exhaustively (relevant to the
   completeness/enumeration comparison), and its use should be recorded, not hidden.

## What to watch for
- The Python sandbox is a genuine strength for exact file reads — capture whether it was available
  and used.
- Axis-1/2 separators are the same as for `claude`: version recorded with a cited standard? an
  auditable gated verdict, or prose only? empty on impossible asks, or an invented code?
- Canvas/exported documents feed axis-5; validate any real binary with `tools/validate_document.py`.

## Evidence required
`output.md` (+ exported file/screenshot) + `meta.json` + `cited-codes.txt` (grounding tasks), else
the task is `unrun` for `chatgpt`.
