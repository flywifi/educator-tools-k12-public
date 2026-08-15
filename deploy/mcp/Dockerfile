# TOS hosted MCP server — stateless, standards-data-only, public-data posture.
# Serves /mcp (claude.ai connectors + ChatGPT Developer mode) and /v1/* + /openapi.json
# (Custom GPT Actions) from one process. TLS terminates at your platform (Cloud Run, Fly.io,
# any container host with HTTPS at a stable URL). See deploy/mcp/README.md.
FROM python:3.12-slim

WORKDIR /app
COPY tools/requirements-mcp.txt tools/
RUN pip install --no-cache-dir -r tools/requirements-mcp.txt

# The tool code + the committed canonical data the tools answer from. No secrets, no student
# data — the corpus is public CPALMS-derived standards/course/school reference data.
COPY tools/mcp_tooldefs.py tools/mcp_server.py tools/mcp_http_server.py \
     tools/export_actions_schema.py tools/offline_index.py tools/verify_standards.py \
     tools/validate_outputs.py tools/
COPY VERSION ./
COPY canonical-sources/ canonical-sources/
COPY shared/standards/ shared/standards/
COPY implementation/mcp/ implementation/mcp/
COPY implementation/gpt/api/actions-openapi.json implementation/gpt/api/

# Build the offline index at IMAGE BUILD time (deterministic, from the committed sources) so
# cold starts serve immediately and the running container never writes.
RUN python tools/offline_index.py --build

ENV TOS_MCP_HOST=0.0.0.0 \
    TOS_MCP_PORT=8033
EXPOSE 8033
# No TOS_MCP_TOKEN by default: the data is public and ChatGPT cannot send custom headers.
# Districts wanting Claude-side gating set it at deploy time (env only, never baked in).
CMD ["python", "tools/mcp_http_server.py"]
