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
curl -s localhost:8033/healthz          # {"ok":true,"tools":8,"public_url":…,"public_url_pinned":…,"stateless":true}
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

**Required env on any real host: `TOS_MCP_PUBLIC_URL=https://<your-host>`.** Without it the
server advertises whatever host each request arrives with, and behind a terminating load balancer
that renders `http://` or an internal name — which ChatGPT Actions rejects at import, at the
*teacher's* step, not yours.

After deploy, verify: `https://<your-host>/healthz` and `https://<your-host>/mcp` respond.
`/healthz` echoes back the exact `public_url` the OpenAPI document will advertise (plus whether
it is pinned, and whether the server is stateless) — check it before telling anyone the address.

| Env | Default | Why you'd change it |
|---|---|---|
| `TOS_MCP_PUBLIC_URL` | *(unset)* | **Set it.** The https base URL ChatGPT/Claude are given. |
| `TOS_MCP_TOKEN` | *(unset)* | Bearer gating on `/mcp` + `/v1/*`; connectors can't send it. |
| `TOS_MCP_HOST` / `TOS_MCP_PORT` | `127.0.0.1` / `8033` | The container sets host `0.0.0.0`. A non-numeric port is refused with a message instead of a crash loop. |
| `TOS_MCP_STATELESS` | `true` | Set `false` only on a single pinned instance where you want resumable streaming. |
| `TOS_MCP_FORWARDED_ALLOW_IPS` | `127.0.0.1` | Set to your LB's address (or `*` in the container) so `X-Forwarded-For` is honored — otherwise every caller shares one rate-limit bucket. Never `*` on a directly-exposed container: the key becomes spoofable. |
| `TOS_MCP_JSON_RESPONSE` | `false` | Set `true` only if your platform cannot stream SSE; the SDK then answers `/mcp` with plain JSON. |
| `TOS_MCP_ALLOWED_HOSTS` | *(unset)* | Comma-separated public hostnames; enables DNS-rebinding protection. Leave unset unless you know all of them — an empty allow-list with protection on rejects everything. |

## What teachers do with the URL (their side, ~1 minute)

- **claude.ai / Cowork:** Settings → Connectors → *Add custom connector* → paste
  `https://<your-host>/mcp`. (Free plan allows one custom connector; on Team/Enterprise an
  **Owner** adds it org-wide.)
- **ChatGPT Developer mode** (where the plan/workspace allows it): Settings → *Security* →
  enable Developer mode → add the same `/mcp` URL.
- **ChatGPT Custom GPT (works on Plus, no admin):** build a GPT → Actions → *Import from URL*
  → `https://<your-host>/openapi.json` → no auth. The schema is generated from the same tool
  registry, so the two surfaces cannot drift: **check 22** holds the committed Actions schema
  to the registry, and **check 23** holds the SDK-derived Claude schema to that same registry
  — check 22 alone could not see the second divergence, which is how all eight tools once
  advertised different rules depending on which product the teacher used.

## Operations notes

- Rate limiting is in-process per-IP (token bucket), applied as middleware to **every** path
  including `/mcp` — front with your platform's limiter for anything serious, since N replicas
  means N independent buckets.
- `POST /v1/{tool}` returns **200** for `index_unavailable` / `index_corrupt`: the tool answered
  honestly and the body carries the fix. Any non-2xx makes ChatGPT report "the action failed" and
  discard that text. 400 = bad arguments, 404 = unknown tool, 500 = a real server-side failure.
  A monitor should therefore watch `/healthz` (and the index), not REST status codes alone.
- Updating: rebuild the image from a fresh clone; the index rebuilds from the committed,
  CPALMS-verified sources at build time. Version = the repo `VERSION` baked into the image.
- Rollback = redeploy the previous image. The server holds no state to migrate.
- Security review: `security/SECURITY_REVIEW.md` (hosted-endpoint section); dependency policy:
  `shared/health/dependency-policy.md` (`mcp_server` capability).
