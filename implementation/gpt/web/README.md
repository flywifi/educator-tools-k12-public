# TOS on ChatGPT (web)

**One file. Drag and drop.**

1. Download `TOS-skills.md` from this folder.
2. In ChatGPT, create a Project (or open an existing one).
3. Add `TOS-skills.md` as a project file — ChatGPT will reference it in every chat.
4. Ask for what you need: "Write me a lesson plan for 4th grade math on fractions."

That's it. See the top of `TOS-skills.md` for an honest description of what works on
ChatGPT and what requires the full Claude TOS deployment.

## Save your profile (one-time, 2 minutes)

1. In your Project, say **"set up my profile"** and answer the short interview
   (grade, subject, school — placeholders only, never real student names).
2. The assistant gives you back one file called `my-teacher-profile.md` — save it.
3. Add it to the same Project. From now on, every chat starts already knowing your
   grade, subject, and school. To change it later, say "update my profile" and
   replace the file.

---

`TOS-skills.md` is generated automatically from the YAML source files in
`implementation/gpt/api/skills/`. To regenerate after a skill update:

```bash
python3 tools/export_chatgpt.py
```
