from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from graphguard.context import current_client, parent_node
from graphguard.events import TraceEvent
from graphguard.exporters import HttpEventExporter, JsonTraceExporter
from graphguard.schemas import SecurityTrace, TraceEdge, TraceNode


class GraphGuardClient:
    """Small tracing client with LangSmith-like opt-in instrumentation.

    The client always keeps a local SecurityTrace.  When ``api_url`` is set it
    additionally streams ordered runtime events to GraphGuard-Agent.
    """

    def __init__(
        self,
        project: str,
        scenario: str = "default",
        output_path: str = "./security_traces",
        policy_pack: str = "gov_default",
        api_url: str | None = None,
        api_key: str | None = None,
        *,
        fail_open: bool = True,
        request_timeout: float = 5.0,
        batch_size: int = 20,
        flush_interval_ms: int = 200,
        capture_mode: str = "redacted",
    ) -> None:
        self.project = project
        self.scenario = scenario
        self.output_path = Path(output_path)
        self.policy_pack = policy_pack
        self.api_url = api_url
        self.api_key = api_key
        self.exporter = JsonTraceExporter(self.output_path)
        self.live_exporter = (
            HttpEventExporter(api_url, api_key, timeout=request_timeout, fail_open=fail_open,
                              batch_size=batch_size, flush_interval_ms=flush_interval_ms)
            if api_url
            else None
        )
        self.trace: SecurityTrace | None = None
        self._finished = False
        self._client_seq = 0
        self.capture_mode = capture_mode if capture_mode in {"metadata_only", "redacted", "full"} else "redacted"
        self.events: list[TraceEvent] = []
        current_client.set(self)

    def start_trace(
        self,
        metadata: dict[str, Any] | None = None,
        *,
        trace_id: str | None = None,
        session_id: str | None = None,
        round_idx: int = 0,
        source: str = "sdk",
    ) -> str:
        trace_id = trace_id or f"trace_{uuid4().hex[:12]}"
        self.trace = SecurityTrace(
            trace_id=trace_id,
            project=self.project,
            scenario=self.scenario,
            session_id=session_id or f"session_{uuid4().hex[:8]}",
            created_at=self._now(),
            source=source,
            round_idx=round_idx,
            metadata={"policy_pack": self.policy_pack, **(metadata or {})},
        )
        self._finished = False
        self._client_seq = 0
        self.events = []
        self._emit(
            "trace_started",
            {
                "project": self.project,
                "scenario": self.scenario,
                "source": source,
                "session_id": self.trace.session_id,
                "round_idx": round_idx,
                "metadata": self.trace.metadata,
            },
        )
        return trace_id

    def record_node(self, **kwargs) -> str:
        if self.trace is None:
            self.start_trace()
        assert self.trace is not None

        raw_content = str(kwargs.get("raw_content") or kwargs.get("content") or "")
        display_content = str(kwargs.get("display_content") or raw_content[:240])
        node_id = str(kwargs.get("id") or f"{self.trace.trace_id}:{kwargs.get('node_type', 'node')}:{len(self.trace.nodes) + 1}")
        stored_raw = raw_content if self.capture_mode == "full" else ""
        display_content = "" if self.capture_mode == "metadata_only" else (self._redact(display_content) if self.capture_mode != "full" else display_content)
        node = TraceNode(
            id=node_id,
            label=str(kwargs.get("label") or node_id),
            node_type=str(kwargs.get("node_type") or "unknown"),
            agent=str(kwargs.get("agent") or "system"),
            content_hash=kwargs.get("content_hash") or "sha256:" + hashlib.sha256(raw_content.encode("utf-8")).hexdigest()[:16],
            raw_content=stored_raw,
            display_content=display_content,
            trust_level=str(kwargs.get("trust_level") or "trusted"),
            sensitivity=str(kwargs.get("sensitivity") or "public"),
            visibility=str(kwargs.get("visibility") or "internal_only"),
            stage=str(kwargs.get("stage") or "runtime"),
            security_tags=list(kwargs.get("security_tags") or []),
            policy_refs=list(kwargs.get("policy_refs") or []),
            is_source=bool(kwargs.get("is_source", False)),
            is_sink=bool(kwargs.get("is_sink", False)),
            risk_score=float(kwargs.get("risk_score", 0.0) or 0.0),
            risk_reason=list(kwargs.get("risk_reason") or []),
            metadata=dict(kwargs.get("metadata") or {}),
        )
        self._upsert_local_node(node)
        event_type = str(kwargs.get("event_type") or "node_completed")
        self._emit(event_type, {"node": node.to_dict()})
        return node_id

    def start_node(self, **kwargs) -> str:
        metadata = dict(kwargs.get("metadata") or {})
        metadata["runtime_status"] = "running"
        kwargs["metadata"] = metadata
        kwargs["event_type"] = "node_started"
        return self.record_node(**kwargs)

    def complete_node(self, node_id: str, **updates) -> str:
        return self.update_node(node_id, event_type="node_completed", **updates)

    def fail_node(self, node_id: str, error: Exception | str, **updates) -> str:
        tags = list(updates.pop("security_tags", []) or [])
        if "runtime_error" not in tags:
            tags.append("runtime_error")
        updates.update(
            {
                "security_tags": tags,
                "risk_score": max(float(updates.get("risk_score", 0.0) or 0.0), 0.5),
                "risk_reason": [str(error)],
            }
        )
        return self.update_node(node_id, event_type="node_failed", **updates)

    def update_node(self, node_id: str, *, event_type: str = "node_completed", **updates) -> str:
        if self.trace is None:
            raise RuntimeError("start_trace() must be called before update_node()")
        current = next((node for node in self.trace.nodes if node.id == node_id), None)
        if current is None:
            updates["id"] = node_id
            updates["event_type"] = event_type
            return self.record_node(**updates)

        requested_runtime_status = str((updates.get("metadata") or {}).get("runtime_status") or "")
        for key, value in updates.items():
            if key == "metadata":
                current.metadata.update(dict(value or {}))
            elif key != "raw_content" and hasattr(current, key) and value is not None:
                setattr(current, key, value)
        if updates.get("raw_content") is not None:
            raw = str(updates["raw_content"])
            current.content_hash = "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
            current.raw_content = raw if self.capture_mode == "full" else ""
            if not updates.get("display_content"):
                current.display_content = self._redact(raw[:240]) if self.capture_mode != "full" else raw[:240]
        if updates.get("display_content") is not None and self.capture_mode != "full":
            current.display_content = "" if self.capture_mode == "metadata_only" else self._redact(str(updates["display_content"]))
        current.metadata["runtime_status"] = requested_runtime_status or {
            "node_started": "running",
            "node_completed": "completed",
            "node_failed": "failed",
        }.get(event_type, current.metadata.get("runtime_status", "completed"))
        self._emit(event_type, {"node": current.to_dict()})
        return node_id

    def record_edge(self, source: str, target: str, **kwargs) -> None:
        if self.trace is None:
            self.start_trace()
        assert self.trace is not None
        edge = TraceEdge(
            source=source,
            target=target,
            edge_type=str(kwargs.get("edge_type") or "control_flow"),
            taint=str(kwargs.get("taint") or ""),
            metadata=dict(kwargs.get("metadata") or {}),
        )
        key = (edge.source, edge.target, edge.edge_type)
        if not any((item.source, item.target, item.edge_type) == key for item in self.trace.edges):
            self.trace.edges.append(edge)
        self._emit("edge_added", {"edge": edge.to_dict()})

    def record_guard_decision(self, decision: dict[str, Any]) -> None:
        self._emit("guard_decision", dict(decision))

    def start_span(self, *, name: str, node_type: str, **kwargs) -> str:
        parent = parent_node()
        node_id = self.start_node(label=name, node_type=node_type, raw_content=str(kwargs.pop("input", "")), **kwargs)
        if parent:
            self.record_edge(parent, node_id, edge_type="calls")
        return node_id

    def complete_span(self, node_id: str, *, output=None, **kwargs) -> str:
        metadata = dict(kwargs.pop("metadata", {}) or {})
        metadata.update(kwargs)
        return self.complete_node(node_id, display_content=str(output or "")[:500], metadata=metadata)

    def fail_span(self, node_id: str, error: Exception, **kwargs) -> str:
        return self.fail_node(node_id, error, metadata=kwargs)

    def span(self, name: str, node_type: str, **kwargs):
        from graphguard.spans import Span
        return Span(self, name, node_type, kwargs)

    def aspan(self, name: str, node_type: str, **kwargs):
        from graphguard.spans import AsyncSpan
        return AsyncSpan(self, name, node_type, kwargs)

    def finish_trace(self, *, status: str = "completed", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.trace is None:
            self.start_trace()
        assert self.trace is not None
        if metadata:
            self.trace.metadata.update(metadata)
        self.trace.metadata["status"] = status
        if self.live_exporter is not None:
            self.trace.metadata["exporter_metrics"] = {
                "queue_size": self.live_exporter.queue_size,
                "dropped_event_count": self.live_exporter.dropped_event_count,
            }
        if not self._finished:
            event_type = {
                "completed": "trace_completed",
                "cancelled": "trace_cancelled",
            }.get(status, "trace_failed")
            self._emit(
                event_type,
                {"metadata": {"status": status, **(metadata or {})}},
            )
            self._finished = True
        return self.trace.to_dict()

    def snapshot(self) -> dict[str, Any]:
        if self.trace is None:
            self.start_trace()
        assert self.trace is not None
        payload = self.trace.to_dict()
        self._emit("trace_snapshot", {"trace": payload})
        return payload

    def save(self, path: str | None = None) -> str:
        return self.exporter.save(self.finish_trace(), path)

    def flush(self, timeout: float = 5.0) -> None:
        if self.live_exporter is not None:
            self.live_exporter.flush(timeout=timeout)

    @property
    def last_live_response(self) -> dict[str, Any] | None:
        return self.live_exporter.last_response if self.live_exporter else None

    @property
    def last_live_error(self) -> str | None:
        return self.live_exporter.last_error if self.live_exporter else None

    def _upsert_local_node(self, node: TraceNode) -> None:
        assert self.trace is not None
        for index, current in enumerate(self.trace.nodes):
            if current.id == node.id:
                self.trace.nodes[index] = node
                return
        self.trace.nodes.append(node)

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.trace is None:
            return
        self._client_seq += 1
        event = TraceEvent(
            event_id=f"evt_{uuid4().hex}", trace_id=self.trace.trace_id,
            session_id=self.trace.session_id, round_idx=self.trace.round_idx,
            seq=self._client_seq, event_type=event_type, timestamp=self._now(), payload=payload,
            metadata={"project": self.project, "scenario": self.scenario},
        ).to_dict()
        event["client_seq"] = event.pop("seq")
        self.events.append(TraceEvent(
            event_id=event["event_id"], trace_id=event["trace_id"], session_id=event["session_id"],
            round_idx=event["round_idx"], seq=event["client_seq"], event_type=event["event_type"],
            timestamp=event["timestamp"], node_id=event.get("node_id"), parent_node_id=event.get("parent_node_id"),
            payload=event.get("payload") or {}, metadata=event.get("metadata") or {},
        ))
        if self.live_exporter is not None:
            self.live_exporter.submit(event)

    @staticmethod
    def _redact(text: str) -> str:
        import re
        text = re.sub(r"(?<!\d)\d{17}[\dXx](?!\d)", "[身份证号已脱敏]", text)
        # Redact composite values before their components. A value such as
        # ``13800138000@example.com`` must become one email placeholder; if the
        # phone number is replaced first, the remaining ``@example.com`` can no
        # longer be recognised as an email address and may be misclassified by
        # downstream policy analysis.
        text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[邮箱已脱敏]", text)
        text = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号已脱敏]", text)
        text = re.sub(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)", "[银行卡号已脱敏]", text)
        text = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]{8,}", "Bearer [令牌已脱敏]", text)
        text = re.sub(r"(?:sk-|AKIA)[A-Za-z0-9_-]{8,}", "[API Key已脱敏]", text)
        text = re.sub(
            r"(?i)((?:api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*)[\"']?[^\s,;\"']+[\"']?",
            r"\1[密钥已脱敏]",
            text,
        )
        return re.sub(
            r"(?i)([\"']highly_sensitive[\"']\s*:\s*)[\"'][^\"']*[\"']",
            r'\1"[高敏字段已脱敏]"',
            text,
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
