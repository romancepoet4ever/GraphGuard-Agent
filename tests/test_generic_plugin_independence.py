from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from api.routers import live
from src.core.live_trace_store import LiveTraceStore


ROOT = Path(__file__).resolve().parents[1]
DEMO_PATH = ROOT / "examples" / "generic_plugin_demo.py"


def _load_demo():
    spec = importlib.util.spec_from_file_location("generic_plugin_demo", DEMO_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event_payload(event) -> dict:
    payload = event.to_dict()
    payload["client_seq"] = payload.pop("seq")
    return payload


def test_demo_has_no_business_repository_imports() -> None:
    tree = ast.parse(DEMO_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = ("interrogation_agent", "app.services", "src.agents.interrogator", "src.agents.suspect", "src.agents.referee")
    assert not any(name.startswith(forbidden) for name in imported)


def test_independent_demo_sends_live_events_and_generates_reports(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(live, "store", LiveTraceStore(tmp_path / "generic.sqlite"))
    demo = _load_demo()

    with TestClient(app) as client:
        results = {}
        for scenario in ("normal", "prompt-injection", "sensitive-leak"):
            result = demo.run_scenario(scenario, api_url=None, output_dir=tmp_path / "json")
            results[scenario] = result
            output_path = Path(result["output_path"])
            assert output_path.is_file()
            response = client.post(
                "/api/v1/live/events/batch",
                json={"events": [_event_payload(event) for event in result["events"]]},
            )
            assert response.status_code == 200
            snapshot = client.get(f"/api/v1/live/traces/{result['trace_id']}").json()
            assert snapshot["status"] == "completed"
            assert snapshot["report"]["risk_report"]["trace_id"] == result["trace_id"]

        items = client.get("/api/v1/live/traces").json()["items"]

    assert all(item["project"] == "generic-plugin-demo" for item in items)
    assert all(item["policy_pack"] == "generic_default" for item in items)
    assert results["prompt-injection"]["decisions"][0]["risk_type"] == "prompt_injection"
    assert results["sensitive-leak"]["decisions"][-1]["risk_score"] >= 0.9


def test_framework_integrations_remain_optional() -> None:
    import graphguard
    from graphguard.integrations.langchain import GraphGuardCallbackHandler
    from graphguard.integrations.langgraph import GraphGuardLangGraphHook
    from graphguard.spans import Span
    from src.adapters.opentelemetry_adapter import otel_spans_to_security_trace

    assert graphguard.GraphGuardClient
    assert GraphGuardCallbackHandler and GraphGuardLangGraphHook and Span
    trace = otel_spans_to_security_trace([{"traceId": "otel", "spanId": "1", "name": "user input"}])
    assert trace["nodes"]
