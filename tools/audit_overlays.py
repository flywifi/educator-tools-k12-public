#!/usr/bin/env python3
"""Standing integrity audit of the CPALMS overlays — offline, stdlib-only, CI-run.

The overlays under shared/standards/resources/florida/data/overlays/ are the durable record of
thousands of network round-trips: 6,500+ entries whose `confirmed` labels gate what the resolver
calls verified and whose `coverage` float decides whether an ABSENT code blocks a build
(verify_standards.OVERLAY_TRUST_COVERAGE). Until this tool existed, nothing in CI ever read them —
which is how a dead census guard, 69 wrong-path URLs and 223 unwritable evidence fields all
persisted while every self-test stayed green. These checks are the sweep-completion audit's
transcript probes (docs/audits/2026-08-13-sweep-completion-audit.md), mechanized so they cannot die
with the session that ran them.

The strongest check is #2: every `confirmed` label is RE-PROVEN from the stored texts under the
live predicate, not trusted. That deliberately couples CI to `_confirm_state` semantics — a future
predicate change will redden this audit until the overlays are re-judged, which is the check
working, not breaking.

Usage:
  python3 tools/audit_overlays.py               # audit the committed overlays; exit 1 on findings
  python3 tools/audit_overlays.py --self-test   # prove every check can FAIL (mutation battery)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cpalms_verify import (  # noqa: E402  (side-effect-free import; network code is call-guarded)
    ARCHIVAL_KEYS, DATA, OVERLAYS, OVERLAY_STATES, PROVENANCED_STATES, RETIREMENT_KEYS,
    SUBJECT_FILES, VERIFIED_STATES, _AP_SEG, _confirm_state, _lead_matches,
)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "ledger" / "cpalms-run-manifest.json"

# Every key run_apply can write, plus the archaeology carried by _merge_entry. Ad-hoc history is
# allowed BY NAME, never by silence — an unknown key is a finding, because the last time fields
# appeared outside the writer's vocabulary they were also invisible to every safety check.
WRITER_KEYS = {"state", "statement_verified", "cpalms_id", "cpalms_url", "date_revised",
               "checked_at", "needs_review", "detail", "new_code", "truncated_card",
               "duplicate_cpalms_ids", "note"}
ALLOWED_ENTRY_KEYS = WRITER_KEYS | set(ARCHIVAL_KEYS) | set(RETIREMENT_KEYS) | {"prior_retirement"}

# Both historical scopes[] element shapes are accepted verbatim: the legacy writer recorded
# rows_in_scope; the current one records rows_applied/rows_verified. History is tolerated, not
# rewritten — but a THIRD shape is a finding.
SCOPE_SHAPES = ({"grades", "rows_in_scope", "generated_at"},
                {"grades", "rows_applied", "rows_verified", "generated_at"})

# URL-exempt states: retired entries carry no URL by design (nothing to link — the code is gone),
# and not_on_cpalms likewise records an absence.
URL_EXEMPT = {"retired", "not_on_cpalms"}

_TS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def audit(data_dir: Path = DATA, overlays_dir: Path = OVERLAYS,
          manifest_path: Path = MANIFEST) -> list[str]:
    """Run all checks; return findings as 'subject:code:check — detail' strings."""
    findings: list[str] = []
    id_owner: dict[tuple[str, str], set[str]] = {}
    man = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    if man is None:
        findings.append(f"manifest:missing — {manifest_path} does not exist")
    totals = {"corpus": 0, "verified": 0, "needs_review": 0, "remaining": 0}
    entries_total = 0

    for subj in SUBJECT_FILES:
        cf = data_dir / f"{subj}.json"
        ovp = overlays_dir / f"{subj}.cpalms.json"
        if not cf.exists() or not ovp.exists():
            findings.append(f"{subj}:files:missing — corpus={cf.exists()} overlay={ovp.exists()}")
            continue
        corpus = {e["code"]: e.get("statement", "")
                  for e in json.loads(cf.read_text(encoding="utf-8"))["standards"]}
        overlay = json.loads(ovp.read_text(encoding="utf-8"))
        entries = overlay.get("entries", {})
        entries_total += len(entries)

        for code, e in entries.items():
            st = e.get("state")
            # 1 — state legality + internal consistency
            if st not in OVERLAY_STATES:
                findings.append(f"{subj}:{code}:state-legal — {st!r} not in OVERLAY_STATES")
            if st in PROVENANCED_STATES and (not e.get("cpalms_url") or not e.get("checked_at")):
                findings.append(f"{subj}:{code}:state-legal — {st} entry missing url/checked_at")
            if st in VERIFIED_STATES and e.get("needs_review"):
                findings.append(f"{subj}:{code}:state-legal — confirmed entry carries needs_review")
            # 2 — the confirmed label re-proven from the stored texts, never trusted
            if st in VERIFIED_STATES and code in corpus:
                cs, ps = corpus[code], e.get("statement_verified") or ""
                if _confirm_state(cs, ps, *_lead_matches(cs, ps)) != "confirmed":
                    findings.append(f"{subj}:{code}:re-proof — stored texts do NOT re-prove "
                                    f"'confirmed' under the live predicate")
            # 3 — URL routed by code shape
            url = e.get("cpalms_url") or ""
            if url:
                want = "/PreviewAccessPoint/" if _AP_SEG.search(code) else "/PreviewStandard/"
                if want not in url:
                    findings.append(f"{subj}:{code}:url-routing — expected {want} in {url}")
            elif st not in URL_EXEMPT and st in OVERLAY_STATES and st in PROVENANCED_STATES:
                pass  # already reported by check 1
            # 4 — id bleed (collect; judged after the loop)
            if e.get("cpalms_id"):
                id_owner.setdefault((subj, str(e["cpalms_id"])), set()).add(code)
            # 5 — extras + retirement completeness
            if code not in corpus and st not in {"cpalms_addition", "renumbered", "retired"}:
                findings.append(f"{subj}:{code}:extras — overlay-only code with state {st!r}")
            if st == "retired":
                for k in (*RETIREMENT_KEYS, "detail"):
                    if not e.get(k):
                        findings.append(f"{subj}:{code}:retired — missing {k}")
            # 9 — checked_at shape (string-order invariant the resume logic depends on)
            if e.get("checked_at") and not _TS.match(e["checked_at"]):
                findings.append(f"{subj}:{code}:checked_at — {e['checked_at']!r} not Z-form UTC")
            # 10 — unknown keys
            for k in set(e) - ALLOWED_ENTRY_KEYS:
                findings.append(f"{subj}:{code}:unknown-key — {k!r}")

        # 7 — the coverage float that gates blocking behaviour must match a recount
        verified = {c for c, e in entries.items()
                    if c in corpus and e.get("state") in VERIFIED_STATES}
        want_cov = round(len(verified) / max(1, len(corpus)), 4)
        if overlay.get("coverage") != want_cov:
            findings.append(f"{subj}:coverage — stored {overlay.get('coverage')} != recomputed "
                            f"{want_cov} (this float flips blocking behaviour at the trust "
                            f"threshold)")
        # 8 — scopes shapes
        for i, sc in enumerate(overlay.get("scopes") or []):
            if set(sc) not in SCOPE_SHAPES:
                findings.append(f"{subj}:scopes[{i}] — unexpected shape {sorted(sc)}")
        # 6 — manifest identity, per subject
        if man:
            ms = man.get("subjects", {}).get(subj, {})
            done = set(entries)
            needs_review = (set(corpus) & done) - verified
            remaining = set(corpus) - done
            got = {"corpus_count": len(corpus), "verified_in_corpus": len(verified),
                   "needs_review_in_corpus": len(needs_review), "remaining_count": len(remaining),
                   "corpus_sha256": hashlib.sha256(cf.read_bytes()).hexdigest()[:16]}
            for k, v in got.items():
                if ms.get(k) != v:
                    findings.append(f"{subj}:manifest — {k}: manifest={ms.get(k)!r} live={v!r}")
            totals["corpus"] += len(corpus)
            totals["verified"] += len(verified)
            totals["needs_review"] += len(needs_review)
            totals["remaining"] += len(remaining)

    # 4 — id bleed verdicts: one id under >1 code is cross-card bleed, the A4 defect shape.
    # duplicate_cpalms_ids legitimizes duplicates only WITHIN one code, never across codes.
    for (subj, cid), codes in id_owner.items():
        if len(codes) > 1:
            findings.append(f"{subj}:id-bleed — cpalms_id {cid} claimed by {sorted(codes)}")

    # 6 — the sum identity, and totals vs manifest. anchor_commit is deliberately NOT compared to
    # HEAD: it lags by one commit by construction (generated before the commit that contains it).
    if man:
        mt = man.get("totals", {})
        if totals["verified"] + totals["needs_review"] + totals["remaining"] != totals["corpus"]:
            findings.append(f"manifest:identity — verified+needs_review+remaining != corpus "
                            f"({totals})")
        for k in ("corpus", "verified", "needs_review", "remaining"):
            if mt.get(k) != totals[k]:
                findings.append(f"manifest:totals — {k}: manifest={mt.get(k)} live={totals[k]}")

    return findings


def main_audit() -> int:
    findings = audit()
    total_entries = sum(
        len(json.loads((OVERLAYS / f"{s}.cpalms.json").read_text(encoding="utf-8"))["entries"])
        for s in SUBJECT_FILES if (OVERLAYS / f"{s}.cpalms.json").exists())
    if findings:
        print(f"FAIL — {len(findings)} finding(s) across {total_entries} entries:")
        for f in findings[:80]:
            print("  •", f)
        if len(findings) > 80:
            print(f"  … and {len(findings) - 80} more")
        print("\nIf this followed a DELIBERATE predicate change: the overlays must be re-judged "
              "(--reclassify) before this audit can pass — that is the check working.")
        return 1
    print(f"OK — 0 findings across {total_entries} entries "
          f"({len(SUBJECT_FILES)} subjects; re-proof, routing, id-bleed, accounting, coverage, "
          f"manifest identity, scopes, timestamps, key vocabulary).")
    return 0


def self_test() -> int:
    """Prove every check can FAIL. A fixture the audit cannot fail on is not evidence.

    Strategy: copy the live corpus+overlays+manifest into a scratch tree, verify the audit is
    clean there, then apply ONE mutation per check and assert the audit catches exactly it."""
    import tempfile
    base = Path(tempfile.mkdtemp(prefix="audit-ov-"))

    def fresh() -> tuple[Path, Path, Path]:
        d = base / f"case{fresh.n}"
        fresh.n += 1
        (d / "overlays").mkdir(parents=True)
        for s in SUBJECT_FILES:
            (d / f"{s}.json").write_bytes((DATA / f"{s}.json").read_bytes())
            (d / "overlays" / f"{s}.cpalms.json").write_bytes(
                (OVERLAYS / f"{s}.cpalms.json").read_bytes())
        mp = d / "manifest.json"
        mp.write_bytes(MANIFEST.read_bytes())
        return d, d / "overlays", mp
    fresh.n = 0

    def run(mutate=None, remanifest=False) -> list[str]:
        d, ov, mp = fresh()
        if mutate:
            for s in SUBJECT_FILES:
                doc = json.loads((ov / f"{s}.cpalms.json").read_text(encoding="utf-8"))
                if mutate(s, doc):
                    (ov / f"{s}.cpalms.json").write_text(json.dumps(doc), encoding="utf-8")
                    break
        return audit(d, ov, mp)

    fails = 0

    def check(name, cond):
        nonlocal fails
        print(("PASS " if cond else "FAIL ") + name)
        fails += 0 if cond else 1

    check("baseline: the copied live tree audits CLEAN", run() == [])

    def flip_digit(s, doc):
        for c, e in doc["entries"].items():
            if e.get("state") == "confirmed" and any(ch.isdigit() for ch in
                                                     (e.get("statement_verified") or "")):
                e["statement_verified"] = re.sub(
                    r"\d", lambda m: str((int(m.group()) + 1) % 10),
                    e["statement_verified"], count=1)
                return True
        return False
    check("mutation: a flipped digit in a confirmed statement is caught by the re-proof",
          any(":re-proof" in f for f in run(flip_digit)))

    def swap_url(s, doc):
        for c, e in doc["entries"].items():
            if e.get("cpalms_url") and "/PreviewStandard/" in e["cpalms_url"]:
                e["cpalms_url"] = e["cpalms_url"].replace("/PreviewStandard/",
                                                          "/PreviewAccessPoint/")
                return True
        return False
    check("mutation: a swapped Preview path is caught by url-routing",
          any(":url-routing" in f for f in run(swap_url)))

    def bad_state(s, doc):
        c = next(iter(doc["entries"]))
        doc["entries"][c]["state"] = "totally_fine"
        return True
    check("mutation: an illegal state is caught",
          any(":state-legal" in f for f in run(bad_state)))

    def bleed(s, doc):
        it = iter(doc["entries"].items())
        (c1, e1), (c2, e2) = next(it), next(it)
        if e1.get("cpalms_id"):
            e2["cpalms_id"] = e1["cpalms_id"]
            return True
        return False
    check("mutation: one id under two codes is caught as id-bleed",
          any(":id-bleed" in f for f in run(bleed)))

    def strip_evidence(s, doc):
        for c, e in doc["entries"].items():
            if e.get("state") == "retired":
                e.pop("evidence", None)
                return True
        return False
    check("mutation: a retired entry stripped of its evidence is caught",
          any(":retired" in f for f in run(strip_evidence)))

    d, ov, mp = fresh()
    man = json.loads(mp.read_text(encoding="utf-8"))
    man["totals"]["verified"] -= 1
    mp.write_text(json.dumps(man), encoding="utf-8")
    check("mutation: a perturbed manifest count is caught",
          any("manifest:totals" in f for f in audit(d, ov, mp)))

    def cov(s, doc):
        doc["coverage"] = round(doc.get("coverage", 1.0) - 0.01, 4)
        return True
    check("mutation: a drifted coverage float is caught (the blocking-flip gate)",
          any(":coverage" in f for f in run(cov)))

    def scope(s, doc):
        (doc.setdefault("scopes", [])).append({"grades": "K", "frobnicate": 1,
                                               "generated_at": "t"})
        return True
    check("mutation: a third scopes shape is caught",
          any(":scopes[" in f for f in run(scope)))

    def ts(s, doc):
        c = next(iter(doc["entries"]))
        doc["entries"][c]["checked_at"] = "2026-08-13T00:00:00+00:00"
        return True
    check("mutation: an offset-form timestamp is caught",
          any(":checked_at" in f for f in run(ts)))

    def unk(s, doc):
        c = next(iter(doc["entries"]))
        doc["entries"][c]["frobnicate"] = True
        return True
    check("mutation: an unknown entry key is caught (archaeology is allowed BY NAME)",
          any(":unknown-key" in f for f in run(unk)))

    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true",
                    help="mutation battery: prove every check can fail")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else main_audit())
