from __future__ import annotations

from typing import Any


class PermissionChecker:
    def check_edge(self, source_node: dict[str, Any], target_node: dict[str, Any], edge: dict[str, Any]) -> dict[str, Any] | None:
        source_agent = str(source_node.get("agent") or source_node.get("role") or "")
        target_type = str(target_node.get("node_type") or target_node.get("type") or "")
        edge_taint = str(edge.get("taint") or "")

        if source_agent in {"trainee", "user"} and target_type == "referee_scoring" and "sanitized" not in edge_taint:
            return {
                "rule_id": "GOV-JUDGE-001",
                "reason": "学员原始输入未经隔离影响裁判评分节点。",
                "edge": [source_node.get("id"), target_node.get("id")],
            }
        if source_agent in {"trainee", "user"} and target_type == "evidence_retrieval":
            return {
                "rule_id": "GOV-OVER-001",
                "reason": "学员输入影响证据检索节点，存在越权检索风险。",
                "edge": [source_node.get("id"), target_node.get("id")],
            }
        return None
