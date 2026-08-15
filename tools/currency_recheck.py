#!/usr/bin/env python3
"""Currency re-verification driver — drift detection over the oldest-verified CPALMS slice.

The full-corpus sweep is COMPLETE (ledger/cpalms-run-manifest.json: verified 6,574 / remaining 0).
This tool exists for what comes after: CPALMS keeps moving, so the oldest `checked_at` entries are
periodically re-verified against the live site. It DETECTS drift; it never acts on it — no
`--apply`, no `--write`, no overlay/corpus mutation, no commit. "Zero drift found" is a successful
deliverable, printed as such.

One run =
  1. preflight   — tools/audit_overlays.py must pass (a red durable record must not be re-verified
                   on top of; that compounds the damage);
  2. re-verify   — the single subject holding the globally oldest in-corpus `checked_at` entries;
                   its N oldest codes (default 200), fetched via cpalms_verify's Phase V with
                   --ignore-overlay (the documented currency-refresh path) — robots.txt, honest
                   UA, politeness delays, and checkpoint/resume are inherited, not reimplemented;
  3. census      — one per-grade reverse-census spot-check of the least-recently-censused scope
                   (from overlay scopes[].generated_at; stateless rotation — applied runs restamp
                   scopes, which advances the choice);
  4. verdict     — drift = fresh state != confirmed (transients excluded); a census whose
                   census_diff is missing or untrusted (_census_problem) is BLOCKED, never zero
                   drift.

Exit codes (tri-state by design — a throttled runner must never masquerade as green or red):
  0  zero drift        1  drift found        2  preflight red / usage        3  environment blocked
     (robots refused, transient fetch failures >10%, or the census could not conclude)

Reports are scratch (RUNBOOK §4a): they land in --workdir (default: a fresh temp dir; NEVER inside
the repo) as recheck-<subject>.report.json, census-<subject>-g<grade>.report.json, summary.md.
Acting on drift routes through RUNBOOK §4a/§5 exactly like a sweep finding — human-gated.

Runs identically in the GitHub workflow (.github/workflows/currency-recheck.yml, manual dispatch)
and on a desktop clone: `python3 tools/currency_recheck.py`. Stdlib only.

Usage:
  python3 tools/currency_recheck.py [--limit 200] [--workdir DIR]
  python3 tools/currency_recheck.py --dry-run-selection   # offline: print the chosen slice
  python3 tools/currency_recheck.py --self-test           # offline fixture probes (CI)
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_overlays                                                   # noqa: E402
import cpalms_verify                                                    # noqa: E402
from cpalms_verify import DATA, OVERLAYS, SUBJECT_FILES, _census_problem  # noqa: E402

TRANSIENTS = {"fetch_failed", "skipped_robots"}
TRANSIENT_RATIO_MAX = 0.10   # strictly-greater-than trips "blocked"


# --------------------------------------------------------------------------------------- selection
def select_slice(overlay_dir: Path, data_dir: Path, n: int) -> tuple[str, list[str]]:
    """The subject owning the globally OLDEST in-corpus checked_at, and its n oldest codes.

    Oldest single entry — not a per-subject average — so the least-recently-verified fact in the
    whole record is always in the next slice. Overlay-only extras (retired, cpalms_addition,
    renumbered sources) are excluded: they have no corpus row to re-verify. Ties break on code,
    so the slice is deterministic. checked_at is Z-form (audit_overlays check 9), which makes
    string order chronological order."""
    best: tuple[str, str] | None = None   # (checked_at, subject)
    per_subject: dict[str, list[tuple[str, str]]] = {}
    for subj in SUBJECT_FILES:
        ov_path = overlay_dir / f"{subj}.cpalms.json"
        corpus_path = data_dir / f"{subj}.json"
        if not ov_path.exists() or not corpus_path.exists():
            continue
        corpus = {e["code"] for e in
                  json.loads(corpus_path.read_text(encoding="utf-8"))["standards"]}
        entries = json.loads(ov_path.read_text(encoding="utf-8")).get("entries", {})
        rows = sorted((e["checked_at"], c) for c, e in entries.items()
                      if c in corpus and e.get("checked_at"))
        if not rows:
            continue
        per_subject[subj] = rows
        if best is None or rows[0][0] < best[0]:
            best = (rows[0][0], subj)
    if best is None:
        raise SystemExit("select_slice: no overlay entries found — nothing to re-verify")
    subj = best[1]
    return subj, [c for _, c in per_subject[subj][:n]]


def select_census(overlay_dir: Path) -> tuple[str, str, str]:
    """(subject, grade, scope_generated_at) of the least-recently-censused scope.

    Stateless rotation: applied runs restamp scopes[].generated_at, which advances this choice on
    its own — no cursor file, no out-of-repo state. Scopes with grades == "all" (ELD) are skipped:
    the search endpoints do not enumerate ELD, so the next-oldest concrete scope is used. Within
    the chosen scope the lexically smallest grade token is taken (deterministic; span tokens like
    912/68 are safe — run_enumerate sweeps each expanded grade separately, the D-H fix)."""
    candidates: list[tuple[str, str, str]] = []   # (generated_at, subject, grades)
    for subj in SUBJECT_FILES:
        ov_path = overlay_dir / f"{subj}.cpalms.json"
        if not ov_path.exists():
            continue
        for scope in json.loads(ov_path.read_text(encoding="utf-8")).get("scopes", []):
            grades, gen = scope.get("grades", ""), scope.get("generated_at", "")
            if not gen or grades == "all":
                continue
            candidates.append((gen, subj, grades))
    if not candidates:
        raise SystemExit("select_census: no censusable scopes found")
    gen, subj, grades = min(candidates)
    grade = min(g.strip() for g in grades.split(",") if g.strip())
    return subj, grade, gen


# ----------------------------------------------------------------------------------------- verdict
def summarize(recheck: dict, census: dict | None) -> dict:
    """Judge one run. Returns {drift: [...], census_drift: [...], blocked: [...], counts: {...}}.

    drift    — rows whose fresh cpalms_state is neither confirmed nor a transient. A transient is
               a fetch outcome, not a fact about the standard, and must never read as drift.
    blocked  — reasons this run cannot conclude: robots refusal, transient ratio > 10%, or a
               census whose census_diff is absent/untrusted (cpalms_verify._census_problem is the
               canonical judge; its absence rule exists because an incomplete census once declared
               every code in scope absent). Blocked is judged BEFORE zero-drift: silence from a
               blocked run is not currency evidence."""
    rows = recheck.get("rows", {})
    drift = sorted((c, r.get("cpalms_state", "?"), (r.get("detail") or "")[:120])
                   for c, r in rows.items()
                   if r.get("cpalms_state") not in TRANSIENTS | {"confirmed"})
    transients = [c for c, r in rows.items() if r.get("cpalms_state") in TRANSIENTS]
    blocked: list[str] = []
    if recheck.get("robots_ok") is False or any(
            r.get("cpalms_state") == "skipped_robots" for r in rows.values()):
        blocked.append("robots.txt refused the run")
    if rows and len(transients) / len(rows) > TRANSIENT_RATIO_MAX:
        blocked.append(f"{len(transients)}/{len(rows)} fetches failed after retries "
                       f"(>{TRANSIENT_RATIO_MAX:.0%}) — environment, not evidence")
    census_drift: list[str] = []
    if census is not None:
        problem = _census_problem(census)
        if problem:
            blocked.append(f"census could not conclude: {problem}")
        else:
            d = census["census_diff"]
            subj = census.get("subject", "")
            known = set()
            ov_path = OVERLAYS / f"{subj}.cpalms.json"
            if ov_path.exists():
                known = set(json.loads(ov_path.read_text(encoding="utf-8")).get("entries", {}))
            census_drift = sorted(
                [f"new-on-cpalms:{c}" for c in d.get("corpus_missing", []) if c not in known]
                + [f"gone-from-cpalms:{c}" for c in d.get("cpalms_absent", [])])
    return {"drift": drift, "census_drift": census_drift, "blocked": blocked,
            "counts": {"rechecked": len(rows),
                       "reconfirmed": sum(1 for r in rows.values()
                                          if r.get("cpalms_state") == "confirmed"),
                       "drifted": len(drift), "transient": len(transients)}}


def verdict_exit(v: dict) -> int:
    """0 zero drift · 1 drift · 3 blocked. Blocked wins: an inconclusive run must not be green."""
    if v["blocked"]:
        return 3
    return 1 if (v["drift"] or v["census_drift"]) else 0


def write_summary(path: Path, subject: str, v: dict, census_target: str) -> None:
    c = v["counts"]
    lines = [f"# Currency re-check — {subject}",
             f"rechecked {c['rechecked']} · re-confirmed {c['reconfirmed']} · "
             f"drifted {c['drifted']} · transient {c['transient']} · census: {census_target}", ""]
    if v["blocked"]:
        lines += ["## BLOCKED — no conclusion drawn"] + [f"- {b}" for b in v["blocked"]]
    elif v["drift"] or v["census_drift"]:
        lines += ["## DRIFT FOUND — human review required (RUNBOOK §4a/§5)"]
        lines += [f"- `{code}` → `{state}` — {detail}" for code, state, detail in v["drift"]]
        lines += [f"- census: {x}" for x in v["census_drift"]]
    else:
        lines += ["## Zero drift found. This is the deliverable."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------------- run
def run(a) -> int:
    print("[preflight] audit_overlays …")
    if audit_overlays.main_audit() != 0:
        print("[abort] preflight red — the durable record is inconsistent; re-verifying on top "
              "of it would compound the damage. Fix the audit findings first.")
        return 2
    subject, codes = select_slice(OVERLAYS, DATA, a.limit)
    c_subj, c_grade, c_gen = select_census(OVERLAYS)
    if a.dry_run_selection:
        print(f"slice: {subject} — {len(codes)} code(s), first {codes[0]} last {codes[-1]}")
        print(f"census target: {c_subj} grade {c_grade} (scope last censused {c_gen})")
        return 0
    work = Path(a.workdir) if a.workdir else Path(tempfile.mkdtemp(prefix="currency-"))
    work.mkdir(parents=True, exist_ok=True)
    recheck_path = work / f"recheck-{subject}.report.json"
    census_path = work / f"census-{c_subj}-g{c_grade}.report.json"

    print(f"[re-verify] {subject}: {len(codes)} oldest code(s) → {recheck_path}")
    cpalms_verify.main(["--subject", subject, "--codes", *codes,
                        "--ignore-overlay", "--resume", "--out", str(recheck_path)])
    print(f"[census] {c_subj} grade {c_grade} → {census_path}")
    # --no-include-practices: a single-grade census can never return K12 practice codes; leaving
    # them in scope makes them show as false cpalms_absent (i.e. fabricated drift) in every run.
    cpalms_verify.main(["--subject", c_subj, "--grades", c_grade, "--enumerate",
                        "--no-include-practices", "--out", str(census_path)])

    recheck = json.loads(recheck_path.read_text(encoding="utf-8"))
    census = (json.loads(census_path.read_text(encoding="utf-8"))
              if census_path.exists() else {"subject": c_subj})
    v = summarize(recheck, census)
    write_summary(work / "summary.md", subject, v, f"{c_subj} g{c_grade}")
    print((work / "summary.md").read_text(encoding="utf-8"))
    print(f"[reports] {work}")
    return verdict_exit(v)


# --------------------------------------------------------------------------------------- self-test
def self_test() -> int:  # noqa: C901
    """Offline probes over synthetic fixtures. Standing rule: every probe is paired with a broken
    twin that must FAIL it — a fixture the check cannot fail on is not evidence."""
    import shutil
    fails = 0

    def check(name: str, ok: bool) -> None:
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    tmp = Path(tempfile.mkdtemp(prefix="currency-st-"))
    ovd, dd = tmp / "overlays", tmp / "data"
    ovd.mkdir(), dd.mkdir()

    def w(d, name, obj):
        (d / name).write_text(json.dumps(obj), encoding="utf-8")

    # Fixture: math holds the single globally oldest entry; ela has the older AVERAGE. A mean-
    # based picker chooses ela; the oldest-single-entry rule must choose math.
    w(dd, "math.json", {"standards": [{"code": f"MA.{i}"} for i in range(6)]})
    w(dd, "ela.json", {"standards": [{"code": f"EL.{i}"} for i in range(3)]})
    w(ovd, "math.cpalms.json", {"entries": {
        "MA.0": {"checked_at": "2026-01-01T00:00:00Z", "state": "confirmed"},
        "MA.1": {"checked_at": "2026-06-01T00:00:00Z", "state": "confirmed"},
        "MA.2": {"checked_at": "2026-06-02T00:00:00Z", "state": "confirmed"},
        "MA.3": {"checked_at": "2026-06-03T00:00:00Z", "state": "confirmed"},
        "MA.RETIRED": {"checked_at": "2025-01-01T00:00:00Z", "state": "retired"},
    }, "scopes": [{"grades": "K,1", "generated_at": "2026-02-01T00:00:00Z"}]})
    w(ovd, "ela.cpalms.json", {"entries": {
        "EL.0": {"checked_at": "2026-02-01T00:00:00Z", "state": "confirmed"},
        "EL.1": {"checked_at": "2026-02-02T00:00:00Z", "state": "confirmed"},
    }, "scopes": [{"grades": "2", "generated_at": "2026-03-01T00:00:00Z"}]})
    w(ovd, "eld.cpalms.json", {"entries": {}, "scopes": [
        {"grades": "all", "generated_at": "2020-01-01T00:00:00Z"}]})
    w(dd, "eld.json", {"standards": []})

    s, codes = select_slice(ovd, dd, 3)
    check("slice: subject = owner of the globally oldest entry (not the oldest mean)",
          s == "math")
    check("slice: oldest-first and capped", codes == ["MA.0", "MA.1", "MA.2"])
    check("slice: overlay-only extras (retired, older than everything) never selected",
          "MA.RETIRED" not in select_slice(ovd, dd, 99)[1])
    s2, codes2 = select_slice(ovd, dd, 3)
    check("slice: deterministic across calls", (s2, codes2) == (s, codes))
    check("slice: every code belongs to the returned subject's corpus",
          all(c.startswith("MA.") for c in codes))

    cs, cg, _ = select_census(ovd)
    check("census: min generated_at wins; ELD 'all' (oldest of all) skipped",
          (cs, cg) == ("math", "1"))  # min token of "K,1" is "1" (lexical; deterministic)

    def rows(states):
        return {"robots_ok": True,
                "rows": {f"C{i}": {"cpalms_state": st, "detail": ""}
                         for i, st in enumerate(states)}}

    good_census = {"subject": "math", "census_diff":
                   {"corpus_missing": [], "cpalms_absent": [], "out_of_scope_in_corpus": []},
                   "census_meta": {"unique_codes": 5}}
    v = summarize(rows(["confirmed"] * 9 + ["statement_differs"]), good_census)
    check("verdict: statement_differs is drift", v["counts"]["drifted"] == 1
          and verdict_exit(v) == 1)
    v = summarize(rows(["confirmed"] * 19 + ["fetch_failed"]), good_census)
    check("verdict: a transient is NOT drift (5% → clean exit 0)",
          v["counts"]["drifted"] == 0 and verdict_exit(v) == 0)
    v = summarize(rows(["confirmed"] * 8 + ["fetch_failed"] * 2), good_census)
    check("verdict: transient ratio 20% → blocked (exit 3), not green, not red",
          verdict_exit(v) == 3)
    v = summarize(rows(["confirmed"] * 10), good_census)
    check("verdict: exactly 10% is NOT blocked (strictly-greater rule)",
          verdict_exit(summarize(rows(["confirmed"] * 9 + ["fetch_failed"]),
                                 good_census)) == 0 and verdict_exit(v) == 0)
    v = summarize(rows(["confirmed"] * 5), {"subject": "math"})   # census_diff MISSING
    check("verdict: a census without census_diff is BLOCKED — never zero drift (D-H rule)",
          verdict_exit(v) == 3 and any("census" in b for b in v["blocked"]))
    v = summarize({"robots_ok": False, "rows": {}}, good_census)
    check("verdict: robots refusal is blocked", verdict_exit(v) == 3)
    v = summarize(rows(["confirmed"] * 5), None)
    check("verdict: clean run, no census requested → zero drift exit 0", verdict_exit(v) == 0)

    d1 = select_slice(ovd, dd, 3)
    d2 = select_slice(ovd, dd, 3)
    check("dry-run determinism: two selections byte-identical", repr(d1) == repr(d2))

    shutil.rmtree(tmp)
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--limit", type=int, default=200, help="slice size (oldest codes)")
    ap.add_argument("--workdir", help="report directory OUTSIDE the repo (default: fresh temp)")
    ap.add_argument("--dry-run-selection", action="store_true",
                    help="print the chosen slice + census target; fetch nothing")
    ap.add_argument("--self-test", action="store_true", help="offline fixture probes")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    return run(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
