from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.trace_store import TraceStore


class LiveTraceStore:
    """Persist ordered runtime events and materialize them as a SecurityTrace.

    Events are append-only.  The materialized trace remains compatible with the
    existing adapters/detectors, so live and offline analysis share one engine.
    """

    def __init__(self, db_path: str | Path = "data/trace_store/graphguard.sqlite") -> None:
        self.trace_store = TraceStore(db_path)
        self.db_path = self.trace_store.db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS live_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    trace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_events_trace_seq ON live_events(trace_id, sequence)"
            )

    def append_event(self, event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        trace_id = str(event.get("trace_id") or "").strip()
        event_id = str(event.get("event_id") or "").strip()
        event_type = str(event.get("event_type") or "").strip()
        if not trace_id or not event_id or not event_type:
            raise ValueError("event_id, trace_id and event_type are required")

        created_at = str(event.get("timestamp") or self._now())
        inserted = True
        with self._connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO live_events(event_id, trace_id, event_type, event_json, created_at)
                    VALUES(?, ?, ?, ?, ?)
                    """,
                    (event_id, trace_id, event_type, json.dumps(event, ensure_ascii=False), created_at),
                )
                sequence = int(cursor.lastrowid)
            except sqlite3.IntegrityError:
                inserted = False
                row = conn.execute(
                    "SELECT sequence FROM live_events WHERE event_id = ?", (event_id,)
                ).fetchone()
                sequence = int(row["sequence"])

        if not inserted:
            trace = self.trace_store.get_trace(trace_id) or self._empty_trace(event)
            return sequence, trace

        trace = self.trace_store.get_trace(trace_id) or self._empty_trace(event)
        trace = self._apply_event(trace, event, sequence)
        self.trace_store.save_trace(trace, source="live_sdk")
        return sequence, trace

    def get_event_sequence(self, event_id: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute("SELECT sequence FROM live_events WHERE event_id = ?", (event_id,)).fetchone()
        return int(row["sequence"]) if row else None

    def list_live_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.trace_store.list_traces(limit=limit)
        items: list[dict[str, Any]] = []
        for row in rows:
            trace = self.trace_store.get_trace(row["trace_id"]) or {}
            metadata = dict(trace.get("metadata") or {})
            if row.get("source") != "live_sdk" and "live_status" not in metadata:
                continue
            report = self.trace_store.get_report(row["trace_id"]) or {}
            risk_report = report.get("risk_report") or report
            items.append(
                {
                    **row,
                    "source": self._normalize_source(trace.get("source") or row.get("source")),
                    "ingestion_source": row.get("source", ""),
                    "policy_pack": metadata.get("policy_pack", "generic_default"),
                    "session_id": trace.get("session_id", ""),
                    "round_idx": trace.get("round_idx", 0),
                    "status": metadata.get("live_status", "unknown"),
                    "last_sequence": metadata.get("last_sequence", 0),
                    "node_count": len(trace.get("nodes") or []),
                    "edge_count": len(trace.get("edges") or []),
                    "risk_score": float(risk_report.get("risk_score", 0.0) or 0.0),
                    "risk_type": risk_report.get("risk_type", "none"),
                    "severity": risk_report.get("severity", "none"),
                }
            )
        return items

    @staticmethod
    def _normalize_source(source: Any) -> str:
        value = str(source or "sdk").strip().lower()
        if "otel" in value or "opentelemetry" in value:
            return "opentelemetry"
        if "callback" in value or "langchain" in value or "langgraph" in value:
            return "callback"
        if "span" in value:
            return "span"
        if "upload" in value:
            return "upload"
        if "demo" in value or "offline" in value:
            return "offline_demo"
        return "sdk"

    def get_events(self, trace_id: str, after_sequence: int = 0, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT sequence, event_json FROM live_events
                WHERE trace_id = ? AND sequence > ?
                ORDER BY sequence ASC LIMIT ?
                """,
                (trace_id, int(after_sequence), int(limit)),
            ).fetchall()
        result = []
        for row in rows:
            payload = json.loads(row["event_json"])
            payload["sequence"] = int(row["sequence"])
            result.append(payload)
        return result

    def get_snapshot(self, trace_id: str) -> dict[str, Any] | None:
        trace = self.trace_store.get_trace(trace_id)
        if trace is None:
            return None
        return {
            "trace": trace,
            "report": self.trace_store.get_report(trace_id),
            "events": self.get_events(trace_id, limit=1000),
        }

    @staticmethod
    def _empty_trace(event: dict[str, Any]) -> dict[str, Any]:
        payload = dict(event.get("payload") or {})
        timestamp = str(event.get("timestamp") or LiveTraceStore._now())
        return {
            "trace_id": event["trace_id"],
            "project": payload.get("project", "interrogation-agent"),
            "scenario": payload.get("scenario", "runtime"),
            "session_id": payload.get("session_id", ""),
            "round_idx": int(payload.get("round_idx", 0) or 0),
            "created_at": timestamp,
            "source": payload.get("source", "sdk"),
            "nodes": [],
            "edges": [],
            "metadata": {
                **dict(payload.get("metadata") or {}),
                "live_status": "running",
                "started_at": timestamp,
                "last_sequence": 0,
            },
        }

    def _apply_event(self, trace: dict[str, Any], event: dict[str, Any], sequence: int) -> dict[str, Any]:
        event_type = str(event["event_type"])
        payload = dict(event.get("payload") or {})
        metadata = dict(trace.get("metadata") or {})
        metadata["last_sequence"] = sequence
        metadata["last_event_type"] = event_type
        metadata["last_event_at"] = event.get("timestamp") or self._now()
        trace["metadata"] = metadata

        if event_type == "trace_started":
            trace.update(
                {
                    "project": payload.get("project", trace.get("project", "unknown")),
                    "scenario": payload.get("scenario", trace.get("scenario", "runtime")),
                    "session_id": payload.get("session_id", trace.get("session_id", "")),
                    "round_idx": int(payload.get("round_idx", trace.get("round_idx", 0)) or 0),
                    "source": payload.get("source", trace.get("source", "sdk")),
                }
            )
            metadata.update(dict(payload.get("metadata") or {}))
            metadata["live_status"] = "running"

        elif event_type in {"node_started", "node_completed", "node_failed"}:
            node = dict(payload.get("node") or {})
            node_id = str(node.get("id") or payload.get("node_id") or "")
            if node_id:
                node["id"] = node_id
                node_metadata = dict(node.get("metadata") or {})
                node_metadata.update(
                    {
                        "runtime_status": {
                            "node_started": "running",
                            "node_completed": "completed",
                            "node_failed": "failed",
                        }[event_type],
                        "last_event_sequence": sequence,
                        "last_event_at": event.get("timestamp") or self._now(),
                    }
                )
                node["metadata"] = node_metadata
                self._upsert_node(trace, node)

        elif event_type == "edge_added":
            edge = dict(payload.get("edge") or {})
            if edge.get("source") and edge.get("target"):
                self._upsert_edge(trace, edge)

        elif event_type == "guard_decision":
            decisions = list(metadata.get("guard_decisions") or [])
            decisions.append({"sequence": sequence, **payload})
            metadata["guard_decisions"] = decisions[-100:]

        elif event_type == "trace_snapshot":
            snapshot = dict(payload.get("trace") or {})
            if snapshot:
                preserved = dict(snapshot.get("metadata") or {})
                preserved.update(metadata)
                snapshot["metadata"] = preserved
                trace = snapshot

        elif event_type in {"trace_completed", "trace_failed", "trace_cancelled"}:
            metadata["live_status"] = {
                "trace_completed": "completed",
                "trace_failed": "failed",
                "trace_cancelled": "cancelled",
            }[event_type]
            metadata["finished_at"] = event.get("timestamp") or self._now()
            metadata.update(dict(payload.get("metadata") or {}))

        return trace

    @staticmethod
    def _upsert_node(trace: dict[str, Any], node: dict[str, Any]) -> None:
        nodes = list(trace.get("nodes") or [])
        for index, current in enumerate(nodes):
            if str(current.get("id")) == str(node.get("id")):
                merged = dict(current)
                merged.update({key: value for key, value in node.items() if value is not None})
                old_meta = dict(current.get("metadata") or {})
                old_meta.update(dict(node.get("metadata") or {}))
                merged["metadata"] = old_meta
                nodes[index] = merged
                trace["nodes"] = nodes
                return
        nodes.append(node)
        trace["nodes"] = nodes

    @staticmethod
    def _upsert_edge(trace: dict[str, Any], edge: dict[str, Any]) -> None:
        edges = list(trace.get("edges") or [])
        key = (str(edge.get("source")), str(edge.get("target")), str(edge.get("edge_type") or "control_flow"))
        for index, current in enumerate(edges):
            current_key = (
                str(current.get("source")),
                str(current.get("target")),
                str(current.get("edge_type") or "control_flow"),
            )
            if current_key == key:
                merged = dict(current)
                merged.update(edge)
                edges[index] = merged
                trace["edges"] = edges
                return
        edges.append(edge)
        trace["edges"] = edges

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
