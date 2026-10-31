from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def load_otel_spans(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def otel_spans_to_security_trace(payload: dict[str, Any] | list[dict[str, Any]], project: str = "otel-import") -> dict[str, Any]:
    spans = _extract_spans(payload)
    nodes = []
    edges = []
    span_id_to_node_id = {}

    for index, span in enumerate(spans, start=1):
        attrs = _attributes_to_dict(span.get("attributes") or [])
        span_id = str(span.get("spanId") or span.get("span_id") or f"span_{index}")
        parent_id = str(span.get("parentSpanId") or span.get("parent_span_id") or "")
        name = str(span.get("name") or attrs.get("llm.operation.name") or f"span {index}")
        node_type = _infer_node_type(name, attrs)
        raw_content = str(attrs.get("input.value") or attrs.get("llm.prompt") or attrs.get("output.value") or name)
        sensitivity, tags = _infer_security(raw_content, attrs, node_type)
        node_id = f"{node_type}_{index}"
        span_id_to_node_id[span_id] = node_id
        nodes.append(
            {
                "id": node_id,
                "label": name,
                "node_type": node_type,
                "agent": str(attrs.get("agent.name") or attrs.get("service.name") or "otel"),
                "content_hash": "sha256:" + hashlib.sha256(raw_content.encode("utf-8")).hexdigest()[:16],
                "raw_content": raw_content,
                "display_content": raw_content[:240],
                "trust_level": "untrusted" if node_type in {"user_input", "external_document"} else "trusted",
                "sensitivity": sensitivity,
                "visibility": "user_visible" if node_type in {"user_input", "user_visible_sink"} else "internal_only",
                "stage": str(attrs.get("graphguard.stage") or "otel"),
                "security_tags": tags,
                "policy_refs": [],
                "is_source": bool(tags) or node_type in {"user_input", "external_document"},
                "is_sink": node_type in {"user_visible_sink", "final_report"},
                "risk_score": 0.0,
                "risk_reason": [],
                "metadata": {"span_id": span_id, "parent_span_id": parent_id, "attributes": attrs},
            }
        )

    for span in spans:
        span_id = str(span.get("spanId") or span.get("span_id") or "")
        parent_id = str(span.get("parentSpanId") or span.get("parent_span_id") or "")
        if parent_id and parent_id in span_id_to_node_id and span_id in span_id_to_node_id:
            edges.append(
                {
                    "source": span_id_to_node_id[parent_id],
                    "target": span_id_to_node_id[span_id],
                    "edge_type": "otel_parent_child",
                    "taint": "untrusted_input",
                    "metadata": {"span_id": span_id, "parent_span_id": parent_id},
                }
            )

    if len(nodes) > 1 and not edges:
        for idx in range(len(nodes) - 1):
            edges.append(
                {
                    "source": nodes[idx]["id"],
                    "target": nodes[idx + 1]["id"],
                    "edge_type": "otel_sequence",
                    "taint": "untrusted_input" if idx == 0 else "",
                    "metadata": {},
                }
            )

    trace_id = _first_trace_id(spans)
    return {
        "trace_id": f"otel_{trace_id}",
        "project": project,
        "scenario": "opentelemetry_import",
        "session_id": trace_id,
        "round_idx": 0,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": "opentelemetry",
        "nodes": nodes,
        "edges": edges,
        "metadata": {"description": "Converted from OpenTelemetry-like span JSON."},
    }


def _extract_spans(payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if "spans" in payload and isinstance(payload["spans"], list):
        return payload["spans"]

    spans = []
    for resource in payload.get("resourceSpans") or []:
        resource_attrs = _attributes_to_dict((resource.get("resource") or {}).get("attributes") or [])
        for scope in resource.get("scopeSpans") or []:
            for span in scope.get("spans") or []:
                span = dict(span)
                attrs = _attributes_to_dict(span.get("attributes") or [])
                attrs.update({k: v for k, v in resource_attrs.items() if k not in attrs})
                span["attributes"] = [{"key": k, "value": {"stringValue": str(v)}} for k, v in attrs.items()]
                spans.append(span)
    return spans


def _attributes_to_dict(attrs: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for item in attrs:
        key = item.get("key")
        value = item.get("value", item.get("Value", ""))
        if isinstance(value, dict):
            value = next(iter(value.values()), "")
        if key:
            out[str(key)] = value
    return out


def _infer_node_type(name: str, attrs: dict[str, Any]) -> str:
    raw = " ".join([name, str(attrs.get("span.kind", "")), str(attrs.get("llm.operation.name", "")), str(attrs.get("graphguard.node_type", ""))]).lower()
    if attrs.get("graphguard.node_type"):
        return str(attrs["graphguard.node_type"])
    if "user" in raw and "input" in raw:
        return "user_input"
    if "retrieval" in raw or "search" in raw:
        return "knowledge_retrieval"
    if "tool" in raw:
        return "tool_call"
    if "report" in raw:
        return "final_report"
    if "output" in raw or "response" in raw:
        return "user_visible_sink"
    return "agent_generation"


def _infer_security(text: str, attrs: dict[str, Any], node_type: str) -> tuple[str, list[str]]:
    lowered = text.lower()
    tags = []
    if any(token in lowered for token in ["忽略", "绕过", "system prompt", "全部证据", "ignore previous"]):
        tags.append("prompt_injection_candidate")
    if any(token in lowered for token in ["身份证", "手机号", "核心证人", "调查底稿", "sk-", "akia"]):
        tags.append("sensitive_evidence")
    if node_type in {"user_visible_sink", "final_report"}:
        tags.append("user_visible_sink")
    sensitivity = str(attrs.get("graphguard.sensitivity") or ("sensitive" if "sensitive_evidence" in tags else "public"))
    return sensitivity, tags


def _first_trace_id(spans: list[dict[str, Any]]) -> str:
    for span in spans:
        trace_id = span.get("traceId") or span.get("trace_id")
        if trace_id:
            return str(trace_id)
    return hashlib.sha256(json.dumps(spans, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
