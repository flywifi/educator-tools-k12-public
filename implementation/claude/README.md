<!-- last_reviewed: 2026-10-03 | owner: claude-maintainer -->
# TOS on Claude — pick your door

Three ways in, depending on how you use Claude. None needs any technical skill.

> **Always true, whichever door you pick:** everything TOS makes is a **draft for
> your review** — you make the final call. Verified data ships for **Florida only**
> today (teachers elsewhere can use every skill; verify standards on your own
> state's site). Never put real student names in — placeholders only.

## Door 1 — "I use Claude Code or the Claude desktop app (Cowork)"

This is the full experience: TOS runs with a complete copy of its verified Florida
data on your computer.

**One-time check — Python 3.10 or newer.** The verified-data tools run on Python. Open
Terminal and type `python3 --version`. If it says 3.10 or higher, you're set. If it says
3.9 (the version built into macOS) or says it isn't found, install a current Python first:
on a Mac, `brew install python` (or the installer from python.org), then reopen Claude.

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

## Door 2 — "I use claude.ai in the browser on a paid plan (Pro/Max/Team) — or Claude for Teachers"

Paid claude.ai chat installs plugins now: **Customize → Plugins → "+" → Add marketplace →**
enter `flywifi/educator-tools-k12-public` → install **Teacher Operating System**. You get every
skill in the browser; the verified-lookup TOOLS still run only where Claude runs on your
computer (Claude Code, the desktop app, or Cowork with the desktop app open) — in the browser
the skills work from their bundled references instead.

**Claude for Teachers** (free for verified US K-12 educators; sign up by June 30, 2027 for a
free year) is "a free Claude for Teams plan" with Claude Code and Cowork, and training is off.
Its published disabled-features list does not include plugins — but nobody has confirmed a
plugin install on a real teacher account yet (UNTESTED-live): if Customize → Plugins isn't
there, use Door 3.

## Door 3 — "I use claude.ai in the browser on the Free plan"

No plugin support, so it works like a Project:

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
(Free plans also get **one** custom remote connector — irrelevant unless someone
hosts the tools server for your school.)

## "Wait — which one is the desktop app?"

Naming, plainly: the Claude **desktop app** now has three tabs — **Chat**, **Cowork**
and **Code** — and **Claude Code** is also a command-line tool. TOS ships as **one plugin
bundle** (`.claude-plugin/` in this repository) that serves all of them: the two `/plugin`
commands work in Claude Code and the Code tab; Chat/Cowork/claude.ai install the same plugin
through **Customize → Plugins**. Plugin skills work in chat everywhere; the local tools server
runs where Claude runs on your computer (Code, Desktop, and Cowork while the desktop app is
open). If you're in a browser tab on the Free plan, you're in Door 3.

## Connect the verified tools (optional, powerful)

Say **"connect my tools"** and your assistant walks you through it — or see
[`implementation/mcp/README.md`](../mcp/README.md). Door 1 plugin users already have them
(the `tos-tools` server ships with the plugin); the Claude desktop app gets a one-click
extension; claude.ai and ChatGPT connect to your school's TOS tools address. The tools let
the assistant *look up* verified Florida standards and *verify* cited codes instead of
recalling them from memory.

## What only works in Door 1

- Reading your documents (PDFs, Word files, scanned handouts) into structured data
- Live update checks against FLDOE/CPALMS sources
- The automated quality-scoring script (Door 2 gets the same quality *rules*,
  applied in prose)

Technical background, if you want it: [`docs/DEPLOYMENT_SURFACES.md`](../../docs/DEPLOYMENT_SURFACES.md).
