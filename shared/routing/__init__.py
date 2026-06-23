"""Shared routing engine — one data-driven router (routing.json) consumed by teacher-core and
meeting-classifier. See router.py and routing.json."""
from .router import load_registry, meeting_route, route, score_skills

__all__ = ["load_registry", "meeting_route", "route", "score_skills"]
