#!/usr/bin/env python3
"""TOS hosted MCP server — streamable-HTTP + REST on one ASGI app (the remote leg).

This is the leg that serves claude.ai/Cowork/mobile custom connectors AND ChatGPT Developer
mode, which are all brokered from vendor clouds and therefore need a PUBLIC HTTPS endpoint —
localhost serves nobody remote (the load-bearing platform fact behind this design). It uses the
official `mcp` 2.x SDK (`MCPServer`; the pre-2.0 `FastMCP` import no longer exists) because a
hosted deployment already owns a container where pinned dependencies are normal; the LOCAL leg
(tools/mcp_server.py) stays stdlib so teachers install nothing.

One ASGI app serves:
  /mcp            streamable-HTTP MCP (claude.ai connectors, ChatGPT Developer mode)
  /v1/{tool}      plain REST POST per tool — the Custom GPT Actions fallback
  /openapi.json   the Actions schema (generated from the registry) with THIS host substituted
  /healthz        liveness

Tools come from tools/mcp_tooldefs.py — the single registry. The SDK derives input schemas from
the typed wrapper signatures below, so those annotations carry every enum and bound the registry
declares; schema_parity() asserts the two sides stay equivalent and sync_check check 23 runs it
(the registry's own _validate_args is still the authoritative enforcement at call time, on every
leg). The committed Actions artifacts are separately gated by check 22.

Deployment posture (see deploy/mcp/README.md, security/SECURITY_REVIEW.md):
  STATELESS · standards-data-only · no identity · request bodies never logged · treat as
  public. No-auth by default (MCP connectors on either platform cannot send custom headers, and
  the data is the public CPALMS-derived corpus; Custom GPT Actions CAN send headers — the
  default is about the connector door, not a platform limit). Districts wanting gating may set
  TOS_MCP_TOKEN (env only); it covers /mcp and /v1/* via middleware, never per-route. Per-IP
  token-bucket rate limiting in-process on every path. Binds 127.0.0.1 unless TOS_MCP_HOST says
  otherwise (the container sets 0.0.0.0; TLS terminates at the host).

Usage:
  python3 tools/mcp_http_server.py                 # serve (env: TOS_MCP_HOST/PORT/TOKEN)
  python3 tools/mcp_http_server.py --self-test     # in-memory Client round-trip (CI)
Requires: python3 tools/deps_preflight.py --install mcp_server   (tools/requirements-mcp.txt)
"""
# NO `from __future__ import annotations` here, deliberately: the SDK derives each tool's
# advertised inputSchema by calling inspect.signature(fn, eval_str=True), which resolves string
# annotations against MODULE globals only. With PEP 563 on, the constrained aliases defined
# inside build_mcp() are invisible to that eval and every tool raises InvalidSignature. Runtime
# annotations cost nothing here (this leg already requires Python >= 3.10 for the SDK).
import argparse
import hmac
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcp_tooldefs  # noqa: E402  (stdlib registry — importable before the SDK check)


SDK_MIN_MAJOR = 2   # MCPServer lives here; 1.x has FastMCP instead and cannot serve this file


def _need_sdk():
    """None when the SDK is usable, else a diagnostic that names the ACTUAL problem.

    Three states, not two (audit H-5). The old version had two, and the missing third bit a
    developer for real: installing the security_scan capability pulled semgrep, which pins
    `mcp<2`, so pip downgraded mcp 2.0.0 to 1.29.0 in the shared venv. `from mcp.server import
    MCPServer` then raised ImportError, and this function reported "not installed" — false, mcp
    was installed — with a fix (`--install mcp_server`) that reinstalls the same requirements into
    the same venv and does nothing. Never claim absence when the package is present."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        return _sdk_diagnosis(None, False)
    try:
        from importlib.metadata import version
        installed = version("mcp")
    except Exception:  # noqa: BLE001
        installed = "unknown"
    try:
        from mcp.server import MCPServer  # noqa: F401
        return None
    except ImportError as exc:
        return _sdk_diagnosis(installed, True, str(exc))


def _sdk_diagnosis(installed, present: bool, exc: str = ""):
    """The message for each state — separated from the probing so the self-test can exercise the
    downgrade case, which is otherwise only reproducible by breaking a real environment."""
    if not present:
        return ("the `mcp` SDK is not installed — this HOSTED leg needs it "
                "(the local stdio server tools/mcp_server.py does not).\n"
                "  fix: python3 tools/deps_preflight.py --install mcp_server")
    try:
        major = int(str(installed).split(".")[0])
    except ValueError:
        major = SDK_MIN_MAJOR
    if major < SDK_MIN_MAJOR:
        return (f"the `mcp` SDK is INSTALLED but too old: version {installed} "
                f"(need >= {SDK_MIN_MAJOR}.0.0 — `MCPServer` does not exist in 1.x, which ships "
                f"`FastMCP` instead).\n"
                f"  likely cause: something in the same environment pins `mcp<2` and pip "
                f"downgraded it. semgrep does exactly this — if the security_scan capability "
                f"shares this venv, that is your answer.\n"
                f"  fix: python3 tools/deps_preflight.py --install mcp_server  (the capability is "
                f"marked isolated, so it installs into .harvest-venv-mcp_server where nothing "
                f"else can downgrade it), then run this file with that interpreter: "
                f"python3 tools/deps_preflight.py --python-path mcp_server")
    return (f"the `mcp` SDK is installed (version {installed}) but `mcp.server.MCPServer` could "
            f"not be imported: {exc}\n"
            f"  this is not the missing-package case; the installation is broken or the API "
            f"moved. Check the SDK changelog before changing this file.")


def build_mcp():
    """The MCPServer with all 8 registry tools as typed wrappers (readOnlyHint on every one).

    The type annotations are LOAD-BEARING, not decoration: the SDK derives each tool's
    advertised inputSchema from them. Shipped in 69182cd with bare `str`/`int`, which silently
    dropped every enum, bound and maxItems the registry promises — so a claude.ai teacher got a
    free-text `subject` while a ChatGPT teacher got a constrained one (finding H-2). Literal[...]
    -> enum, Annotated[int, Field(ge/le)] -> minimum/maximum, Field(max_length) -> maxItems.
    schema_parity() below asserts the two sides stay equivalent; sync_check check 23 runs it."""
    from typing import Annotated, Literal

    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations
    from pydantic import Field

    mcp = MCPServer("tos-tools", instructions=mcp_tooldefs.server_instructions())
    ro = ToolAnnotations(readOnlyHint=True)
    call = mcp_tooldefs.call_tool
    by = {t["name"]: t["description"] for t in mcp_tooldefs.TOOLS}
    Subject = Literal["math", "ela", "science", "social_studies", "computer_science", "eld"]
    Limit = Annotated[int, Field(ge=1, le=10)]

    def search_standards(query: str, grade: str | None = None, subject: Subject | None = None,
                         limit: Limit = 5) -> dict:
        return call("search_standards", {"query": query, "grade": grade, "subject": subject,
                                         "limit": limit})

    def lookup_course_code(query: str, limit: Limit = 5) -> dict:
        return call("lookup_course_code", {"query": query, "limit": limit})

    def lookup_school(query: str, district: str | None = None, private: bool = False,
                      limit: Limit = 5) -> dict:
        return call("lookup_school", {"query": query, "district": district,
                                      "private": private, "limit": limit})

    def standard_resources(standard_code: str, limit: Limit = 5) -> dict:
        return call("standard_resources", {"standard_code": standard_code, "limit": limit})

    def verify_standard_codes(codes: Annotated[list[str], Field(min_length=1, max_length=25)],
                              standards_set: str | None = None,
                              grade_band: str | None = None,
                              standards_applicability: str | None = None) -> dict:
        return call("verify_standard_codes",
                    {"codes": codes, "standards_set": standards_set,
                     "grade_band": grade_band,
                     "standards_applicability": standards_applicability})

    def check_citation_mutation(cited: str, origin: str) -> dict:
        return call("check_citation_mutation", {"cited": cited, "origin": origin})

    def validate_artifact(artifact: dict) -> dict:
        return call("validate_artifact", {"artifact": artifact})

    def index_status() -> dict:
        return call("index_status", {})

    for fn in (search_standards, lookup_course_code, lookup_school, standard_resources,
               verify_standard_codes, check_citation_mutation, validate_artifact,
               index_status):
        mcp.add_tool(fn, name=fn.__name__, description=by[fn.__name__], annotations=ro)
    return mcp


# ------------------------------------------------------------------------------- schema parity
# The gate that would have caught H-2. sync_check check 22 diffs the committed Actions artifacts
# against a fresh REGISTRY render — registry vs registry, so a divergence between the registry and
# what the SDK derives for Claude is structurally invisible to it. That is how all 8 tools came to
# advertise different schemas on the two platforms for a full release.
_CONSTRAINTS = ("type", "enum", "minimum", "maximum", "minItems", "maxItems", "items_type")


def _norm_prop(spec: dict) -> dict:
    """One property reduced to the constraints that change what a caller may send.

    Dropped on purpose: `title` (SDK-only), `description` (registry-only prose — the two sides
    describe the same field for different audiences), and `default` unless the REGISTRY declares
    one (pydantic materializes `default: null` for every optional parameter; comparing that to a
    registry that stays silent would report noise on every optional field forever).

    `anyOf: [X, {"type": "null"}]` is how the SDK spells an optional parameter — unwrapped to X,
    because the registry spells the same thing by omitting the field from `required`. This is why
    parity is compared SEMANTICALLY: byte-equality between the two schemas cannot hold."""
    branches = [b for b in spec.get("anyOf", []) if b.get("type") != "null"]
    if len(branches) == 1:
        spec = {**{k: v for k, v in spec.items() if k != "anyOf"}, **branches[0]}
    elif branches:
        spec = {**{k: v for k, v in spec.items() if k != "anyOf"},
                "type": sorted(str(b.get("type")) for b in branches)}
    out = {}
    for key in _CONSTRAINTS:
        if key == "items_type":
            if isinstance(spec.get("items"), dict):
                out["items_type"] = spec["items"].get("type")
        elif key in spec:
            out[key] = sorted(spec[key]) if key == "enum" else spec[key]
    return out


def _norm_schema(schema: dict, *, sdk: bool) -> dict:
    props = {n: _norm_prop(s) for n, s in (schema.get("properties") or {}).items()}
    # additionalProperties: the registry says false everywhere; the SDK's derivation has no way to
    # say it at all (it is not an add_tool option, and rewriting mcp._tool_manager schemas is the
    # private-API surgery this design rejected). Absent on the SDK side is therefore normalized to
    # false — accurate in behaviour, not a coercion of a real difference: an unexpected keyword is
    # rejected twice over, by _validate_args in the registry (which every leg funnels through) and
    # by the SDK's own pydantic model. An explicit `true` still fails parity, which is the case
    # that would actually mean unknown keys are accepted.
    extra = schema.get("additionalProperties", False if sdk else None)
    return {"properties": props, "required": sorted(schema.get("required") or []),
            "additionalProperties": bool(extra)}


def schema_parity() -> list[str]:
    """Issues where the Claude-side (SDK-derived) schema and the GPT-side (registry) schema differ.

    Returns sync_check-shaped strings; empty means a teacher on claude.ai and a teacher on ChatGPT
    are held to the same contract. Raises ImportError when the `mcp` SDK is absent — check 23
    treats that as a SKIP (the hosted leg is an optional capability), unlike checks 21/22."""
    import anyio

    registry = {t["name"]: t["inputSchema"] for t in mcp_tooldefs.TOOLS}
    return _parity(registry, anyio.run(build_mcp().list_tools))


def _parity(registry: dict, tools) -> list[str]:
    """The comparison itself, split out so the self-test can feed it a constraint-stripped
    server and prove the gate fails on exactly the shape that shipped (finding H-2)."""
    issues = []
    for name in sorted(set(registry) | {t.name for t in tools}):
        sdk_tool = next((t for t in tools if t.name == name), None)
        if sdk_tool is None or name not in registry:
            issues.append(f"  x {name}: advertised on "
                          f"{'ChatGPT/registry' if sdk_tool is None else 'Claude/SDK'} only — "
                          f"every tool must exist on both doors")
            continue
        reg, sdk = registry[name], sdk_tool.input_schema
        n_reg, n_sdk = _norm_schema(reg, sdk=False), _norm_schema(sdk, sdk=True)
        for key in ("required", "additionalProperties"):
            if n_reg[key] != n_sdk[key]:
                issues.append(f"  x {name}.{key}: registry {n_reg[key]!r} != SDK {n_sdk[key]!r}")
        for prop in sorted(set(n_reg["properties"]) | set(n_sdk["properties"])):
            r, s = n_reg["properties"].get(prop), n_sdk["properties"].get(prop)
            if r is None or s is None:
                issues.append(f"  x {name}.{prop}: property present only in "
                              f"{'the registry (ChatGPT)' if s is None else 'the SDK (Claude)'}")
                continue
            for key in sorted(set(r) | set(s)):
                if r.get(key) != s.get(key):
                    issues.append(f"  x {name}.{prop}: {key} present in registry as "
                                  f"{r.get(key)!r}, in SDK schema as {s.get(key)!r} — the two "
                                  f"doors would enforce different rules (fix the annotation in "
                                  f"build_mcp(), never the registry, unless the registry is wrong)")
            if reg.get("properties", {}).get(prop, {}).get("default") is not None:
                rd = reg["properties"][prop]["default"]
                sd = _sdk_default(sdk, prop)
                if rd != sd:
                    issues.append(f"  x {name}.{prop}: default {rd!r} in the registry, {sd!r} in "
                                  f"the SDK schema")
    return issues


def _sdk_default(schema: dict, prop: str):
    return (schema.get("properties") or {}).get(prop, {}).get("default")


# --------------------------------------------------------------------------- REST + app assembly
class _Bucket:
    """Tiny in-process per-IP token bucket. Refuses with 429; never queues.

    Per-process by construction: N replicas mean N buckets, so this is a crude abuse brake, not a
    quota. Front it with the platform's limiter for anything serious (deploy/mcp/README.md)."""

    MAX_KEYS = 10000

    def __init__(self, rate_per_min: int = 60, burst: int = 20):
        self.rate, self.burst, self.state = rate_per_min / 60.0, burst, {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens, last = self.state.get(key, (self.burst, now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        allowed = tokens >= 1
        self.state[key] = (tokens - 1 if allowed else tokens, now)
        if len(self.state) > self.MAX_KEYS:
            self._evict(key)
        return allowed

    def _evict(self, active: str) -> None:
        """Bounded memory without punishing the caller being served (L-3).

        The old one-liner popped the oldest INSERTED key, which under a flood of fresh IPs can be
        the key of the request in flight — evicting it resets that caller to a full burst, i.e.
        the limiter forgets exactly the client it is throttling. Fully-refilled buckets go first
        (they are indistinguishable from a new client), then the least-recently-seen; `active` is
        never a candidate."""
        now = time.monotonic()
        idle = [(k, v) for k, v in self.state.items() if k != active]
        if not idle:
            return
        victims = [k for k, (tok, last) in idle
                   if min(self.burst, tok + (now - last) * self.rate) >= self.burst]
        if not victims:
            victims = [min(idle, key=lambda kv: kv[1][1])[0]]   # least recently seen
        for k in victims:
            self.state.pop(k, None)


#: Paths reachable without TOS_MCP_TOKEN (still rate-limited). Both are exempt for a concrete
#: deployment reason, not convenience: platform health probes (Cloud Run, Fly, App Runner) cannot
#: send a bearer, so gating /healthz means the service never reports healthy and the deploy never
#: comes up; and ChatGPT's "Import from URL" fetches /openapi.json from a browser with no auth, so
#: gating it closes Door 4 entirely. Neither returns corpus data — the token guards the DATA paths
#: (/mcp and /v1/*), which is the whole point of having one.
TOKEN_EXEMPT_PATHS = ("/healthz", "/openapi.json")


def _gate_middleware(app, bucket: "_Bucket", token: str):
    """Rate limit + optional bearer for EVERY path, /mcp included.

    AUDIT H-3: this was a per-route helper called from rest_tool() only, so /v1/* was gated and
    /mcp — mounted as a sub-app — was not. Per-route gating structurally cannot reach inside
    Mount("/", streamable_http_app()); that is the bug, so the fix has to be middleware. While it
    was broken, SECURITY_REVIEW.md and deploy/mcp/README.md both claimed the endpoint was
    limited and token-gated; those claims are retracted in the same commit as this fix."""
    from starlette.responses import JSONResponse

    async def middleware(scope, receive, send):
        if scope["type"] != "http":
            return await app(scope, receive, send)
        client = scope.get("client") or ()
        ip = client[0] if client else "?"
        path = scope.get("path", "")
        refuse = None
        if not bucket.allow(ip):                       # rate limit FIRST: cheap and universal
            refuse = JSONResponse({"error": "rate_limited"}, status_code=429)
        elif token and path not in TOKEN_EXEMPT_PATHS:
            header = ""
            for k, v in scope.get("headers") or ():
                if k == b"authorization":
                    header = v.decode("latin-1")
                    break
            # compare_digest, not == : a plain compare leaks the token prefix through timing
            # to an endpoint whose entire threat model is "anonymous internet" (L-2).
            if not hmac.compare_digest(header, f"Bearer {token}"):
                refuse = JSONResponse({"error": "unauthorized"}, status_code=401)
        if refuse is not None:
            return await refuse(scope, receive, send)
        return await app(scope, receive, send)

    return middleware


#: REST status per error kind (M-4). Any non-2xx makes ChatGPT tell the teacher "the action
#: failed" and swallow the body — so an OPERATIONAL answer the model should relay must be 200.
#: index_unavailable/index_corrupt are exactly that: the tool worked, answered honestly, and
#: carries the fix text; returning 400 turned the honesty tool into a dead end.
_ERROR_STATUS = {"index_unavailable": 200, "index_corrupt": 200,
                 "unknown tool": 404, "invalid_arguments": 400,
                 "artifact must be": 400}


def _status_for(out: dict) -> int:
    err = out.get("error")
    if not err:
        return 200
    for key, status in _ERROR_STATUS.items():
        if str(err).startswith(key):
            return status
    return 500          # a genuine server-side failure (the call_tool chokepoint caught something)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in ("1", "true", "yes", "on")


def _transport_security():
    """DNS-rebinding protection: OFF unless TOS_MCP_ALLOWED_HOSTS names the hosts (M-1).

    Stated explicitly rather than left to the default, because the default is the surprising
    one and the naive "hardening" breaks production. Passing transport_security=None makes the
    SDK build TransportSecuritySettings(enable_dns_rebinding_protection=False) — validation
    skipped, which is why a deployment behind a load balancer works at all. Constructing the
    settings object with protection ON and an empty allow-list would reject EVERY request whose
    Host header is the LB's. So: opt-in, and only a deployer who knows their public hostnames
    can turn it on."""
    from mcp.server.transport_security import TransportSecuritySettings

    hosts = [h.strip() for h in os.environ.get("TOS_MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if not hosts:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True, allowed_hosts=hosts,
        allowed_origins=[f"https://{h}" for h in hosts])


def public_url(request) -> str:
    """The base URL to advertise in the OpenAPI document (M-2).

    ChatGPT Actions requires TLS on 443 and rejects the import outright if servers[0].url is
    http:// or an internal name — and that is exactly what request.base_url renders behind a
    terminating load balancer. Resolution order: TOS_MCP_PUBLIC_URL (a required deploy step,
    documented) -> base_url with the scheme corrected from x-forwarded-proto -> base_url."""
    explicit = os.environ.get("TOS_MCP_PUBLIC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    url = str(request.base_url).rstrip("/")
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    if proto == "https" and url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


def build_app(mcp):
    """One ASGI app: /mcp (SDK) + /v1/{tool} + /openapi.json + /healthz, all behind the gate."""
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    import export_actions_schema
    bucket = _Bucket()
    token = os.environ.get("TOS_MCP_TOKEN", "")

    async def rest_tool(request: Request):
        try:
            args = await request.json()
        except Exception:
            return JSONResponse({"error": "body must be a JSON object"}, status_code=400)
        out = mcp_tooldefs.call_tool(request.path_params["tool"],
                                     args if isinstance(args, dict) else {})
        return JSONResponse(out, status_code=_status_for(out))

    async def openapi(request: Request):
        doc = export_actions_schema.render_actions()
        doc["servers"] = [{"url": public_url(request)}]
        return JSONResponse(doc)

    async def healthz(request: Request):
        # public_url is echoed so a deployer sees what ChatGPT will be handed BEFORE attempting
        # the import — the failure it prevents shows up at a teacher's step, not the deployer's.
        return JSONResponse({"ok": True, "tools": len(mcp_tooldefs.TOOLS),
                             "public_url": public_url(request),
                             "public_url_pinned": bool(os.environ.get("TOS_MCP_PUBLIC_URL")),
                             "stateless": _env_bool("TOS_MCP_STATELESS", True)})

    app = Starlette(routes=[
        Route("/v1/{tool}", rest_tool, methods=["POST"]),
        Route("/openapi.json", openapi),
        Route("/healthz", healthz),
        # stateless_http defaults to False in the SDK, i.e. in-process sessions — on the
        # scale-to-zero / multi-replica hosts deploy/mcp/README.md recommends, a teacher's second
        # request can land on a replica that never saw the first, producing intermittent "session
        # not found" on BOTH platforms (M-1). These 8 tools are request/response, so the cost of
        # stateless (no resumable streaming) is nil. Env escape hatch for a single pinned instance.
        Mount("/", app=mcp.streamable_http_app(
            stateless_http=_env_bool("TOS_MCP_STATELESS", True),
            json_response=_env_bool("TOS_MCP_JSON_RESPONSE", False),
            transport_security=_transport_security())),
    ])
    return _gate_middleware(app, bucket, token)


def serve() -> int:
    missing = _need_sdk()
    if missing:
        print(missing, file=sys.stderr)
        return 2
    import uvicorn
    host = os.environ.get("TOS_MCP_HOST", "127.0.0.1")
    port = _port()
    if port is None:
        return 2
    mcp = build_mcp()
    stateless = _env_bool("TOS_MCP_STATELESS", True)
    if not os.environ.get("TOS_MCP_PUBLIC_URL"):
        print("[tos-tools http] TOS_MCP_PUBLIC_URL is unset — /openapi.json will advertise "
              "whatever host the request arrives with. Behind a load balancer that can render "
              "http:// or an internal name, which ChatGPT Actions rejects at import. Set it to "
              "your public https:// base URL.", file=sys.stderr)
    print(f"[tos-tools http] {len(mcp_tooldefs.TOOLS)} read-only tools · /mcp + /v1/* + "
          f"/openapi.json on {host}:{port} · "
          f"{'stateless' if stateless else 'STATEFUL (pinned instance)'}, standards-data-only",
          file=sys.stderr)
    # forwarded_allow_ips: without it uvicorn ignores X-Forwarded-*, so behind a load balancer
    # request.client.host is the LB for every caller and the per-IP rate limiter degrades to ONE
    # GLOBAL BUCKET (M-2 — it is a limiter fix as much as a URL fix). "*" trusts the header, which
    # is only safe because the LB terminates in front; a container exposed directly would let a
    # caller spoof its own rate-limit key.
    uvicorn.run(build_app(mcp), host=host, port=port, log_level="warning",
                forwarded_allow_ips=os.environ.get("TOS_MCP_FORWARDED_ALLOW_IPS", "127.0.0.1"),
                access_log=False)  # request bodies/paths never logged — the privacy posture
    return 0


def _port():
    """TOS_MCP_PORT as an int, or None after explaining the refusal (L-10).

    int(os.environ[...]) raised a bare ValueError traceback on a typo'd env var — on a container
    host that is a crash loop whose logs say "invalid literal for int()" and nothing about which
    knob is wrong."""
    raw = os.environ.get("TOS_MCP_PORT", "8033").strip()
    if raw.isdigit() and 1 <= int(raw) <= 65535:
        return int(raw)
    print(f"TOS_MCP_PORT={raw!r} is not a port number (1-65535) — refusing to start rather than "
          f"crash-looping on a typo.", file=sys.stderr)
    return None


# ------------------------------------------------------------------------------------ self-test
def self_test() -> int:
    missing = _need_sdk()
    if missing:
        print("FAIL " + missing)
        return 1
    import anyio
    from mcp import Client
    fails = 0

    def ck(name: str, ok: bool) -> None:
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    async def run() -> None:
        mcp = build_mcp()
        async with Client(mcp) as client:
            tools = await client.list_tools()
            ck("in-memory Client: 8 tools listed", len(tools.tools) == 8)
            ck("readOnlyHint survives the SDK on every tool",
               all(t.annotations and t.annotations.read_only_hint for t in tools.tools))
            r = await client.call_tool("check_citation_mutation",
                                       {"cited": "count to 1000",
                                        "origin": "count to 100 with support"})
            body = json.loads(r.content[0].text)
            ck("call round-trip: mutation flags flow through the SDK envelope",
               body["faithful"] is False)
            r = await client.call_tool("verify_standard_codes",
                                       {"codes": ["MA.999.ZZ.9.9"]})
            body = json.loads(r.content[0].text)
            ck("fabricated code blocking survives the SDK",
               "MA.999.ZZ.9.9" in body.get("blocking", []))
    anyio.run(run)

    # --- H-2: the two doors advertise the same contract, and the gate can prove a violation ---
    ck("schema parity: registry (ChatGPT) == SDK-derived (Claude) on all 8 tools",
       schema_parity() == [])

    import anyio
    from mcp.server import MCPServer
    from mcp.types import ToolAnnotations

    def _stripped_tools():
        """THE BROKEN TWIN — the wrapper exactly as it shipped in 69182cd: bare `str`/`int`
        annotations. This is what the SDK advertised to every claude.ai teacher while ChatGPT
        got the constrained registry schema."""
        twin = MCPServer("twin")

        def search_standards(query: str, grade: str = None, subject: str = None,
                             limit: int = 5) -> dict:
            return {}
        twin.add_tool(search_standards, name="search_standards", description="twin",
                      annotations=ToolAnnotations(readOnlyHint=True))
        return anyio.run(twin.list_tools)

    twin_issues = _parity({t["name"]: t["inputSchema"] for t in mcp_tooldefs.TOOLS
                           if t["name"] == "search_standards"}, _stripped_tools())
    ck("broken twin: a constraint-stripped wrapper is caught, naming the enum",
       any("search_standards.subject" in i and "enum" in i for i in twin_issues))
    ck("broken twin: the dropped limit bounds are caught too",
       any("search_standards.limit" in i and ("minimum" in i or "maximum" in i)
           for i in twin_issues))

    b = _Bucket(rate_per_min=60, burst=2)
    ck("rate limit: burst honored then refused",
       b.allow("ip") and b.allow("ip") and not b.allow("ip"))

    # --- L-3: eviction must never hand the caller being throttled a fresh burst ---
    b2 = _Bucket(rate_per_min=1, burst=1)
    b2.MAX_KEYS = 3
    for i in range(6):
        b2.allow(f"flood-{i}")
    b2.allow("victim")                                  # spends victim's only token
    ck("bucket eviction keeps the active caller's state (never resets its burst)",
       "victim" in b2.state and not b2.allow("victim"))
    ck("bucket eviction bounds memory", len(b2.state) <= b2.MAX_KEYS + 1)

    # --- H-3: the gate covers /mcp, not just /v1/* (the finding), with the exemptions the
    # deploy path needs. Driven as raw ASGI so the assertions are about the MOUNTED app, which
    # is exactly what per-route gating could not reach. ---
    def _call(app, path, headers=(), method="POST"):
        status = {}

        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(msg):
            if msg["type"] == "http.response.start":
                status["code"] = msg["status"]

        async def go():
            await app({"type": "http", "method": method, "path": path, "raw_path": path.encode(),
                       "headers": list(headers), "query_string": b"", "client": ("9.9.9.9", 1),
                       "server": ("test", 80), "scheme": "http", "root_path": "",
                       "http_version": "1.1", "asgi": {"version": "3.0", "spec_version": "2.1"}},
                      receive, send)
        anyio.run(go)
        return status.get("code")

    # The B105 suppression below is for a throwaway value, set and unset inside this self-test to
    # prove the gate refuses a caller without it: not a credential, and it reaches no deployment.
    os.environ["TOS_MCP_TOKEN"] = "s3cret"  # nosec B105
    try:
        gated = build_app(build_mcp())
        ck("/mcp is token-gated (H-3: it was wide open while the docs said otherwise)",
           _call(gated, "/mcp") == 401)
        ck("/v1/* stays token-gated", _call(gated, "/v1/index_status") == 401)
        ck("/healthz is token-exempt so platform probes can bring the deploy up",
           _call(gated, "/healthz", method="GET") == 200)
        ck("/openapi.json is token-exempt so ChatGPT's Import-from-URL still works",
           _call(gated, "/openapi.json", method="GET") == 200)
        ck("a wrong token is refused",
           _call(gated, "/mcp", [(b"authorization", b"Bearer wrong")]) == 401)
    finally:
        os.environ.pop("TOS_MCP_TOKEN", None)

    # No token set — the shipped default. Spend the burst on the exempt path (proving L-1: exempt
    # still means rate-limited), then /mcp must be refused BEFORE reaching the mounted SDK app.
    open_app = build_app(build_mcp())
    spent = [_call(open_app, "/healthz", method="GET") for _ in range(_Bucket().burst + 2)]
    ck("token-exempt paths are still rate-limited (L-1)", spent[-1] == 429)
    ck("/mcp is rate-limited even with no token set — the limiter runs before the mount",
       _call(open_app, "/mcp") == 429)
    # --- M-2 / L-10: the URL ChatGPT is handed, and the env knobs around it ---
    class _Req:
        def __init__(self, base, headers=None):
            self.base_url, self.headers = base, headers or {}

    os.environ["TOS_MCP_PUBLIC_URL"] = "https://tools.example.org/"
    ck("public_url: an explicit TOS_MCP_PUBLIC_URL wins and loses its trailing slash",
       public_url(_Req("http://10.0.0.7:8033/")) == "https://tools.example.org")
    os.environ.pop("TOS_MCP_PUBLIC_URL")
    ck("public_url: x-forwarded-proto https upgrades the scheme behind a terminating LB",
       public_url(_Req("http://tools.example.org/",
                       {"x-forwarded-proto": "https, http"})) == "https://tools.example.org")
    ck("public_url: with neither signal it reports what it actually sees, no invention",
       public_url(_Req("http://127.0.0.1:8033/")) == "http://127.0.0.1:8033")

    os.environ["TOS_MCP_PORT"] = "not-a-port"
    ck("TOS_MCP_PORT: a typo is refused with an explanation, not a ValueError crash loop",
       _port() is None)
    os.environ["TOS_MCP_PORT"] = "70000"
    ck("TOS_MCP_PORT: out-of-range is refused too", _port() is None)
    os.environ["TOS_MCP_PORT"] = "9001"
    ck("TOS_MCP_PORT: a real port is accepted", _port() == 9001)
    os.environ.pop("TOS_MCP_PORT")

    # --- M-1: stateless by default, and DNS-rebinding protection stated rather than defaulted ---
    ck("stateless_http defaults ON (scale-to-zero hosts) and the env can pin it off",
       _env_bool("TOS_MCP_STATELESS", True) and not _env_bool("TOS_MCP_STATELESS", False))
    ts = _transport_security()
    ck("transport security: protection explicitly OFF unless hosts are named — enabling it with "
       "an empty allow-list would reject every request behind an LB",
       ts.enable_dns_rebinding_protection is False)
    os.environ["TOS_MCP_ALLOWED_HOSTS"] = "tools.example.org, tos.example.net"
    ts2 = _transport_security()
    os.environ.pop("TOS_MCP_ALLOWED_HOSTS")
    ck("transport security: naming hosts turns protection on for exactly those hosts",
       ts2.enable_dns_rebinding_protection and
       ts2.allowed_hosts == ["tools.example.org", "tos.example.net"])

    # --- H-5: the diagnostic must never call an installed-but-downgraded SDK "not installed" ---
    downgraded = _sdk_diagnosis("1.29.0", True, "cannot import name 'MCPServer'")
    ck("wrong-major SDK: reported as INSTALLED but too old, naming the version",
       "1.29.0" in downgraded and "not installed" not in downgraded)
    ck("wrong-major SDK: names semgrep, the actual cause, and the isolated venv",
       "semgrep" in downgraded and ".harvest-venv-mcp_server" in downgraded)
    ck("absent SDK still says absent", "not installed" in _sdk_diagnosis(None, False))
    ck("present-but-broken is its own message, not the downgrade one",
       "not the missing-package case" in _sdk_diagnosis("2.0.0", True, "boom"))
    ck("the live environment satisfies the floor", _need_sdk() is None)

    # --- M-4: the REST status table. A wrong status makes ChatGPT report a failed action and
    # throw away a body that was telling the teacher exactly how to fix things. ---
    ck("index_unavailable is 200 — an honest operational answer, not a failed action",
       _status_for({"error": "index_unavailable", "fix": "run offline_index.py --build"}) == 200)
    ck("index_corrupt is 200 for the same reason",
       _status_for({"error": "index_corrupt"}) == 200)
    ck("a bad argument is the caller's fault: 400",
       _status_for({"error": "invalid_arguments", "issues": []}) == 400)
    ck("an unknown tool is 404", _status_for({"error": "unknown tool: 'nope'"}) == 404)
    ck("an unexpected handler failure is 500, not 400",
       _status_for({"error": "DatabaseError: file is not a database"}) == 500)
    ck("a successful call is 200", _status_for({"count": 0, "rows": []}) == 200)

    import export_actions_schema
    ck("openapi served == generated schema paths",
       set(export_actions_schema.render_actions()["paths"]) ==
       {f"/v1/{t['name']}" for t in mcp_tooldefs.list_tools()})
    print(f"self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    return self_test() if a.self_test else serve()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
