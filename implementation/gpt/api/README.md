# TOS on OpenAI API (developer use)

This folder contains OpenAI function calling definitions for all 29 TOS skills.
It is intended for **developers** building applications with the OpenAI API.

**If you are a teacher using ChatGPT on the website** → see `implementation/gpt/web/` instead.
Drag `implementation/gpt/web/TOS-skills.md` into a ChatGPT Project and you're done.

---

## API usage

```python
import json, openai

tools = json.load(open("implementation/gpt/api/tools.json"))
system_prompt = open("implementation/gpt/api/system-prompt.md").read()

client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    tools=tools,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Write me a lesson plan for 4th grade math on fractions."}
    ]
)
```

## Files

| File | Purpose |
|---|---|
| `skills/*.yaml` | One function definition per TOS skill (source of truth) |
| `tools.yaml` | Combined tools array (YAML) |
| `tools.json` | Combined tools array (JSON) — pass directly to the API |
| `system-prompt.md` | Teacher-core routing logic as a system prompt |

## Regenerating after a skill change

```bash
python3 tools/export_openai.py    # rebuilds tools.yaml + tools.json
python3 tools/export_chatgpt.py   # also rebuild the ChatGPT web version
```
