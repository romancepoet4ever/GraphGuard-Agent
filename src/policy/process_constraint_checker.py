from __future__ import annotations

from typing import Any

from src.policy.policy_loader import GovPolicyLoader


class ProcessConstraintChecker:
    def __init__(self, loader: GovPolicyLoader | None = None) -> None:
        self.loader = loader or GovPolicyLoader()
        self.stages = (self.loader.load("process_constraints.yaml").get("stages") or {})

    def check_node(self, node: dict[str, Any]) -> dict[str, Any] | None:
        stage = str(node.get("stage") or "")
        sensitivity = str(node.get("sensitivity") or "public")
        stage_rule = self.stages.get(stage) or {}
        forbidden = set(stage_rule.get("forbidden_evidence_levels") or [])
        if sensitivity in forbidden:
            return {
                "stage": stage,
                "sensitivity": sensitivity,
                "reason": f"{stage_rule.get('label', stage)} 不允许使用或展示 {sensitivity} 数据。",
            }
        return None
