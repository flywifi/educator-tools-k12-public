"""context — teaching-context & SOP engine (package).

Re-exports the resolver API from context.py so `import context` works when `shared/` is on the path.
Canonical docs: README.md, context-model.md, sop-model.md, adaptation.md.
"""
from .context import (
    DEFAULT_PRECEDENCE,
    SCOPE_RANK,
    apply_override,
    build_context,
    find_district,
    load_districts,
    load_overlays,
    load_school_types,
    resolve,
    resolve_conflict,
    school_type_rules,
    validate_context,
)

__all__ = [
    "build_context", "resolve", "apply_override", "resolve_conflict", "validate_context",
    "load_districts", "load_school_types", "load_overlays", "find_district", "school_type_rules",
    "DEFAULT_PRECEDENCE", "SCOPE_RANK",
]
