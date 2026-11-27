#!/usr/bin/env python3
"""Run TOS model-facing eval cases on an OpenAI or Gemini model — cross-vendor evidence (R3).

The Claude arm (claude-session) answered each case with the TOS skills loaded. This runner gives
another vendor's model the same rules in a fixed, hashed context — the governance prompt
(implementation/gpt/api/system-prompt.md), the hub skill (teacher-core) and the case's own
SKILL.md — and the case prompt verbatim. It saves each answer to a file; judging and recording
stay with tools/eval_evidence.py --record (a judge is REQUIRED for prose assertions), under arm
`openai-responses-api` or `gemini-api`. It tests whether the TOS rules hold on that model, not the
plugin experience (no tools run here).

Usage:
  python3 tools/eval_vendor_run.py --vendor openai --list-models
  python3 tools/eval_vendor_run.py --vendor openai --model <id> --recorded --runs 3 --out <dir>
  python3 tools/eval_vendor_run.py --vendor gemini --model <id> --case lesson-planner/<name> --out <dir>
  python3 tools/eval_vendor_run.py --self-test        # offline, against a local stub server
Keys: OPENAI_API_KEY / GEMINI_API_KEY, or none when a network proxy injects them for the host.
stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_evidence  # noqa: E402  (prompt_cases — the one case registry)

ARMS = {"openai": "openai-responses-api", "gemini": "gemini-api"}
BASES = {"openai": ("TOS_OPENAI_BASE", "https://api.openai.com"),
         "gemini": ("TOS_GEMINI_BASE", "https://generativelanguage.googleapis.com")}


def _base(vendor: str) -> str:
    env, default = BASES[vendor]
    return os.environ.get(env, default).rstrip("/")


def build_context(skill_dir: Path) -> tuple[str, str]:
    """(system text, description) — governance + hub + the case's own skill folder, in that order."""
    hub = next(iter(sorted(ROOT.glob("skills/*/teacher-core"))))
    parts = ["# TOS governance (always applies)\n\n" +
             (ROOT / "implementation/gpt/api/system-prompt.md").read_text(encoding="utf-8")]
    for d in dict.fromkeys([hub, skill_dir]):
        parts.append(f"# Active skill: {d.name}\n\n" + (d / "SKILL.md").read_text(encoding="utf-8"))
    text = "\n\n".join(parts)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, f"governance+teacher-core+{skill_dir.name} sha256:{sha}"


def _post(url: str, body: dict, headers: dict, tries: int = 3) -> dict:
    data = json.dumps(body).encode("utf-8")
    for n in range(tries):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:   # nosec B310 — fixed https vendor bases
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and n < tries - 1:
                time.sleep(2 ** n)
                continue
            raise SystemExit(f"eval_vendor_run: HTTP {e.code} from {url}: {e.read()[:300]!r}")
    raise SystemExit("eval_vendor_run: retries exhausted")


def _get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:   # nosec B310 — fixed https vendor bases
        return json.loads(r.read())


def _auth(vendor: str) -> dict:
    if vendor == "openai":
        return {"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', 'proxy-injected')}"}
    return {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "proxy-injected")}


def ask(vendor: str, model: str, system: str, prompt: str) -> tuple[str, str]:
    """(answer text, served model id)."""
    if vendor == "openai":
        r = _post(f"{_base('openai')}/v1/responses",
                  {"model": model, "instructions": system, "input": prompt, "store": False},
                  _auth("openai"))
        text = "".join(c.get("text", "") for item in r.get("output", []) if item.get("type") == "message"
                       for c in item.get("content", []) if c.get("type") == "output_text")
        return text, r.get("model", model)
    r = _post(f"{_base('gemini')}/v1beta/models/{model}:generateContent",
              {"systemInstruction": {"parts": [{"text": system}]},
               "contents": [{"role": "user", "parts": [{"text": prompt}]}]}, _auth("gemini"))
    parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts if not p.get("thought")), r.get("modelVersion", model)


def list_models(vendor: str) -> list[str]:
    if vendor == "openai":
        return sorted(m["id"] for m in _get(f"{_base('openai')}/v1/models", _auth("openai")).get("data", []))
    return sorted(m["name"].split("/", 1)[-1] for m in
                  _get(f"{_base('gemini')}/v1beta/models", _auth("gemini")).get("models", []))


def run(vendor: str, model: str, case_ids: list[str], runs: int, out: Path) -> dict:
    cases = eval_evidence.prompt_cases()
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"arm": ARMS[vendor], "requested_model": model, "runs": []}
    for cid in case_ids:
        if cid not in cases:
            raise SystemExit(f"eval_vendor_run: unknown case {cid!r}")
        case, evals_path = cases[cid]
        system, desc = build_context(evals_path.parent.parent)   # the folder that owns the case
        for n in range(1, runs + 1):
            text, served = ask(vendor, model, system, case["prompt"])
            f = out / f"{cid.replace('/', '__')}__run{n}.txt"
            f.write_text(text, encoding="utf-8")
            manifest["runs"].append({"case": cid, "run": n, "file": f.name, "model": served,
                                     "context": desc})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def self_test() -> int:
    import tempfile
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    fails = 0

    def ck(name, ok):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    seen: list[dict] = []
    flaky = {"left": 1}

    class Stub(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            b = json.dumps(obj).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            if self.path == "/v1/models":
                return self._send(200, {"data": [{"id": "gpt-stub"}]})
            if self.path == "/v1beta/models":
                return self._send(200, {"models": [{"name": "models/gemini-stub"}]})
            self._send(404, {})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"path": self.path, "body": body,
                         "headers": {k.lower(): v for k, v in self.headers.items()}})
            if self.path == "/v1/responses":
                if flaky["left"]:
                    flaky["left"] -= 1
                    return self._send(429, {"error": "slow down"})
                return self._send(200, {"model": "gpt-stub-2026", "output": [
                    {"type": "reasoning", "summary": []},
                    {"type": "message", "content": [{"type": "output_text", "text": "3.NF.A.9 is not "},
                                                    {"type": "output_text", "text": "a verified code."}]}]})
            if self.path.endswith(":generateContent"):
                return self._send(200, {"modelVersion": "gemini-stub-001", "candidates": [{"content": {
                    "parts": [{"text": "thinking...", "thought": True}, {"text": "Flagged: 3.NF.A.9."}]}}]})
            self._send(404, {})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    os.environ["TOS_OPENAI_BASE"] = os.environ["TOS_GEMINI_BASE"] = base
    os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1,localhost"   # the stub is local
    for k in ("OPENAI_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(k, None)
    try:
        cid = "lesson-planner/fabricated_standard_flagged_not_cited"
        case = eval_evidence.prompt_cases()[cid][0]
        with tempfile.TemporaryDirectory(prefix="evr-") as td:
            m = run("openai", "gpt-x", [cid], 1, Path(td) / "o")
            req = [s for s in seen if s["path"] == "/v1/responses"][-1]
            ck("openai: Responses API body = model + instructions + verbatim case prompt, store off",
               req["body"]["input"] == case["prompt"] and req["body"]["store"] is False
               and "# TOS governance" in req["body"]["instructions"]
               and "# Active skill: teacher-core" in req["body"]["instructions"]
               and "# Active skill: lesson-planner" in req["body"]["instructions"])
            ck("openai: a 429 is retried, then the answer joins every output_text part",
               (Path(td) / "o" / m["runs"][0]["file"]).read_text(encoding="utf-8") == "3.NF.A.9 is not a verified code.")
            ck("openai: served model id + context sha recorded in the manifest",
               m["runs"][0]["model"] == "gpt-stub-2026" and "sha256:" in m["runs"][0]["context"]
               and m["arm"] == "openai-responses-api")
            g = run("gemini", "gemini-x", [cid], 2, Path(td) / "g")
            greq = [s for s in seen if s["path"].endswith(":generateContent")][-1]
            ck("gemini: generateContent body carries systemInstruction + the user prompt",
               greq["path"] == "/v1beta/models/gemini-x:generateContent"
               and greq["body"]["contents"][0]["parts"][0]["text"] == case["prompt"]
               and "# Active skill: lesson-planner" in greq["body"]["systemInstruction"]["parts"][0]["text"])
            ck("gemini: thought parts are dropped; 2 runs -> 2 files",
               len(g["runs"]) == 2 and (Path(td) / "g" / g["runs"][1]["file"]).read_text(encoding="utf-8") == "Flagged: 3.NF.A.9.")
            ck("auth: a placeholder key is sent when none is set (a proxy injects the real one)",
               any(s["headers"].get("authorization") == "Bearer proxy-injected" for s in seen)
               and any(s["headers"].get("x-goog-api-key") for s in seen))
            ck("list-models works for both vendors",
               list_models("openai") == ["gpt-stub"] and list_models("gemini") == ["gemini-stub"])
            d = eval_evidence.prompt_cases()[cid][1].parent.parent
            ck("context is deterministic (same repo state -> same sha)", build_context(d) == build_context(d))
            ck("every recorded case resolves to a real skill folder (atoms included)",
               all(build_context(p.parent.parent)[0] for c, p in eval_evidence.prompt_cases().values()
                   if c.get("evidence")))
            try:
                run("openai", "gpt-x", ["nope/nope"], 1, Path(td) / "x")
                ck("an unknown case is refused", False)
            except SystemExit:
                ck("an unknown case is refused", True)
    finally:
        srv.shutdown()
    print(f"eval_vendor_run self-test: {fails} failure(s)")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cross-vendor eval runner (OpenAI / Gemini arms)")
    ap.add_argument("--vendor", choices=sorted(ARMS))
    ap.add_argument("--model")
    ap.add_argument("--case", action="append", default=[])
    ap.add_argument("--recorded", action="store_true", help="every case that has Claude evidence")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default="dist/vendor-evals")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.vendor:
        ap.error("--vendor is required")
    if a.list_models:
        print("\n".join(list_models(a.vendor)))
        return 0
    ids = list(a.case)
    if a.recorded:
        ids += [cid for cid, (c, _p) in eval_evidence.prompt_cases().items() if c.get("evidence")]
    if not (a.model and ids):
        ap.error("--model and at least one --case (or --recorded) are required")
    m = run(a.vendor, a.model, list(dict.fromkeys(ids)), a.runs, ROOT / a.out)
    print(f"{len(m['runs'])} answer(s) -> {a.out}; judge each, then record with:")
    print(f"  python3 tools/eval_evidence.py --record <case> --arm {m['arm']} --model <served model> "
          f"--context '<manifest context>' --output-file <file> --judge-verdict ... --judge-by ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
