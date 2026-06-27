# Validation checklist — run before declaring a repair done

Run top to bottom. Anything you cannot run, **say so explicitly** in the approval summary.

1. **Drift guard** — `python3 tools/sync_check.py` exits 0 (synced refs byte-identical; frontmatter +
   resource integrity; every `MAINTAINER.md` present with required sections).
2. **Health re-scan** — `python3 shared/health/health.py --summary`: the targeted finding is resolved and
   no new blocking issue appeared; readiness band did not regress.
3. **References resolve** — every backticked path in the changed `SKILL.md` exists.
4. **Evals** — `evals/evals.json` still parses; a regression case was added for the bug that was fixed.
5. **Scripts** — re-run a representative script (or note it could not be run and why).
6. **Output validity** — if the skill emits artifacts, run `output-validator` on a sample (governance +
   schema + document-structure as applicable).
7. **Metrics** — `python3 tools/metrics.py` if counts changed.
8. **Scope** — diff is limited to what the plan called for; untouched behavior is preserved.

> Honesty rule: a patch is **not complete** if the risky parts could not be validated. Report
> "checks passed / checks not run / remaining watch items" — never imply more confidence than you have.
