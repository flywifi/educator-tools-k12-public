<!-- last_reviewed: 2026-07-15 | owner: web-maintainer -->
# TOS on ChatGPT (web)

**One file. Drag and drop.**

1. Download `TOS-skills.md` from this folder.
2. In ChatGPT, create a Project (or open an existing one).
3. Add `TOS-skills.md` as a project file — ChatGPT will reference it in every chat.
4. Ask for what you need: "Write me a lesson plan for 4th grade math on fractions."

That's it. See the top of `TOS-skills.md` for an honest description of what works on
ChatGPT and what requires the full Claude TOS deployment.

## Level up: the Reference Pack (recommended)

The pack is the actual Florida data — all 6,583 state standards with their full
text, the course-code directory, the 67 districts, and the school-type rules — so
answers quote the real, verified data instead of the model's memory.

**Pick the download that fits your ChatGPT plan** (Projects hold a limited number
of files — as of 2026-07 roughly: Free ~5, Plus ~20-25, Pro ~40; these change, so
trust what the upload screen tells you):

- **On ChatGPT Free — or if you just want the simplest path:** one file,
  [`reference-pack/tos-reference-pack-onefile.json`](reference-pack/tos-reference-pack-onefile.json).
  Same data in a single upload; with this guide and your profile you use only 3 slots.
- **On Plus/Pro:** [`reference-pack/reference-pack.zip`](reference-pack/reference-pack.zip)
  — one download, then unzip and add the 11 files. Separate files give the
  assistant sharper file search, so this is the better experience when your plan
  allows it.

**How to download a file from this site (GitHub):** click the file's name, then
the **Download** icon near the top-right of the file view (or right-click **Raw**
→ "Save link as…"). The zip downloads directly.

Every pack file's origin and how to double-check it is in
[`reference-pack/MANIFEST.md`](reference-pack/MANIFEST.md). Verified data ships for
**Florida only** today — teachers in other states can use every skill, but should
verify standards against their own state's site.

## Save your profile (one-time, 2 minutes)

1. In your Project, say **"set up my profile"**. The built-in Setup Wizard takes over:
   one question at a time, each with the reason it's asked, everything skippable
   (grade, subject, school — placeholders only, never real student names).
2. At the end the assistant writes your complete profile into one block of text
   titled `my-teacher-profile.md` — and helps you save it: it will offer a
   downloadable file when it can, or walk you through copy → Notepad/TextEdit →
   save as `my-teacher-profile.md`. *(On Windows Notepad, set "Save as type" to
   **All Files** first, or it saves `my-teacher-profile.md.txt`. A BOM/line-ending
   quirk is fine — the tools handle it.)*
3. Add that file to the same Project. Why a file? Chats don't remember each other —
   the Project's files are the assistant's only memory of you. From now on, every
   chat starts already knowing your grade, subject, and school. To change it later,
   say "update my profile" and replace the file.

## Switching devices, or using the ChatGPT desktop app

Nothing to redo. Projects live in your ChatGPT **account**, not on one device —
install the desktop app (or open ChatGPT on any computer), sign in with the same
account, and your TOS Project is already there with all its files, your profile,
and your chats. Same plan limits apply. If something looks missing, first check
you're signed into the same account.

One thing you do **not** need: building a "Custom GPT". TOS on ChatGPT is just
Project files — this guide plus the pack. (The `implementation/gpt/api/` folder in
the project repository is for software developers, not for teachers.)

## A note on privacy

On personal ChatGPT plans, your conversations may be used to help train models
unless you turn that off (Settings → **Data Controls** → "Improve the model for
everyone" — as of 2026; the menu wording changes occasionally). School/enterprise
workspaces (Team/Edu) don't train on your content by default. This is also why the
Setup Wizard never accepts real student names: everything about students stays a
placeholder, so there is nothing private to protect.

## Your requirements map

With the profile and pack in place, say **"build my requirements map"**: one table
with every standard for your grade and subject (full text), your course codes, your
district, and your school type's rules — each row citing the pack file it came from
and the official site to verify it on. It's a draft for your review, always.

## Want everything?

The full TOS experience — document parsing, live update checks, quality scoring —
runs on the Claude side with a complete copy of the repository on your computer.
Start at [`implementation/claude/README.md`](../../claude/README.md).

---

`TOS-skills.md` is generated from the YAML sources in `implementation/gpt/api/skills/`;
the `reference-pack/` folder is generated from the repository's canonical data.
To regenerate after an update:

```bash
python3 tools/export_chatgpt.py
python3 tools/export_reference_pack.py
```
