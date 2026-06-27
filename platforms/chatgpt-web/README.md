# TOS on ChatGPT (web)

**One file. Drag and drop.**

1. Download `TOS-skills.md` from this folder.
2. In ChatGPT, create a Project (or open an existing one).
3. Add `TOS-skills.md` as a project file — ChatGPT will reference it in every chat.
4. Ask for what you need: "Write me a lesson plan for 4th grade math on fractions."

That's it. See the top of `TOS-skills.md` for an honest description of what works on
ChatGPT and what requires the full Claude TOS deployment.

---

`TOS-skills.md` is generated automatically from the YAML source files in
`platforms/openai/skills/`. To regenerate after a skill update:

```bash
python3 tools/export_chatgpt.py
```
