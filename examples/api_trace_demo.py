from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE = ROOT / "data" / "demo_traces" / "prompt_injection.json"


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit a SecurityTrace to GraphGuard-Agent API.")
    parser.add_argument("--api", default="http://127.0.0.1:8001", help="FastAPI base URL.")
    parser.add_argument("--trace", default=str(DEFAULT_TRACE), help="SecurityTrace JSON path.")
    parser.add_argument("--provider", choices=["mock", "openai", "openrouter"], default="mock")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key", default=None, help="Optional request-level API key. Prefer .env for real deployments.")
    parser.add_argument("--base-url", default=None, help="Optional OpenAI-compatible base URL, for example StepFun.")
    args = parser.parse_args()

    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    payload = {
        "trace": trace,
        "source": "api_demo",
        "model": {
            "provider": args.provider,
            "model": args.model,
            "api_key": args.api_key,
            "base_url": args.base_url,
        },
    }
    result = post_json(f"{args.api.rstrip('/')}/api/v1/analyze", payload)
    report = result["report"]
    risk = report["risk_report"]
    print(json.dumps(
        {
            "trace_id": result["trace_id"],
            "provider": result["provider"],
            "risk_type": risk.get("risk_type"),
            "risk_score": risk.get("risk_score"),
            "recommended_action": risk.get("recommended_action"),
            "agent_report": report.get("agent_report", "")[:300],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
