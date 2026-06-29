---
name: feed-discover
description: "Discover RSS/Atom feed URLs from a seed web page using autodiscovery (link tags, common paths, MIME sniffing). Use this atom when feed-curator needs to find new feeds from an authoritative page. Do NOT use for validating existing feeds — that is atom-feed-validate. Do NOT use for content extraction."
---

# feed-discover

Performs RSS/Atom autodiscovery from a seed page URL. Returns candidate feed URLs with confidence and discovery method. Used by feed-curator step 2 and reusable by any system expanding its feed catalog.

## Input

```json
{
  "seed_url": "https://www.fldoe.org/academics/standards/",
  "max_candidates": 10,
  "discovery_methods": ["link_tag", "common_paths", "mime_sniff"]
}
```

## Output

```json
{
  "tool": "feed-discover",
  "candidates": [
    {"feed_url": "https://www.fldoe.org/feed.xml", "method": "link_tag", "confidence": 0.95, "title": "FL DOE Updates"},
    {"feed_url": "https://www.fldoe.org/rss/standards.xml", "method": "common_paths", "confidence": 0.6, "title": null}
  ],
  "seed_url": "https://www.fldoe.org/academics/standards/",
  "human_review_required": true
}
```

## Do NOT use this atom for
- Validating existing feeds (use atom-feed-validate)
- Extracting or summarizing feed content
- Crawling beyond the seed page (single-page discovery only)

## Pipeline note
Follows `references/method.md` at the Discovery step (feed autodiscovery). Output conforms to `references/metadata-schema.md`. `human_review_required: true` — discovered feeds must be verified by a human before adding to the catalog.
