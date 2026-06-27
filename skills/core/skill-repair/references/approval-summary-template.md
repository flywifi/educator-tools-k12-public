# Approval summary template — plain language, for a human to approve

Use this exact shape so a non-technical maintainer can approve confidently. Plain language first.

```
## Proposed changes summary
<one-paragraph, non-technical overview of what is wrong and what the fix does>

### Intended edits
- <file>: <what changes and why>           (mechanical | judgment)
- ...

### Intentionally unchanged
- <what is preserved — purpose, voice, triggering, untouched files>

### Validation plan
- <which checks will run; which cannot run here and why>

## Validation results        (after --apply)
- checks passed: <list>
- checks not run: <list + why>
- remaining watch items: <risks / follow-ups>

## Finalization status
- waiting for approval | safe fixes applied (N judgment items remain) | finalized
- archive/version updated: yes | no | not possible in this environment
```

Rules: lead with the plain-language overview; mark every edit mechanical vs judgment; never claim a check
ran if it didn't; stop at "waiting for approval" until the human says go.
