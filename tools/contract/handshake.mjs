// R5-F2: the contract test that would have caught B2 the day MCP clients moved their default
// offer to 2025-11-25 — the OFFICIAL client library (the code Claude Code/Desktop and Codex
// actually ship) connects to tools/mcp_server.py over real pipes, lists the 8 tools, and runs
// one fabrication check. CI runs it after `npm ci` in tools/contract/ (pinned SDK).
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const server = process.argv[2] ?? "tools/mcp_server.py";
const t = new StdioClientTransport({ command: "python3", args: [server], stderr: "pipe" });
const c = new Client({ name: "tos-contract-test", version: "1.0.0" });
try {
  await c.connect(t);
  const tools = await c.listTools();
  if (tools.tools.length !== 8) throw new Error(`expected 8 tools, got ${tools.tools.length}`);
  const r = await c.callTool({ name: "verify_standard_codes",
                               arguments: { codes: ["MA.3.NSO.1.1", "MA.3.NSO.9.99"] } });
  const out = JSON.parse(r.content[0].text);
  const states = Object.fromEntries(out.results.map(x => [x.code, x.state]));
  if (states["MA.3.NSO.1.1"] !== "resolved" || states["MA.3.NSO.9.99"] === "resolved")
    throw new Error(`verification contract broken: ${JSON.stringify(states)}`);
  console.log("PASS official-client handshake + tools/list(8) + fabrication check", states);
  await c.close();
} catch (e) {
  console.error("FAIL contract:", e.message);
  process.exit(1);
}
