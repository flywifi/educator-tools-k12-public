# Arm: `gemini` — Google Gemini (native, no TOS)

The "AI alone" baseline on Google's side: Gemini with its native file upload and canvas/doc tools,
and its Workspace (Docs/Sheets/Slides) reach — **without** any TOS files loaded.

## Run mode
Hosted → manual or subagent. Cannot run headless from this repo.

## Setup (record in `meta.json`)
- A fresh Gemini session with **no TOS files** attached.
- Record the model shown (e.g. the current Gemini model), any Workspace integration used, and date.

## Per-task protocol
1. Paste the task `prompt` verbatim; attach any `input_files`.
2. Save the response as `results/gemini/<task>/output.md`; export any produced Doc/Slides/Sheets or
   file into the same folder (or screenshot if it can't export).
3. Grounding tasks: `cited-codes.txt` with every standard/course code cited.
4. Note any Workspace-native generation (a real Google Doc/Slides) — relevant to axis-5 and to the
   Google-bridge comparison (`shared/office/google_bridge.py`).

## What to watch for
- Gemini's Workspace tie-in is its distinctive generation strength; capture what it actually
  produces as a file.
- Same axis-1/2 separators: standard cited with a recorded version? auditable gated verdict vs
  prose? empty on impossible standards asks vs an invented code?

## Evidence required
`output.md` (+ exported file/screenshot) + `meta.json` + `cited-codes.txt` (grounding tasks), else
the task is `unrun` for `gemini`.
