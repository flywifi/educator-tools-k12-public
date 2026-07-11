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
answers quote the real, verified snapshot instead of the model's memory.

1. Download the 11 files in [`reference-pack/`](reference-pack/) from this folder.
2. Add them to the same Project.
3. Done. The pack uses 11 of your ~20 Project file slots; `TOS-skills.md` and your
   profile use 2 more — the rest are yours.

Every pack file's origin and how to double-check it is in
[`reference-pack/MANIFEST.md`](reference-pack/MANIFEST.md). Verified data ships for
**Florida only** today — teachers in other states can use every skill, but should
verify standards against their own state's site.

## Save your profile (one-time, 2 minutes)

1. In your Project, say **"set up my profile"** and answer the short interview
   (grade, subject, school — placeholders only, never real student names).
2. The assistant gives you back one file called `my-teacher-profile.md` — save it.
3. Add it to the same Project. From now on, every chat starts already knowing your
   grade, subject, and school. To change it later, say "update my profile" and
   replace the file.

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
