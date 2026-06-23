#!/usr/bin/env python3
"""Resolve workplace-connector feature flags into an available-evidence plan (offline).

Reads the connector registry (connectors.json) and an optional per-deployment flag config
(feature-flags.*.json) and answers: given what's connected, which evidence sources are ACTIVE, what is
the provider chain (primary + fallbacks) per evidence type, and where are the GAPS? Encodes the
degradation/convergence + override policy from connectors.md. Mirrors tools/crosswalk.py. Stdlib only,
no network.

Usage:
  python3 shared/connectors/connectors.py --list
  python3 shared/connectors/connectors.py --flags <config.json> --plan
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "connectors.json"

# Always-on offline fallbacks (unless a deployment explicitly disables/blocks them).
ALWAYS_ON = {"manual_paste", "uploaded_file"}
# Evidence priority, strong -> weak (see connectors.md). Drives the provider chain order of preference.
EVIDENCE_PRIORITY = ["calendar_event", "email", "roster", "attendee_roles", "transcript",
                     "call_notes", "chat_history", "file", "student_profile", "guardians", "plan_flags"]


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def load_flags(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve(flags: dict, registry: dict | None = None) -> dict:
    """Return effective per-connector state, the active set, the per-evidence provider chain, and gaps."""
    reg = registry or load_registry()
    conf = flags.get("connectors", {}) or {}
    blocked = set(flags.get("blocked_sources", []) or [])
    allowed = set(flags.get("allowed_sources", []) or [])

    states: dict[str, str] = {}
    for c in reg["connectors"]:
        cid, default = c["id"], c["default_flag"]
        st = conf.get(cid, default)
        if cid in ALWAYS_ON and st != "disabled":
            st = "available"
        if cid in blocked:
            st = "disabled"
        if allowed and cid not in allowed and cid not in ALWAYS_ON:
            st = "disabled"  # an allow-list narrows the path: anything not listed is off
        states[cid] = st

    active = [c["id"] for c in reg["connectors"] if states[c["id"]] == "available"]

    # Provider chain per evidence type: active connectors that provide it, in registry order.
    provides = {c["id"]: set(c.get("provides", [])) for c in reg["connectors"]}
    authoritative = {c["id"]: set(c.get("authoritative_for", [])) for c in reg["connectors"]}
    chains, gaps = {}, []
    for et in reg.get("evidence_types", EVIDENCE_PRIORITY):
        provs = [cid for cid in active if et in provides.get(cid, set())]
        # An authoritative provider (e.g., SIS for student_profile) goes first.
        provs.sort(key=lambda cid: (0 if et in authoritative.get(cid, set()) else 1))
        if provs:
            chains[et] = provs
        else:
            gaps.append(et)
    return {"states": states, "active": active, "evidence_chain": chains, "gaps": gaps,
            "blocked": sorted(blocked), "allowed": sorted(allowed),
            "student_identification": flags.get("student_identification", {"mode": "name"}),
            "storage_adapter": flags.get("storage_adapter", "auto")}


def cmd_list() -> None:
    reg = load_registry()
    print(f"connector registry ({len(reg['connectors'])}):")
    for c in reg["connectors"]:
        auth = "  AUTHORITATIVE for " + ",".join(c["authoritative_for"]) if c.get("authoritative_for") else ""
        print(f"  - {c['id']:17} [{c['default_flag']:13}] provides: {', '.join(c.get('provides', []))}{auth}")
    print("\nstates:", " · ".join(reg["states"]))
    print("extensible stubs:", ", ".join(reg.get("extensible_stubs", [])) or "none")


def cmd_plan(flags_path: str | None) -> None:
    flags = load_flags(flags_path)
    r = resolve(flags)
    print(f"deployment: {flags.get('deployment', '(defaults — no flags file)')}")
    print(f"student_identification: {r['student_identification'].get('mode', 'name')}   "
          f"storage_adapter: {r['storage_adapter']}")
    print("\neffective connector states:")
    for cid, st in r["states"].items():
        mark = "ACTIVE " if st == "available" else "off    "
        print(f"  {mark} {cid:17} {st}")
    print("\nevidence provider chain (primary -> fallbacks):")
    for et, chain in r["evidence_chain"].items():
        print(f"  {et:16} {' -> '.join(chain)}")
    if r["gaps"]:
        print("\nGAPS (no active provider — lower confidence / converge from other signals or ask):")
        print("  " + ", ".join(r["gaps"]))
    if r["blocked"]:
        print("\nblocked_sources:", ", ".join(r["blocked"]))


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Resolve connector feature flags into an evidence plan (offline).")
    ap.add_argument("--list", action="store_true", help="list the connector registry + default flags")
    ap.add_argument("--flags", metavar="CONFIG", help="path to a per-deployment feature-flags JSON")
    ap.add_argument("--plan", action="store_true", help="show the active sources + evidence provider chains")
    a = ap.parse_args(argv)
    if a.plan or a.flags:
        cmd_plan(a.flags)
    else:
        cmd_list()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
