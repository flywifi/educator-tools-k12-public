# Arm: `ed_tools` — consumer education-AI tools

The tools a teacher would realistically compare TOS against for lesson/assessment generation —
e.g. MagicSchool, Diffit, SchoolAI, Khanmigo. These are the "market" arm: purpose-built for
educators, standards-alignment features advertised.

## Run mode
Hosted → manual or subagent. Cannot run headless from this repo. Each product is a **sub-arm** —
name the specific product and version in `meta.json` (`arm_version: "MagicSchool 2026-07"`), and
keep one results folder per product where it matters
(`results/ed_tools/<task>/<product>/`).

## Per-task protocol
1. Use the product's closest matching generator (lesson planner, quiz/assessment maker,
   differentiation tool) with the task's `prompt`/intent.
2. Save the output as `output.md` (or export the file / screenshot the result).
3. Grounding tasks: `cited-codes.txt` with every standard code the tool attaches. Resolve them the
   same way — a consumer tool that *labels* a lesson with a standard is making a grounding claim
   the objective grader will check against `tools/offline_index.py`.

## What to watch for (the honest differentiators to measure, not assume)
- **Grounding:** do the attached standard codes actually exist and match the grade/subject, or are
  they plausible-looking labels? This is the axis-1 heart of the comparison.
- **Governance/auditability:** do these tools emit any recorded, gated decision or a verify-on-the-
  authority flag, or do they present output as finished? (Axis 2.)
- **Differentiation:** many advertise tiered/ELL/IEP output — capture whether the tiers are correct
  and standards-tied (axis 4), not just present.
- **Do NOT overclaim the reverse:** these tools may beat TOS on polish, UI, or breadth. Record
  losses honestly — a loss becomes a new eval case (the durable loop), not a number to bury.

## Evidence required
`output.md` (+ file/screenshot) + `meta.json` naming the product+version + `cited-codes.txt`
(grounding tasks), else the task is `unrun` for that product.
