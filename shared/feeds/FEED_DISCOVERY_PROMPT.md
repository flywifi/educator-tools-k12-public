# Feed-discovery prompt (give this to a web-enabled AI chatbot)

Paste everything in the fenced block below into a chatbot that can browse the live web.
Paste its JSON answer back to the TOS assistant; it drops straight into `shared/feeds/feeds.json`.

```
You are a feed-discovery assistant with live web access. Find REAL, WORKING RSS or Atom
feeds for K-12 education sources and return them as JSON in the exact schema below.

NON-NEGOTIABLE RULES
- Only include a feed if you actually fetched its URL and confirmed it is a valid RSS or
  Atom document (the response is XML whose root is <rss> or <feed> and contains <item> or
  <entry> elements). Do NOT guess or fabricate a feed URL. A page that merely mentions
  "RSS" is not a feed.
- For each verified feed, prove it by quoting the title + link + date of the single most
  recent item.
- If you cannot find/verify a real feed for a target, put it under "unverified" with the
  page(s) you checked and what you found (e.g., "no RSS link in page source"). Never invent one.
- Respect robots.txt and only use public pages. Report any host that blocks you.

TARGETS (find a feed for each; add others you discover)
1. Orange County Public Schools (OCPS), Orlando FL — district news/newsroom. It is a
   Finalsite site (ocps.net); Finalsite news feeds are often at a URL containing
   "/site/RSS/". Find the actual feed URL by viewing the newsroom page source for
   <link rel="alternate" type="application/rss+xml" href="..."> or an RSS icon link.
2. Florida Department of Education (fldoe.org) — newsroom/press releases feed.
3. CPALMS (cpalms.org) — any updates/news feed.
4. Florida Legislature / FL Statutes Title XLVIII (leg.state.fl.us) — any updates feed.
5. WIDA (wida.wisc.edu) — news feed (English-language-development standards).
6. U.S. Department of Education (ed.gov) — news/press feed.
7. Monarch Learning Academy, Orlando FL (monarchlearningacademy.com) — a private PK-8
   school; find any news, blog, events, or calendar feed (RSS/iCal). Calendar/iCal is fine —
   note the format.

HOW TO LABEL EACH FEED
- category: one of standards | legislation | program | news | directory
- authority: "primary" for an official government / standards / district-official source;
  "secondary" for news/commentary or a single private school.
- tier: "canonical" (official gov/standards/district-official — the only tier that confirms
  a change) | "news_teacher_student" (news about issues affecting teachers/students) |
  "product_updates" (edtech/vendor product news — only if explicitly a vendor).
- scope: national | state | district | school
- grade_band (e.g., "K-12", "PK-8") and subject (or null)
- purpose: one plain sentence on what the feed is for
- parser: "rss" or "atom" (or "ical" if it is a calendar feed)
- cadence_days: a reasonable check interval (news ~7, low-traffic ~14-30)

OUTPUT — return ONLY this JSON, nothing else:
{
  "verified": [
    {
      "id": "ocps-news",
      "url": "<the ACTUAL feed URL you fetched and confirmed>",
      "label": "Orange County Public Schools — newsroom",
      "category": "news",
      "authority": "primary",
      "tier": "canonical",
      "purpose": "OCPS official district news affecting teachers and students",
      "grade_band": "K-12",
      "subject": null,
      "scope": "district",
      "type": "feed",
      "parser": "rss",
      "cadence_days": 7,
      "verified": true,
      "discover_from": "<the page where you found the feed link>",
      "proof_latest_item": {"title": "...", "link": "...", "date": "..."},
      "state": {"etag": null, "last_modified": null, "content_sha256": null, "last_checked": null, "last_status": null}
    }
  ],
  "unverified": [
    {"target": "monarch-news", "pages_checked": ["https://www.monarchlearningacademy.com/"],
     "finding": "no <link rel=alternate type=application/rss+xml> in page source; site uses a JS calendar",
     "suggested_next_step": "check for an iCal export or a /calendar feed"}
  ],
  "blocked_hosts": []
}
```
