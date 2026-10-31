from __future__ import annotations

import time
import re
from typing import Any

from graphguard.decisions import GuardDecision
from graphguard.policy import get_policy_pack


_PERSONAL_INFORMATION_PATTERN = re.compile(
    r"(?:1[3-9]\d{9})|(?:\d{17}[\dXx])|(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})"
)


class GraphGuardRuntime:
    """Local deterministic guard delegated to the selected Policy Pack."""

    def __init__(self, client) -> None:
        self.client = client
        self.policy_pack = get_policy_pack(getattr(client, "policy_pack", "generic_default"))
        self._last_node_id: str | None = None

    def _record_guard_node(self, *, taint: str = "", guard_stage: str = "", **kwargs) -> str:
        metadata = dict(kwargs.get("metadata") or {})
        metadata.update({"guard_stage": guard_stage, "policy_pack": self.policy_pack.name})
        kwargs["metadata"] = metadata
        node_id = self.client.record_node(**kwargs)
        if self._last_node_id:
            self.client.record_edge(
                self._last_node_id,
                node_id,
                edge_type="guard_sequence",
                taint=taint,
                metadata={"guard_stage": guard_stage, "policy_pack": self.policy_pack.name},
            )
        self._last_node_id = node_id
        return node_id

    def _record_decision(self, decision: GuardDecision) -> GuardDecision:
        decision.metadata = {"policy_pack": self.policy_pack.name, **dict(decision.metadata or {})}
        self.client.record_guard_decision(decision.to_dict())
        return decision

    @staticmethod
    def _attach_latency(decision: GuardDecision, started_at: float) -> None:
        decision.metadata = {
            **dict(decision.metadata or {}),
            "guard_latency_ms": round((time.perf_counter() - started_at) * 1000, 3),
        }

    def check_input(self, user_input: str, metadata: dict[str, Any] | None = None) -> GuardDecision:
        started_at = time.perf_counter()
        decision = self.policy_pack.check_input(user_input, metadata or {})
        contains_personal_information = bool(_PERSONAL_INFORMATION_PATTERN.search(user_input or ""))
        if contains_personal_information and decision.risk_type == "none":
            decision = GuardDecision(
                action="alert",
                risk_score=0.8,
                risk_type="personal_information_leakage",
                severity="high",
                matched_rules=["GOV-PII-001"] if self.policy_pack.name == "government_agent" else ["GG-PII-001"],
                reason="输入包含未脱敏的个人信息。",
            )
        self._attach_latency(decision, started_at)
        tags = []
        if decision.risk_type == "prompt_injection":
            tags.append("prompt_injection_candidate")
        if contains_personal_information:
            tags.append("personal_information")
        # Personal information is a sensitive-data source, not evidence that
        # the user has maliciously influenced protected decision nodes. Only
        # control-flow attacks become untrusted propagation sources.
        control_flow_risk = decision.risk_type in {"prompt_injection", "role_escape", "knowledge_poisoning"}
        self._record_guard_node(
            label="runtime input check",
            node_type="user_input",
            agent="user",
            raw_content=user_input,
            display_content=user_input[:240],
            trust_level="untrusted",
            visibility="user_visible",
            security_tags=tags,
            is_source=control_flow_risk,
            risk_score=decision.risk_score,
            metadata=metadata or {},
            taint="untrusted_input" if control_flow_risk else ("sensitive_data" if contains_personal_information else ""),
            guard_stage="input",
        )
        return self._record_decision(decision)

    def check_tool_call(
        self,
        tool_name: str,
        tool_args: dict,
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        context = context or {}
        started_at = time.perf_counter()
        decision = self.policy_pack.check_tool_call(tool_name, tool_args, context)
        self._attach_latency(decision, started_at)
        high_risk = decision.risk_score > 0 or decision.action == "block"
        self._record_guard_node(
            label=f"tool call: {tool_name}",
            node_type="tool_call",
            agent="tool",
            raw_content=str(tool_args),
            display_content=str(tool_args)[:240],
            sensitivity="internal",
            security_tags=["high_risk_tool"] if high_risk else [],
            risk_score=decision.risk_score,
            metadata={
                "tool_name": tool_name,
                "guard_action": decision.action,
                "blocked": decision.action == "block",
                "runtime_status": "blocked" if decision.action == "block" else "completed",
                **context,
            },
            taint=str(context.get("taint") or ""),
            guard_stage="tool_call",
        )
        return self._record_decision(decision)

    def check_tool_result(
        self,
        tool_name: str,
        result: Any,
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        context = context or {}
        text = str(result)
        started_at = time.perf_counter()
        decision = self.policy_pack.check_tool_result(tool_name, result, context)
        self._attach_latency(decision, started_at)
        sensitive = decision.risk_type != "none"
        self._record_guard_node(
            label=f"tool result: {tool_name}",
            node_type="tool_result",
            agent="tool",
            raw_content=text,
            display_content=text[:240],
            sensitivity=str(context.get("sensitivity") or ("sensitive" if sensitive else "public")),
            security_tags=["sensitive_evidence"] if sensitive else [],
            is_source=sensitive,
            risk_score=decision.risk_score,
            metadata=context,
            taint=str(context.get("taint") or ("sensitive_data" if sensitive else "")),
            guard_stage="tool_result",
        )
        return self._record_decision(decision)

    def check_output(self, output: str, context: dict[str, Any] | None = None) -> GuardDecision:
        context = context or {}
        started_at = time.perf_counter()
        decision = self.policy_pack.check_output(output, context)
        self._attach_latency(decision, started_at)
        user_visible = str(context.get("visibility") or "user_visible").lower() == "user_visible"
        sensitive = decision.risk_type != "none"
        tags = ["user_visible_sink"] if user_visible else []
        if sensitive:
            tags.append("sensitive_evidence")
        self._record_guard_node(
            label="runtime output check",
            node_type="user_visible_sink",
            agent="system",
            raw_content=output,
            display_content=output[:240],
            sensitivity=str(context.get("sensitivity") or ("sensitive" if sensitive else "public")),
            visibility=str(context.get("visibility") or "user_visible"),
            security_tags=tags,
            is_sink=user_visible,
            risk_score=decision.risk_score,
            metadata=context,
            taint=str(context.get("taint") or ("sensitive_data" if sensitive else "")),
            guard_stage="output",
        )
        return self._record_decision(decision)
