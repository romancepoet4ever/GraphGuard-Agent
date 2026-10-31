from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.adapters.security_trace_adapter import trace_to_networkx
from src.detection.government_risk_engine import GovernmentRiskEngine


class IncrementalRiskEngine:
    """Deterministic, local-only live risk analysis."""

    def __init__(self) -> None:
        self.engine = GovernmentRiskEngine(write_audit=False)

    def analyze(self, trace: dict[str, Any], status: str = "running") -> dict[str, Any]:
        if not trace.get("nodes"):
            return self.empty_report(trace.get("trace_id", ""), status)
        report = self.engine.analyze(trace_to_networkx(trace))
        report["status"] = status
        report["current_risk_node"] = report.get("risk_path", [None])[-1] if report.get("risk_path") else None
        report["updated_at"] = datetime.now(timezone.utc).isoformat()
        return report

    @staticmethod
    def empty_report(trace_id: str, status: str = "running") -> dict[str, Any]:
        return {"trace_id": trace_id, "status": status, "is_attack": False, "risk_score": 0.0,
                "risk_type": "none", "severity": "none", "current_risk_node": None, "risk_path": [],
                "matched_rules": [], "recommended_action": "allow", "repair_suggestions": [],
                "updated_at": datetime.now(timezone.utc).isoformat()}


def rebuild_trace(events: list[dict[str, Any]]) -> tuple[dict[str, Any], str, str | None]:
    events = sorted(events, key=lambda item: int(item.get("seq", 0)))
    first = events[0] if events else {}
    trace_payload = (first.get("payload") or {}).get("trace") or {}
    trace = {
        "trace_id": first.get("trace_id", ""), "session_id": first.get("session_id", ""),
        "round_idx": first.get("round_idx", 0), "project": (first.get("metadata") or {}).get("project", trace_payload.get("project", "unknown")),
        "scenario": (first.get("metadata") or {}).get("scenario", trace_payload.get("scenario", "unknown")),
        "created_at": first.get("timestamp", ""), "source": "live_http", "nodes": [], "edges": [],
        "metadata": trace_payload.get("metadata", {}),
    }
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    status, current = "running", None
    for event in events:
        event_type, payload = event.get("event_type"), event.get("payload") or {}
        node = payload.get("node")
        if node and node.get("id"):
            nodes[str(node["id"])] = node
            current = str(node["id"])
        edge = payload.get("edge")
        if edge and edge.get("source") and edge.get("target"):
            edges[(edge["source"], edge["target"], edge.get("edge_type", "control_flow"))] = edge
        if event_type == "trace.completed":
            status = "completed"
        elif event_type == "trace.failed":
            status = "failed"
    trace["nodes"], trace["edges"] = list(nodes.values()), list(edges.values())
    trace["metadata"]["status"] = status
    return trace, status, current
