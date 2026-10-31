from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.main import app
from api.routers import live
from src.core.live_trace_store import LiveTraceStore


def event(trace_id: str, seq: int, kind: str, payload: dict) -> dict:
    return {"event_id": f"{trace_id}-{seq}", "trace_id": trace_id, "client_seq": seq,
            "event_type": kind, "timestamp": datetime.now(timezone.utc).isoformat(), "payload": payload}


def test_node_completion_updates_existing_node_and_final_report(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "store", LiveTraceStore(tmp_path / "snapshot.sqlite"))
    trace_id = "trace_snapshot_001"
    started = {"id": f"{trace_id}:strategy_decision:1", "label": "strategy", "node_type": "strategy_decision",
               "agent": "interrogator", "display_content": "running", "metadata": {}}
    completed = {**started, "display_content": "completed"}
    events = [
        event(trace_id, 1, "trace_started", {"project": "test", "scenario": "runtime", "session_id": "s1"}),
        event(trace_id, 2, "node_started", {"node": started}),
        event(trace_id, 3, "node_completed", {"node": completed}),
        event(trace_id, 4, "trace_completed", {"metadata": {"status": "completed"}}),
    ]
    with TestClient(app) as client:
        response = client.post("/api/v1/live/events/batch", json={"events": list(reversed(events))})
        assert response.status_code == 200
        snapshot = client.get(f"/api/v1/live/traces/{trace_id}").json()
    assert len(snapshot["trace"]["nodes"]) == 1
    assert snapshot["trace"]["nodes"][0]["display_content"] == "completed"
    assert snapshot["trace"]["nodes"][0]["metadata"]["runtime_status"] == "completed"
    assert snapshot["status"] == "completed"
    assert snapshot["report"]["risk_report"]["trace_id"] == trace_id


def test_optional_live_api_key_is_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "store", LiveTraceStore(tmp_path / "auth.sqlite"))
    monkeypatch.setenv("GRAPHGUARD_API_KEY", "test-secret")
    with TestClient(app) as client:
        assert client.get("/api/v1/live/traces").status_code == 401
        assert client.get("/api/v1/live/traces", headers={"Authorization": "Bearer test-secret"}).status_code == 200


def test_trace_list_exposes_generic_source_and_policy_pack(tmp_path, monkeypatch):
    monkeypatch.setattr(live, "store", LiveTraceStore(tmp_path / "sources.sqlite"))
    trace_id = "trace_callback_source"
    events = [
        event(
            trace_id,
            1,
            "trace_started",
            {
                "project": "framework-demo",
                "scenario": "rag",
                "session_id": "s1",
                "metadata": {"policy_pack": "generic_default"},
            },
        )
    ]
    events[0]["payload"]["metadata"]["adapter"] = "langchain_callback"
    events[0]["payload"]["source"] = "langchain_callback"
    with TestClient(app) as client:
        assert client.post("/api/v1/live/events/batch", json={"events": events}).status_code == 200
        item = client.get("/api/v1/live/traces").json()["items"][0]
    assert item["project"] == "framework-demo"
    assert item["scenario"] == "rag"
    assert item["policy_pack"] == "generic_default"
    assert item["source"] == "callback"
