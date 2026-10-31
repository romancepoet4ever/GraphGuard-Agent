from __future__ import annotations

import asyncio
import json
import os
import threading
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.adapters.security_trace_adapter import SecurityTraceAdapter
from src.agents.detection_agent import GraphGuardDetectionAgent
from src.agents.model_clients import ModelClientConfig
from src.core.live_trace_store import LiveTraceStore
from src.detection.government_risk_engine import GovernmentRiskEngine

router = APIRouter(prefix="/api/v1/live", tags=["live-security-traces"])
store = LiveTraceStore()
adapter = SecurityTraceAdapter()
_analysis_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)


class LiveEventRequest(BaseModel):
    event_id: str
    trace_id: str
    event_type: str
    timestamp: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    client_seq: int | None = None
    session_id: str | None = None
    round_idx: int | None = None


class LiveEventBatchRequest(BaseModel):
    events: list[LiveEventRequest] = Field(default_factory=list)


def _authorize(authorization: str | None) -> None:
    expected = os.getenv("GRAPHGUARD_API_KEY", "")
    if expected and authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid GraphGuard API key")


def _analyze_latest(trace_id: str, final_event: bool = False) -> None:
    """Analyze after the ingestion response has been released to the exporter."""
    with _analysis_locks[trace_id]:
        trace = store.trace_store.get_trace(trace_id) or {}
        if not trace.get("nodes"):
            return
        try:
            if final_event:
                report = GraphGuardDetectionAgent(ModelClientConfig(provider="mock")).analyze(trace)
                report["provider"] = "deterministic"
                report["model"] = "rule-engine+template"
            else:
                graph = adapter.trace_to_security_graph(trace)
                risk_report = GovernmentRiskEngine().analyze(graph, write_audit=False)
                report = {
                    "trace_id": trace_id,
                    "project": trace.get("project", "unknown"),
                    "scenario": trace.get("scenario", "unknown"),
                    "provider": "deterministic",
                    "model": "incremental-rule-engine",
                    "risk_report": risk_report,
                    "method_results": {},
                    "agent_report": "实时阶段使用确定性规则与污点传播；Trace 完成后生成完整综合报告。",
                    "recommended_actions": risk_report.get("repair_suggestions") or [],
                }
            store.trace_store.save_report(trace_id, report, provider="deterministic", model="live-rule-engine")
        except Exception:
            # Event persistence is authoritative; analysis failure must not reject ingestion.
            return


@router.post("/events")
async def ingest_live_event(request: LiveEventRequest, background_tasks: BackgroundTasks,
                            authorization: str | None = Header(default=None)):
    _authorize(authorization)
    event = request.model_dump(mode="json")
    existing_sequence = store.get_event_sequence(request.event_id)
    try:
        sequence, trace = store.append_event(event)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if existing_sequence is None:
        background_tasks.add_task(
            _analyze_latest,
            trace["trace_id"],
            request.event_type in {"trace_completed", "trace_failed", "trace_cancelled"},
        )
    report = store.trace_store.get_report(trace["trace_id"]) or {}
    risk_report = (report or {}).get("risk_report") or {}
    return {
        "accepted": True,
        "sequence": sequence,
        "trace_id": trace["trace_id"],
        "status": (trace.get("metadata") or {}).get("live_status", "running"),
        "risk_score": float(risk_report.get("risk_score", 0.0) or 0.0),
        "risk_type": risk_report.get("risk_type", "none"),
        "recommended_action": risk_report.get("recommended_action", "allow"),
        "warnings": [],
    }


@router.post("/events/batch")
async def ingest_live_event_batch(request: LiveEventBatchRequest, background_tasks: BackgroundTasks,
                                  authorization: str | None = Header(default=None)):
    _authorize(authorization)
    accepted = duplicates = rejected = 0
    updates: dict[str, dict[str, Any]] = {}
    changed_traces: set[str] = set()
    final_traces: set[str] = set()
    ordered_events = sorted(request.events, key=lambda item: (item.trace_id, item.client_seq if item.client_seq is not None else 10**12))
    for item in ordered_events:
        event = item.model_dump(mode="json")
        try:
            before = store.get_event_sequence(item.event_id)
            sequence, trace = store.append_event(event)
            if before is None:
                accepted += 1
                changed_traces.add(item.trace_id)
            else:
                duplicates += 1
            updates[item.trace_id] = {"trace_id": item.trace_id, "sequence": sequence,
                                      "status": (trace.get("metadata") or {}).get("live_status", "running")}
            if item.event_type in {"trace_completed", "trace_failed", "trace_cancelled"}:
                final_traces.add(item.trace_id)
        except ValueError:
            rejected += 1
    for trace_id in changed_traces:
        background_tasks.add_task(_analyze_latest, trace_id, trace_id in final_traces)
    return {"accepted": accepted, "duplicates": duplicates, "rejected": rejected,
            "trace_updates": list(updates.values())}


@router.get("/traces")
async def list_live_traces(limit: int = Query(default=100, ge=1, le=500), authorization: str | None = Header(default=None)):
    _authorize(authorization)
    return {"items": store.list_live_traces(limit=limit)}


@router.get("/traces/{trace_id}")
async def get_live_trace(trace_id: str, authorization: str | None = Header(default=None)):
    _authorize(authorization)
    snapshot = store.get_snapshot(trace_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"Live trace not found: {trace_id}")

    trace = snapshot["trace"]
    report = snapshot.get("report") or {}
    risk_report = report.get("risk_report") or report
    graph_data: dict[str, Any] = {"nodes": [], "edges": [], "metadata": {}}
    risk_scores: dict[str, float] = {}
    if trace.get("nodes"):
        graph = adapter.trace_to_security_graph(trace)
        graph_data = adapter.graph_to_visualization_data(graph, risk_report.get("risk_path") or [])
        risk_scores = {
            str(node_id): max(
                float(data.get("risk_score", 0.0) or 0.0),
                float((risk_report.get("node_risk_scores") or {}).get(str(node_id), 0.0) or 0.0),
            )
            for node_id, data in graph.nodes(data=True)
        }
    return {
        **snapshot,
        "graph_data": graph_data,
        "risk_scores": risk_scores,
        "status": (trace.get("metadata") or {}).get("live_status", "unknown"),
    }


@router.get("/traces/{trace_id}/events")
async def get_live_events(
    trace_id: str,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=2000),
    authorization: str | None = Header(default=None),
):
    _authorize(authorization)
    return {"items": store.get_events(trace_id, after_sequence=after_sequence, limit=limit)}


@router.get("/traces/{trace_id}/stream")
async def stream_live_events(trace_id: str, after_sequence: int = Query(default=0, ge=0),
                             authorization: str | None = Header(default=None)):
    _authorize(authorization)
    if store.trace_store.get_trace(trace_id) is None:
        raise HTTPException(status_code=404, detail=f"Live trace not found: {trace_id}")

    async def generate():
        cursor = int(after_sequence)
        idle_ticks = 0
        while True:
            events = store.get_events(trace_id, after_sequence=cursor, limit=200)
            if events:
                idle_ticks = 0
                for event in events:
                    cursor = max(cursor, int(event["sequence"]))
                    yield f"id: {cursor}\nevent: {event['event_type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            else:
                idle_ticks += 1
                yield ": heartbeat\n\n"
            trace = store.trace_store.get_trace(trace_id) or {}
            status = (trace.get("metadata") or {}).get("live_status")
            if status in {"completed", "failed", "cancelled"} and idle_ticks >= 2:
                break
            await asyncio.sleep(0.75)

    return StreamingResponse(generate(), media_type="text/event-stream")
