<!-- last_reviewed: 2026-08-16 | owner: mcp-maintainer -->
# Deploying the TOS hosted MCP server (maintainer/district-facing)

This is the **remote leg**: one small container that lets teachers on **claude.ai / Cowork /
mobile** (custom connectors) and **ChatGPT** (Developer mode, or Custom GPT Actions) call TOS's
verified tools. Teachers never deploy this — a district IT person or the TOS maintainer does,
once. Until someone does, nothing in the repo points at any live endpoint, by design.

**Posture (read before deploying):** stateless · standards-data-only (public CPALMS-derived
reference data) · no identity, no accounts, no student data ever server-side · request bodies
are not logged · treat the endpoint as public. No-auth by default — MCP *connectors* on either
platform cannot send custom headers, and the data is already public; set `TOS_MCP_TOKEN` (env
only) if you want bearer gating on `/mcp` and `/v1/*`, and accept that connectors then can't
use it. (Custom GPT **Actions** do support key/header auth — the no-auth default is about the
connector door and zero-config import, not a platform impossibility.)

> **RETRACTION — 2026-08-16.** The version of this page published on 2026-08-15 said the
> endpoint was rate-limited and optionally token-gated. In the code as merged, both ran only on
> `/v1/{tool}`; **`/mcp` was ungated and unthrottled**, because it is a mounted sub-app that a
> per-route check cannot reach. Anyone who deployed that image and set `TOS_MCP_TOKEN` was not
> protected on the path their teachers actually used. The gate is now ASGI middleware ahead of
> routing and covers every path; `/healthz` and `/openapi.json` stay token-exempt (still
> rate-limited) so platform health probes and ChatGPT's Import-from-URL keep working. If you
> deployed the earlier image, redeploy.

## Build + run locally (smoke test)

```bash
docker build -f deploy/mcp/Dockerfile -t tos-mcp .
docker run --rm -p 8033:8033 tos-mcp
curl -s localhost:8033/healthz          # {"ok": true, "tools": 8}
curl -s localhost:8033/openapi.json | head
```

For development against ChatGPT without a host, OpenAI's own guidance is an HTTPS tunnel
(e.g. ngrok) in front of the local port — dev only, never a production posture.

## Host it (any TLS container platform with a stable URL)

The requirements are just: HTTPS on 443 with a valid public cert, a stable base URL, and
streaming support. Any of these fit; pick what your district already uses:

- **Google Cloud Run / Fly.io / Azure Container Apps / AWS App Runner** — deploy the image,
  note the public URL. Scale-to-zero is fine (the index is baked at image build; cold starts
  are fast).
- **Not** Cloudflare Workers for this image (their MCP template is JS-only; this server is
  Python). Prefect Horizon (ex-FastMCP Cloud) is Python-native but its current free-tier terms
  were unverifiable at writing — check before budgeting a school on it.

After deploy, verify: `https://<your-host>/healthz` and `https://<your-host>/mcp` respond.

## What teachers do with the URL (their side, ~1 minute)

- **claude.ai / Cowork:** Settings → Connectors → *Add custom connector* → paste
  `https://<your-host>/mcp`. (Free plan allows one custom connector; on Team/Enterprise an
  **Owner** adds it org-wide.)
- **ChatGPT Developer mode** (where the plan/workspace allows it): Settings → *Security* →
  enable Developer mode → add the same `/mcp` URL.
- **ChatGPT Custom GPT (works on Plus, no admin):** build a GPT → Actions → *Import from URL*
  → `https://<your-host>/openapi.json` → no auth. The schema is generated from the same tool
  registry, so the two surfaces cannot drift (sync_check check 22).

## Operations notes

- Rate limiting is in-process per-IP (token bucket), applied as middleware to **every** path
  including `/mcp` — front with your platform's limiter for anything serious, since N replicas
  means N independent buckets.
- Updating: rebuild the image from a fresh clone; the index rebuilds from the committed,
  CPALMS-verified sources at build time. Version = the repo `VERSION` baked into the image.
- Rollback = redeploy the previous image. The server holds no state to migrate.
- Security review: `security/SECURITY_REVIEW.md` (hosted-endpoint section); dependency policy:
  `shared/health/dependency-policy.md` (`mcp_server` capability).
