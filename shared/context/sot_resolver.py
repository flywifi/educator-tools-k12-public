"""sot_resolver - the canonical source-of-truth resolver for the teaching domain.

When sources disagree about a claim (a standard, a course rule, a mandate, an operating norm), this
picks ONE interpretation by source authority + the context's authority precedence, and emits an
**auditable decision record with a minority report** (decision_log / conflicts / failed_to_merge /
residual_uncertainty) so the alternative is preserved, never buried in prose.

Adapted from the operating-reference / minority-report pattern: classify which source is allowed to
prove a claim (source-roles.json), choose the winner, and structure the disagreement. Stdlib only;
fully offline. Canonical prose: shared/context/source-of-truth.md, minority-report.md.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # works both as a script (python3 shared/context/sot_resolver.py) and as a package import
    from context import SCOPE_RANK, DEFAULT_PRECEDENCE
except ImportError:  # pragma: no cover - package path
    from .context import SCOPE_RANK, DEFAULT_PRECEDENCE

HERE = Path(__file__).resolve().parent
SOURCE_ROLES_PATH = HERE / "source-roles.json"

# Claim types that ALWAYS require a human decision when contested or low-confidence (conflict-protocol
# §5): individual-student and legal determinations are never auto-decided.
_ESCALATING_CLAIMS = {"iep_504_requirement", "eligibility_scholarship",
                      "graduation_promotion_requirement", "compliance_mandate"}

# `kind` pairs that must not be silently blended -> failed_to_merge + minority report (policy triggers).
_NON_MERGEABLE = {frozenset({"canon", "current_practice"}),
                  frozenset({"canon", "provisional_update"})}


def load_source_roles() -> Dict[str, Any]:
    return json.loads(SOURCE_ROLES_PATH.read_text(encoding="utf-8"))


def source_role(claim_type: Optional[str]) -> Dict[str, Any]:
    """The source-role entry for a claim type (what proves it, ranked sources, anti-rules)."""
    return load_source_roles().get("claim_types", {}).get(claim_type or "", {})


def _ladder_rank(roles: Dict[str, Any], ladder_name: str, source: str) -> Optional[int]:
    for e in roles.get(ladder_name, {}).get("order", []):
        if e.get("source") == source:
            return e.get("rank")
    return None


def _authority_rank(cand: Dict[str, Any], claim_type: Optional[str], applicability: Optional[str],
                    precedence: List[str]) -> int:
    """How strong this candidate is. Source-role rank (if the source is recognized for this claim)
    wins; otherwise fall back to the authority-precedence rank of the candidate's scope."""
    roles = load_source_roles()
    role = roles.get("claim_types", {}).get(claim_type or "", {})
    src = cand.get("source")
    # 1) explicit authoritative source for this claim type (respecting standards applicability `when`)
    for s in role.get("authoritative_sources", []):
        if s.get("source") == src and (s.get("when") in (None, applicability)):
            return int(s.get("rank", 50))
    # 2) a claim type that uses a shared compliance ladder
    if role.get("uses_ladder"):
        r = _ladder_rank(roles, role["uses_ladder"], src)
        if r is not None:
            return int(r)
    # 3) fall back to the context's authority precedence by scope
    rank_by_scope = {sc: (len(precedence) - i) * 5 for i, sc in enumerate(precedence)}
    return int(rank_by_scope.get(cand.get("scope"), 10))


def _is_meaningful(cand: Dict[str, Any]) -> bool:
    """A candidate that can win or count as a real disagreement: verified and not fabricated.
    Fabrication is never a source (hard rule); unverified candidates can only raise uncertainty."""
    if cand.get("fabricated"):
        return False
    return cand.get("verified", True) is not False


def resolve(claim: str, claim_type: Optional[str] = None,
            candidates: Optional[List[Dict[str, Any]]] = None,
            context: Optional[Dict[str, Any]] = None,
            precedence: Optional[List[str]] = None) -> Dict[str, Any]:
    """Settle `claim` among `candidates`, returning a decision record (decision.schema.json).

    Each candidate: {interpretation, scope, source, source_id?, claim_id?, evidence?, confidence?,
    verified?, fabricated?, kind?, materiality?}. `kind` in {canon, current_practice,
    provisional_update, ...} drives non-mergeable detection.
    """
    candidates = list(candidates or [])
    applicability = (context or {}).get("standards_applicability")
    precedence = precedence or (context or {}).get("authority_precedence") or list(DEFAULT_PRECEDENCE)

    # Rank every candidate; fabricated ones are recorded as uncertainty, never as winners.
    ranked: List[Dict[str, Any]] = []
    residual: List[Dict[str, Any]] = []
    for c in candidates:
        if c.get("fabricated"):
            residual.append({
                "statement": f"A candidate from {c.get('source','?')} was flagged fabricated/unverifiable and excluded.",
                "what_would_resolve_it": "Verify the claim on its authoritative source or drop it.",
                "impact_if_wrong": "Using it would be a fabrication (critical integrity failure)."})
            continue
        ranked.append({**c, "_rank": _authority_rank(c, claim_type, applicability, precedence)})
    ranked.sort(key=lambda c: c["_rank"], reverse=True)

    winner = ranked[0] if ranked else None
    meaningful = [c for c in ranked if _is_meaningful(c)]

    # Conflicts: meaningful candidates whose interpretation differs from the winner's.
    conflicts: List[Dict[str, Any]] = []
    failed_to_merge: List[Dict[str, Any]] = []
    if winner:
        win_interp = (winner.get("interpretation") or "").strip().lower()
        for c in meaningful[1:]:
            if (c.get("interpretation") or "").strip().lower() == win_interp:
                continue
            close = (winner["_rank"] - c["_rank"]) <= 15  # comparably strong -> material
            conflicts.append({
                "source_a": f"{winner.get('source','?')} ({winner.get('source_id') or winner.get('scope','?')})",
                "source_b": f"{c.get('source','?')} ({c.get('source_id') or c.get('scope','?')})",
                "conflict_summary": f"{winner.get('interpretation')}  VS  {c.get('interpretation')}",
                "materiality": c.get("materiality") or ("high" if close else "medium"),
                "affected_claim_ids": [i for i in (winner.get("claim_id"), c.get("claim_id")) if i]})
            # Non-mergeable kinds (canon vs current-practice / provisional update) -> keep both, never blend.
            if frozenset({winner.get("kind"), c.get("kind")}) in _NON_MERGEABLE:
                failed_to_merge.append({
                    "interpretation_a": f"[{winner.get('kind')}] {winner.get('interpretation')}",
                    "interpretation_b": f"[{c.get('kind')}] {c.get('interpretation')}",
                    "why_not_mergeable": "Canon and observed/provisional practice must not be blended; "
                                         "promoting practice to doctrine requires explicit review.",
                    "affected_claim_ids": [i for i in (winner.get("claim_id"), c.get("claim_id")) if i]})

    # Residual uncertainty: low-confidence or unverified winner.
    if winner and winner.get("confidence") == "low":
        residual.append({
            "statement": f"The chosen interpretation rests on a low-confidence source ({winner.get('source','?')}).",
            "what_would_resolve_it": "Confirm on the authoritative source for this claim type.",
            "impact_if_wrong": "Downstream artifacts may align to the wrong rule/standard."})
    if winner and winner.get("verified") is False:
        residual.append({
            "statement": f"The chosen source ({winner.get('source','?')}) is not yet verified.",
            "what_would_resolve_it": source_role(claim_type).get("hard_rule", "Verify on the source."),
            "impact_if_wrong": "Possible misalignment; never present unverified as verified."})

    minority_report_required = bool(conflicts or failed_to_merge)
    escalate = bool(claim_type in _ESCALATING_CLAIMS and (minority_report_required or
                    (winner or {}).get("confidence") == "low" or not winner))

    why = "no candidate sources were provided" if not winner else (
        f"highest authority for a {claim_type or 'general'} claim "
        f"(scope={winner.get('scope')}, source={winner.get('source')}, rank={winner['_rank']})"
        + ("; alternatives preserved in the minority report" if minority_report_required else
           "; no material disagreement"))

    return {
        "decision_id": f"dec-{uuid.uuid4().hex[:12]}",
        "claim": claim,
        "claim_type": claim_type,
        "context_ref": (context or {}).get("context_id"),
        "decision_log": {
            "chosen_interpretation": winner.get("interpretation") if winner else None,
            "why_it_won": why,
            "winning_scope": winner.get("scope") if winner else None,
            "winning_source": winner.get("source") if winner else None,
            "supporting_claim_ids": [winner["claim_id"]] if winner and winner.get("claim_id") else [],
            "supporting_source_ids": [winner["source_id"]] if winner and winner.get("source_id") else [],
            "confidence": (winner.get("confidence", "medium") if winner else "low"),
        },
        "conflicts": conflicts,
        "failed_to_merge": failed_to_merge,
        "residual_uncertainty": residual,
        "minority_report_required": minority_report_required,
        "escalate": escalate,
        "resolved_by": "sot-resolver",
        "human_review_required": True,
    }


if __name__ == "__main__":  # demo: district pacing SOP (canon) vs a recurring classroom practice
    decision = resolve(
        claim="What pacing governs the Algebra 1 unit sequence this quarter?",
        claim_type="operating_rule",
        candidates=[
            {"interpretation": "Follow the district pacing guide (Unit 3 by week 6).",
             "scope": "district", "source": "district_policy", "source_id": "OCPS-pacing-2025",
             "claim_id": "c1", "confidence": "high", "verified": True, "kind": "canon"},
            {"interpretation": "Stay on the teacher's slower sequence used all year (Unit 3 by week 9).",
             "scope": "classroom", "source": "classroom_practice", "claim_id": "c2",
             "confidence": "medium", "verified": True, "kind": "current_practice"},
        ])
    print(json.dumps(decision, indent=2))
