#!/usr/bin/env python3
"""Teacher-profile setup wizard + context registration (offline, stdlib) — RFC-F001 V2 workstream E.

Establishes/maintains ONE teacher's operating profile (roles, duties, handoff/role-interaction map,
preferences) and registers it into the shared context as classroom/teacher-scope sop_refs + overrides so
every other skill adapts to this teacher. The profile is a GITIGNORED local store
(shared/context/profiles/teacher.local.json) — the teacher's own data, never committed.

Interactive use drives a short interview (see references/wizard.md). For automation/testing this is
ALSO answers-file driven so it runs headless and deterministic.

Honest by construction: teacher-stated facts outrank crawled inferences (provenance + confidence on
every fact); no student PII; human_review_required stays true.

Local-First preferences (L0): the wizard also captures the teacher's offline/low-token operating
preferences (which retrieval tier to use, whether to opt in to the local semantic index or a local
model) as a structured, REVERSIBLE `local_first` block in the same gitignored profile. Capability-gated
tiers (vector index, local LLM) are OFF until the teacher grants explicit consent — installs are never
silent — and consent + choices can be reset or re-pointed when a teacher moves schools or changes their
mind. Defaults are the safest, fully-offline path: cached_python + stdlib_keyword.

Usage:
  python3 skills/operations/teacher-profile/scripts/profile_wizard.py --init answers.json     # write the local profile
  python3 skills/operations/teacher-profile/scripts/profile_wizard.py --demo                  # init from the example
  python3 skills/operations/teacher-profile/scripts/profile_wizard.py --show                  # print current profile
  python3 skills/operations/teacher-profile/scripts/profile_wizard.py --validate              # check vs schema (light)
  python3 skills/operations/teacher-profile/scripts/profile_wizard.py --register              # emit context sop_refs/overrides
  python3 .../profile_wizard.py --preferences                                      # show Local-First prefs
  python3 .../profile_wizard.py --preferences --consent local_semantic --set '{"retrieval_mode":"vector"}'
  python3 .../profile_wizard.py --preferences --reset                              # revert to safe defaults
  python3 .../profile_wizard.py --preferences --school-change '{"school":"Lake Nona HS","msid":"480123"}'
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "tools" / "sync_check.py").exists()), Path(__file__).resolve().parents[3])  # repo root by marker (relocation-proof)
PROFILES = ROOT / "shared" / "context" / "profiles"
LOCAL = PROFILES / "teacher.local.json"
EXAMPLE = PROFILES / "teacher.example.json"
SCHEMA = PROFILES / "teacher.schema.json"

REQUIRED_TOP = ["schema_version", "teacher", "roles", "human_review_required"]
HANDOFF_REQUIRED = ["what", "direction", "counterparty_role"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_provenance(items: list[dict]) -> list[dict]:
    """A teacher-driven wizard records facts as teacher_stated/high unless told otherwise."""
    for it in items:
        it.setdefault("provenance", "teacher_stated")
        it.setdefault("confidence", "high")
    return items


def build_profile(answers: dict) -> dict:
    prof = {
        "schema_version": "0.1.0",
        "teacher": answers.get("teacher", {}),
        "roles": _default_provenance(answers.get("roles", [])),
        "duties": _default_provenance(answers.get("duties", [])),
        "handoffs": answers.get("handoffs", []),
        "meetings": answers.get("meetings", []),
        "preferences": answers.get("preferences", {}),
        "overrides": answers.get("overrides", []),
        "updated": _now(),
        "human_review_required": True,
    }
    return prof


def validate(prof: dict) -> list[str]:
    """Light structural validation (no external deps). Returns a list of problems (empty = ok)."""
    issues = []
    for k in REQUIRED_TOP:
        if k not in prof:
            issues.append(f"missing required field: {k}")
    if prof.get("human_review_required") is not True:
        issues.append("human_review_required must be true")
    if not prof.get("teacher", {}).get("display_name"):
        issues.append("teacher.display_name is required")
    if not prof.get("roles"):
        issues.append("at least one role is required")
    for i, h in enumerate(prof.get("handoffs", [])):
        for k in HANDOFF_REQUIRED:
            if not h.get(k):
                issues.append(f"handoff[{i}] missing {k}")
        if h.get("direction") not in ("to", "from", "bidirectional"):
            issues.append(f"handoff[{i}] direction must be to/from/bidirectional")
    # PII guardrail: nudge if a contact looks committed-worthy (it must stay local-only)
    return issues


def register_fragment(prof: dict) -> dict:
    """Produce the context contribution: a classroom-scope sop_ref to the (gitignored) profile + overrides
    derived from preferences. A context build merges this; we do not mutate a contract here."""
    sop_ref = {
        "id": "teacher-profile-local",
        "scope": "classroom",
        "path": str(LOCAL.relative_to(ROOT)),
        "label": f"Teacher operating profile — {prof.get('teacher', {}).get('display_name', '?')}",
        "effective": prof.get("updated"),
        "source": "teacher-profile wizard (teacher_stated)",
    }
    overrides = list(prof.get("overrides", []))
    for k, v in (prof.get("preferences") or {}).items():
        overrides.append({"instruction": f"preference: {k} = {v}", "by": "teacher",
                          "timestamp": prof.get("updated")})
    # Role/handoff map exposed for routing skills (meeting-classifier, records handoffs).
    role_map = {
        "roles": [r.get("role") for r in prof.get("roles", [])],
        "handoffs": [{"what": h.get("what"), "direction": h.get("direction"),
                      "counterparty_role": h.get("counterparty_role")} for h in prof.get("handoffs", [])],
    }
    out = {"sop_refs": [sop_ref], "overrides": overrides, "role_interaction_map": role_map,
           "scope": "classroom", "human_review_required": True}
    # Expose Local-First operating preferences (L0) so retrieval/generation engines pick the
    # teacher's chosen tier (e.g. the L1 cache vs an opt-in vector index) without re-asking.
    if prof.get("local_first"):
        out["local_first"] = prof["local_first"]
    return out


# --------------------------------------------------------------------- Local-First preferences (L0)
# Capability-gated tiers map to a consent key; a tier/mode that needs consent stays at the safe default
# until that consent is granted. Consent is recorded in the profile and is fully reversible.
OFFLINE_TIERS = ["cached_python", "local_semantic", "local_llm"]
RETRIEVAL_MODES = ["stdlib_keyword", "vector"]
LOCAL_MODELS = ["off", "ollama", "llamafile"]
FEED_UPDATE_MODES = ["manual", "on_session_start", "scheduled"]
# choice -> consent capability it requires (None = no consent needed; always safe + offline)
_TIER_CONSENT = {"cached_python": None, "local_semantic": "local_semantic", "local_llm": "local_llm"}
_MODE_CONSENT = {"stdlib_keyword": None, "vector": "local_semantic"}
# Feed self-update cadence default DERIVED from the offline tier (separately overridable, L7).
_TIER_FEED_DEFAULT = {"cached_python": "manual", "local_semantic": "on_session_start",
                      "local_llm": "on_session_start"}


def default_prefs() -> dict:
    """The safest, fully-offline, zero-token-overhead path. Everything gated is OFF."""
    return {
        "offline_tier": "cached_python",
        "retrieval_mode": "stdlib_keyword",
        "local_model": "off",
        "feed_update_mode": "manual",          # L7 trigger; default derived from offline_tier
        "feed_update_mode_source": "derived",  # "derived" follows the tier; "explicit" is teacher-pinned
        "consents": {},                # capability_id -> {"granted": bool, "at": iso}
        "school_scope": None,          # {"school":..., "msid":...} — re-pointed on a school change
        "provenance": "teacher_stated",
        "confidence": "high",
        "updated": _now(),
    }


def load_prefs(prof: dict) -> dict:
    p = default_prefs()
    p.update(prof.get("local_first") or {})
    p.setdefault("consents", {})
    return p


def _granted(prefs: dict, cap: str | None) -> bool:
    return cap is None or bool(prefs.get("consents", {}).get(cap, {}).get("granted"))


def apply_prefs(prefs: dict, updates: dict) -> list[str]:
    """Apply requested preference changes, honoring consent gates. Returns warnings for any
    change that was held back because its consent isn't granted (the safe default is kept)."""
    warnings: list[str] = []
    if "offline_tier" in updates:
        t = updates["offline_tier"]
        if t not in OFFLINE_TIERS:
            warnings.append(f"offline_tier '{t}' invalid (choose {OFFLINE_TIERS}) — unchanged")
        elif not _granted(prefs, _TIER_CONSENT[t]):
            warnings.append(f"offline_tier '{t}' needs consent '{_TIER_CONSENT[t]}' — "
                            f"kept '{prefs['offline_tier']}'. Grant with --consent {_TIER_CONSENT[t]}")
        else:
            prefs["offline_tier"] = t
    if "retrieval_mode" in updates:
        m = updates["retrieval_mode"]
        if m not in RETRIEVAL_MODES:
            warnings.append(f"retrieval_mode '{m}' invalid (choose {RETRIEVAL_MODES}) — unchanged")
        elif not _granted(prefs, _MODE_CONSENT[m]):
            warnings.append(f"retrieval_mode '{m}' needs consent '{_MODE_CONSENT[m]}' — "
                            f"kept '{prefs['retrieval_mode']}'. Grant with --consent {_MODE_CONSENT[m]}")
        else:
            prefs["retrieval_mode"] = m
    if "local_model" in updates:
        lm = updates["local_model"]
        if lm not in LOCAL_MODELS:
            warnings.append(f"local_model '{lm}' invalid (choose {LOCAL_MODELS}) — unchanged")
        else:
            prefs["local_model"] = lm
    # Feed-update cadence (L7): an explicit set pins it; otherwise it follows the offline tier.
    if "feed_update_mode" in updates:
        fm = updates["feed_update_mode"]
        if fm not in FEED_UPDATE_MODES:
            warnings.append(f"feed_update_mode '{fm}' invalid (choose {FEED_UPDATE_MODES}) — unchanged")
        else:
            prefs["feed_update_mode"] = fm
            prefs["feed_update_mode_source"] = "explicit"
    elif "offline_tier" in updates and prefs.get("feed_update_mode_source") != "explicit":
        # tier changed and the teacher hasn't pinned the cadence — derive the sensible default
        derived = _TIER_FEED_DEFAULT.get(prefs["offline_tier"], "manual")
        if derived != prefs.get("feed_update_mode"):
            prefs["feed_update_mode"] = derived
            warnings.append(f"feed_update_mode derived '{derived}' from offline_tier "
                            f"'{prefs['offline_tier']}' (override with --set '{{\"feed_update_mode\":...}}')")
    # Coherence: a local_llm tier with no model selected is inert — flag it, don't silently fix.
    if prefs["offline_tier"] == "local_llm" and prefs["local_model"] == "off":
        warnings.append("offline_tier 'local_llm' selected but local_model is 'off' — "
                        "set --set '{\"local_model\":\"ollama\"}' (or llamafile) to make it active")
    return warnings


def grant_consent(prefs: dict, cap: str) -> None:
    prefs.setdefault("consents", {})[cap] = {"granted": True, "at": _now()}


def revoke_consent(prefs: dict, cap: str) -> list[str]:
    """Revoke a consent and roll back any preference that depended on it (reversibility)."""
    notes = []
    prefs.setdefault("consents", {})[cap] = {"granted": False, "at": _now()}
    if _TIER_CONSENT.get(prefs.get("offline_tier")) == cap:
        prefs["offline_tier"] = "cached_python"
        notes.append(f"offline_tier rolled back to 'cached_python' (consent '{cap}' revoked)")
        if prefs.get("feed_update_mode_source") != "explicit":
            prefs["feed_update_mode"] = _TIER_FEED_DEFAULT["cached_python"]
    if _MODE_CONSENT.get(prefs.get("retrieval_mode")) == cap:
        prefs["retrieval_mode"] = "stdlib_keyword"
        notes.append(f"retrieval_mode rolled back to 'stdlib_keyword' (consent '{cap}' revoked)")
    return notes


def _parse_json_arg(val: str) -> dict:
    """Accept inline JSON or @path/to/file.json."""
    if val.startswith("@"):
        return _load(Path(val[1:]))
    return json.loads(val)


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="Teacher-profile setup wizard + context registration (offline).")
    ap.add_argument("--init", metavar="ANSWERS_JSON", help="build the local profile from an answers file")
    ap.add_argument("--demo", action="store_true", help="build the local profile from teacher.example.json")
    ap.add_argument("--show", action="store_true", help="print the current local profile")
    ap.add_argument("--validate", action="store_true", help="validate the current local profile")
    ap.add_argument("--register", action="store_true", help="emit the context sop_refs/overrides fragment")
    # Local-First preferences (L0)
    ap.add_argument("--preferences", action="store_true", help="view/edit Local-First offline preferences")
    ap.add_argument("--set", metavar="JSON", help="preference updates as inline JSON or @file")
    ap.add_argument("--consent", action="append", default=[], metavar="CAP",
                    help="grant consent for a gated capability (local_semantic, local_llm); repeatable")
    ap.add_argument("--revoke", action="append", default=[], metavar="CAP",
                    help="revoke a consent and roll back any preference that needed it; repeatable")
    ap.add_argument("--reset", action="store_true", help="revert Local-First preferences to safe defaults")
    ap.add_argument("--school-change", metavar="JSON", dest="school_change",
                    help="re-point school scope (inline JSON or @file) and re-confirm preferences")
    a = ap.parse_args(argv)

    if a.init or a.demo:
        answers = _load(Path(a.init)) if a.init else _load(EXAMPLE)
        prof = build_profile(answers)
        issues = validate(prof)
        if issues:
            print(json.dumps({"status": "invalid", "issues": issues}, indent=2))
            return 1
        PROFILES.mkdir(parents=True, exist_ok=True)
        LOCAL.write_text(json.dumps(prof, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "profile_written", "path": str(LOCAL.relative_to(ROOT)),
                          "roles": [r.get("role") for r in prof["roles"]],
                          "handoffs": len(prof["handoffs"]), "gitignored": True,
                          "next": "--register to contribute sop_refs/overrides to the context",
                          "human_review_required": True}, indent=2))
        return 0

    if not LOCAL.exists():
        print(json.dumps({"status": "no_profile",
                          "detail": f"no {LOCAL.relative_to(ROOT)} yet — run --init <answers.json> or --demo"}))
        return 1
    prof = _load(LOCAL)
    if a.validate:
        issues = validate(prof)
        print(json.dumps({"status": "ok" if not issues else "invalid", "issues": issues}, indent=2))
        return 0 if not issues else 1
    if a.preferences:
        prefs = default_prefs() if a.reset else load_prefs(prof)
        notes: list[str] = []
        if a.reset:
            notes.append("preferences reset to safe defaults (consents cleared)")
        for cap in a.revoke:
            notes += revoke_consent(prefs, cap)
        for cap in a.consent:
            grant_consent(prefs, cap)
        if a.school_change:
            prefs["school_scope"] = _parse_json_arg(a.school_change)
            notes.append("school_scope re-pointed — re-confirm preferences for the new school "
                         "(ties into F3 schools + context overlays)")
        if a.set:
            notes += apply_prefs(prefs, _parse_json_arg(a.set))
        prefs["updated"] = _now()
        # persist only when something was actually requested (a bare --preferences just views)
        changed = bool(a.reset or a.revoke or a.consent or a.school_change or a.set)
        if changed:
            prof["local_first"] = prefs
            prof["updated"] = _now()
            LOCAL.write_text(json.dumps(prof, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "preferences" if not changed else "preferences_updated",
                          "local_first": prefs, "notes": notes, "gitignored": True,
                          "human_review_required": True}, indent=2, ensure_ascii=False))
        return 0
    if a.register:
        print(json.dumps(register_fragment(prof), indent=2, ensure_ascii=False))
        return 0
    # default: show
    print(json.dumps(prof, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
