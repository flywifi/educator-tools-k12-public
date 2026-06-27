"""shared/render — resilient multi-prong fetch for JS-required / hard-to-scrape public pages.

Render, not evasion: one honest identifying User-Agent, robots.txt respected, the site's own
JavaScript run the way a browser is meant to. No UA rotation, no impersonation, no CAPTCHA /
rate-limit bypass. See render_prongs.py for the prong chain and capability gating.
"""
from .render_prongs import (  # noqa: F401
    HONEST_UA,
    DEFAULT_ORDER,
    capability_report,
    detect,
    resilient_fetch,
    robots_allowed,
)

__version__ = "0.1.0"
