from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from itertools import pairwise
from typing import Any

import networkx as nx

from evaluation.core.schemas import assert_no_gold
from src.adapters.government_agent_adapter import GovernmentAgentTraceAdapter

_SINK_TYPES = {"user_visible_sink", "final_report", "tool_call"}
_SOURCE_TYPES = {"user_input", "external_document", "tool_result"}


def _security_tags(node_type: str, spec: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    if node_type == "user_input" and spec.get("taint") == "untrusted_input":
        tags.append("prompt_injection_candidate")
    if node_type == "external_document" and spec.get("source_type") == "knowledge":
        tags.extend(["knowledge_poisoning_candidate", "unverified_claim"])
    if spec.get("unverified_claim") and node_type in {"model_generation", "final_report"}:
        tags.append("unverified_claim")
    if spec.get("gateway_denied") and node_type == "tool_call":
        tags.append("tool_denied")
    return sorted(set(tags))


def _node_content(case: dict[str, Any], node_type: str) -> str:
    spec = case["scenario_spec"]
    if node_type == "user_input":
        return str(case.get("input_text") or "")
    if node_type == "external_document":
        return str(case.get("external_content") or spec.get("raw_tool_result") or "")
    if node_type == "tool_result":
        return str(spec.get("raw_tool_result") or "synthetic weather tool result")
    if node_type in {"model_generation", "final_report", "user_visible_sink"}:
        return str(case.get("input_text") or "")
    return str(spec.get("tool_name") or node_type)


def _make_node(case: dict[str, Any], node_type: str, index: int) -> dict[str, Any]:
    spec = case["scenario_spec"]
    content = _node_content(case, node_type)
    is_source = node_type in _SOURCE_TYPES and index == 0
    is_sink = node_type in _SINK_TYPES and index == len(spec["path"]) - 1
    sensitivity = str(spec.get("sensitivity") or "public")
    trust = "untrusted" if is_source and (
        spec.get("taint") == "untrusted_input"
        or node_type == "external_document"
        or sensitivity in {"sensitive", "secret", "secret_like", "confidential"}
    ) else "trusted"
    metadata = {
        "protected_sink": bool(spec.get("protected_sink")) if is_sink else False,
        "provenance_present": spec.get("provenance_present") if is_sink else None,
        "gateway_denied": bool(spec.get("gateway_denied")) if node_type == "tool_call" else False,
        "business_valid": bool(spec.get("business_valid", True)),
        "document_version": spec.get("document_version") if is_sink else None,
    }
    return {
        "id": f"{case['case_id']}:n{index + 1}",
        "label": node_type,
        "node_type": node_type,
        "agent": "user" if node_type == "user_input" else "weather_agent",
        "trust_level": trust,
        "sensitivity": sensitivity if is_source else "public",
        "visibility": "user_visible" if is_sink else "internal_only",
        "is_source": is_source,
        "is_sink": is_sink,
        "raw_content": content,
        "display_content": content,
        "security_tags": _security_tags(node_type, spec),
        "metadata": metadata,
        "tool": str(spec.get("tool_name") or "") if node_type == "tool_call" else "",
        "stage": "report" if node_type in {"final_report", "user_visible_sink"} else node_type,
    }


def build_weather_trace(case: dict[str, Any]) -> dict[str, Any]:
    """Build one SecurityTrace exclusively from observable case fields."""

    assert_no_gold(case)
    spec = dict(case.get("scenario_spec") or {})
    path = list(spec.get("path") or [])
    if not path:
        raise ValueError(f"case {case.get('case_id')} has no observable path")

    nodes = [_make_node(case, node_type, index) for index, node_type in enumerate(path)]
    edges: list[dict[str, Any]] = []
    for index, (source, target) in enumerate(pairwise(nodes), start=1):
        edges.append(
            {
                "id": f"{case['case_id']}:e{index}",
                "source": source["id"],
                "target": target["id"],
                "edge_type": "data_flow",
                "taint": str(spec.get("taint") or "") if index == 1 else "",
            }
        )

    if spec.get("sanitized"):
        sanitizer = {
            **_make_node(case, "sanitizer", len(nodes)),
            "id": f"{case['case_id']}:sanitizer",
            "security_tags": ["synthetic_sanitized"],
        }
        last_sink = nodes[-1]
        predecessor = nodes[-2]
        edges = [edge for edge in edges if edge["target"] != last_sink["id"]]
        edges.extend(
            [
                {
                    "id": f"{case['case_id']}:sanitize-in",
                    "source": predecessor["id"],
                    "target": sanitizer["id"],
                    "edge_type": "data_flow",
                    "taint": str(spec.get("taint") or "sensitive_data"),
                },
                {
                    "id": f"{case['case_id']}:sanitize-out",
                    "source": sanitizer["id"],
                    "target": last_sink["id"],
                    "edge_type": "cleaned_flow",
                    "taint": "",
                },
            ]
        )
        nodes.insert(-1, sanitizer)
    elif spec.get("blocked") and edges:
        edges.pop()

    trace = {
        "trace_id": f"v3:{case['case_id']}",
        "session_id": "evaluation-v3-controlled",
        "scenario": "government_weather_agent",
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "project": "meteorological_agent",
            "policy_pack": "government_weather",
            "source": str(case.get("source") or ""),
            "case_id": str(case["case_id"]),
            "split": str(case.get("split") or ""),
            "risk_name_mapping": {
                "core": "missing_provenance",
                "runtime_guard": "provenance_loss",
            },
        },
    }
    assert_no_gold(trace)
    return trace


def to_networkx(trace: dict[str, Any]) -> nx.DiGraph:
    return GovernmentAgentTraceAdapter().trace_to_networkx(trace)


def topology_signature(trace: dict[str, Any]) -> str:
    value = {
        "nodes": [node["node_type"] for node in trace.get("nodes", [])],
        "edges": [
            (
                next(node["node_type"] for node in trace["nodes"] if node["id"] == edge["source"]),
                edge.get("edge_type", "control_flow"),
                next(node["node_type"] for node in trace["nodes"] if node["id"] == edge["target"]),
            )
            for edge in trace.get("edges", [])
        ],
    }
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_anomaly_pair(case: dict[str, Any]) -> tuple[nx.DiGraph, nx.DiGraph]:
    """Create a normal baseline and observable graph without consulting gold labels."""

    observed = to_networkx(build_weather_trace(case))
    baseline = deepcopy(observed)
    spec = case["scenario_spec"]
    variant = "baseline"
    if spec.get("unverified_claim"):
        variant = "report_path_anomaly"
    elif spec.get("gateway_denied") or spec.get("taint") == "untrusted_input":
        variant = "unexpected_high_risk_branch"
    elif spec.get("sensitivity") in {"sensitive", "secret", "secret_like", "confidential"}:
        variant = "orphan_sensitive_result"
    elif spec.get("provenance_present") is False:
        variant = "missing_connection"
    elif case.get("external_content"):
        variant = "abnormal_chain"

    if variant != "baseline" and baseline.number_of_nodes() > 1:
        removable = list(baseline.nodes())[1 if baseline.number_of_nodes() > 2 else 0]
        baseline.remove_node(removable)
    elif variant != "baseline" and baseline.number_of_edges() > 0:
        baseline.remove_edge(*next(iter(baseline.edges())))

    observed.graph["anomaly_variant"] = variant
    baseline.graph["anomaly_variant"] = "allowed_baseline"
    return baseline, observed
