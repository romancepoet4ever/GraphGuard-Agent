from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx


class GovernmentAgentTraceAdapter:
    """Convert SecurityTrace JSON from the government-agent demo into NetworkX."""

    def load_trace(self, trace_path: str | Path) -> dict[str, Any]:
        path = Path(trace_path)
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        self.validate_trace(payload)
        return payload

    def validate_trace(self, trace: dict[str, Any]) -> None:
        required = ["trace_id", "nodes", "edges"]
        missing = [key for key in required if key not in trace]
        if missing:
            raise ValueError(f"SecurityTrace missing required keys: {missing}")
        if not isinstance(trace.get("nodes"), list):
            raise ValueError("SecurityTrace.nodes must be a list.")
        if not isinstance(trace.get("edges"), list):
            raise ValueError("SecurityTrace.edges must be a list.")

        node_ids = {str(node.get("id")) for node in trace["nodes"] if node.get("id")}
        if not node_ids:
            raise ValueError("SecurityTrace must contain at least one node with id.")
        for edge in trace["edges"]:
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            if source not in node_ids or target not in node_ids:
                raise ValueError(f"SecurityTrace edge references unknown node: {source} -> {target}")

    def trace_to_networkx(self, trace: dict[str, Any]) -> nx.DiGraph:
        self.validate_trace(trace)
        graph = nx.DiGraph(
            trace_id=trace.get("trace_id", ""),
            session_id=trace.get("session_id", ""),
            scenario=trace.get("scenario", ""),
            round_idx=trace.get("round_idx", 0),
            metadata=dict(trace.get("metadata") or {}),
        )

        for node in trace.get("nodes", []):
            node_id = str(node["id"])
            node_type = str(node.get("node_type") or node.get("type") or "unknown")
            graph.add_node(
                node_id,
                **{
                    **dict(node),
                    "type": node_type,
                    "node_type": node_type,
                    "label": str(node.get("label") or node_id),
                    "content": str(
                        node.get("display_content")
                        or node.get("content")
                        or node.get("raw_content")
                        or ""
                    ),
                    "trust": str(node.get("trust_level") or node.get("trust") or "neutral"),
                    "risk_score": float(node.get("risk_score", 0.0) or 0.0),
                    "security_tags": list(node.get("security_tags") or []),
                    "policy_refs": list(node.get("policy_refs") or []),
                    "is_source": bool(node.get("is_source", False)),
                    "is_sink": bool(node.get("is_sink", False)),
                },
            )

        for index, edge in enumerate(trace.get("edges", []), start=1):
            source = str(edge["source"])
            target = str(edge["target"])
            edge_type = str(edge.get("edge_type") or edge.get("type") or "control_flow")
            graph.add_edge(
                source,
                target,
                **{
                    **dict(edge),
                    "id": edge.get("id") or f"{source}->{target}:{index}",
                    "type": edge_type,
                    "edge_type": edge_type,
                    "taint": edge.get("taint", ""),
                },
            )

        return graph

    def graph_to_visualization_data(
        self,
        graph: nx.DiGraph,
        risk_path: list[str] | None = None,
    ) -> dict[str, Any]:
        levels = self._compute_levels(graph)
        risk_path = [str(item) for item in (risk_path or [])]
        risk_edges = {
            (risk_path[index], risk_path[index + 1])
            for index in range(max(0, len(risk_path) - 1))
        }

        nodes = []
        for node_id, data in graph.nodes(data=True):
            node_id = str(node_id)
            nodes.append(
                {
                    "id": node_id,
                    "label": str(data.get("label") or node_id),
                    "type": str(data.get("node_type") or data.get("type") or "unknown"),
                    "level": int(levels.get(node_id, 0)),
                    "lane": self._lane_for_node(data),
                    "trust_level": str(data.get("trust_level") or data.get("trust") or "neutral"),
                    "sensitivity": str(data.get("sensitivity") or "public"),
                    "visibility": str(data.get("visibility") or "internal_only"),
                    "metadata": dict(data.get("metadata") or {}),
                    "security_tags": list(data.get("security_tags") or []),
                    "is_source": bool(data.get("is_source", False)),
                    "is_sink": bool(data.get("is_sink", False)),
                    "display_content": str(data.get("display_content") or data.get("content") or ""),
                }
            )

        edges = []
        for source, target, data in graph.edges(data=True):
            source = str(source)
            target = str(target)
            edges.append(
                {
                    "from": source,
                    "to": target,
                    "type": str(data.get("edge_type") or data.get("type") or "control_flow"),
                    "label": str(data.get("label") or data.get("taint") or ""),
                    "taint": str(data.get("taint") or ""),
                    "is_risk_path": (source, target) in risk_edges,
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": dict(graph.graph),
        }

    @staticmethod
    def _compute_levels(graph: nx.DiGraph) -> dict[str, int]:
        levels = {str(node): 0 for node in graph.nodes()}
        try:
            order = list(nx.topological_sort(graph))
        except Exception:
            order = list(graph.nodes())

        for node in order:
            node_id = str(node)
            predecessors = list(graph.predecessors(node))
            if predecessors:
                levels[node_id] = 1 + max(levels.get(str(pred), 0) for pred in predecessors)
        return levels

    @staticmethod
    def _lane_for_node(data: dict[str, Any]) -> int:
        metadata = dict(data.get("metadata") or {})
        explicit_lane = data.get("lane", metadata.get("lane"))
        if explicit_lane is not None:
            try:
                return int(explicit_lane)
            except (TypeError, ValueError):
                pass
        agent = str(data.get("agent") or "")
        node_type = str(data.get("node_type") or data.get("type") or "")
        if agent in {"trainee", "user"} or node_type == "user_input":
            return 0
        if agent in {"interrogator", "system"}:
            return 1
        if agent == "suspect":
            return 2
        if agent == "referee":
            return 3
        if node_type in {"final_report", "user_visible_sink"}:
            return 4
        return 1

