<!-- last_reviewed: 2026-07-11 | owner: claude-maintainer -->
# TOS on Claude — pick your door

Two ways in, depending on how you use Claude. Neither needs any technical skill.

> **Always true, whichever door you pick:** everything TOS makes is a **draft for
> your review** — you make the final call. Verified data ships for **Florida only**
> today (teachers elsewhere can use every skill; verify standards on your own
> state's site). Never put real student names in — placeholders only.

## Door 1 — "I use Claude Code or the Claude desktop app (Cowork)"

This is the full experience: TOS runs with a complete copy of its verified Florida
data on your computer.

Type three things, in order:

1. `/plugin marketplace add flywifi/educator-tools-k12-public`
2. `/plugin install teacher-operating-system@tos-marketplace`
3. **"set up my profile"**

That third one starts the setup wizard — a short, friendly interview (about 7
questions: who you are, your school, your roles, what you hand off to whom, your
meetings, your preferences). Skip anything. Your answers stay in a private file on
your computer that is never shared or published.

Then just ask for work in plain language: *"make me a 5th-grade fractions lesson"*,
*"draft a family letter about the field trip"*, *"turn this lesson into slides."*

**After setup, say "build my requirements map."** You'll get one table with every
standard for your grade and subject (full text, checked against the built-in
verified Florida data), your course codes, your district, and the rules for your
kind of school — each row citing its source and the official site to verify it on.
It's a draft for your review, always.

## Door 2 — "I use claude.ai in the browser"

No files live on your computer, so it works like a Project:

1. Create a Project on claude.ai.
2. Add `implementation/gpt/web/TOS-skills.md` **and the Reference Pack** as Project
   files — either the files in `implementation/gpt/web/reference-pack/` (sharper
   file search) or, for the fewest uploads, the single
   `reference-pack/tos-reference-pack-onefile.json`. (The pack is plain data — the
   same verified Florida standards, course codes, districts, and school types the
   full deployment uses. Origins and verification links: `reference-pack/MANIFEST.md`.)
3. Say **"set up my profile"**, answer the short interview, and save the
   `my-teacher-profile.md` file the assistant gives you back into the Project.

Same flow as the ChatGPT version — the step-by-step lives in
[`implementation/gpt/web/README.md`](../gpt/web/README.md). TOS itself stores
nothing in the browser: your profile lives in your Project, under your control.

## "Wait — which one is the desktop app?"

Naming, plainly: **Claude Code** is the command-line/IDE tool; **Cowork** is the
Claude desktop app. TOS ships as **one plugin bundle** (`.claude-plugin/` in this
repository) that serves both — the same two `/plugin` commands above work in
either. If you can open a folder of files with it, you're in Door 1; if you're in
a browser tab, you're in Door 2.

## What only works in Door 1

- Reading your documents (PDFs, Word files, scanned handouts) into structured data
- Live update checks against FLDOE/CPALMS sources
- The automated quality-scoring script (Door 2 gets the same quality *rules*,
  applied in prose)

Technical background, if you want it: [`docs/DEPLOYMENT_SURFACES.md`](../../docs/DEPLOYMENT_SURFACES.md).
