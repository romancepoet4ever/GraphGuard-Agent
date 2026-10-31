from __future__ import annotations

from typing import Any

from graphguard.traceable import traceable


class GraphGuardGenericCallback:
    def __init__(self, client) -> None:
        self.client = client
        self._last_node_id: str | None = None

    def on_event(self, node_type: str, payload: dict[str, Any]) -> str:
        text = str(payload.get("text") or payload.get("args") or payload.get("tool_name") or payload)
        tags = []
        if any(token in text.lower() for token in ["忽略", "绕过", "system prompt", "全部证据"]):
            tags.append("prompt_injection_candidate")
        if any(token in text for token in ["核心证人", "调查底稿", "身份证", "手机号"]):
            tags.append("sensitive_evidence")
        if node_type == "user_visible_sink":
            tags.append("user_visible_sink")

        node_id = self.client.record_node(
            label=str(payload.get("label") or node_type),
            node_type=node_type,
            agent=str(payload.get("agent") or "callback"),
            raw_content=text,
            display_content=text[:240],
            trust_level=str(payload.get("trust_level") or ("untrusted" if node_type == "user_input" else "trusted")),
            sensitivity=str(payload.get("sensitivity") or ("sensitive" if "sensitive_evidence" in tags else "public")),
            visibility="user_visible" if node_type in {"user_input", "user_visible_sink"} else "internal_only",
            security_tags=tags,
            is_source=node_type == "user_input" or bool(tags),
            is_sink=node_type == "user_visible_sink",
            metadata={k: v for k, v in payload.items() if k not in {"text"}},
        )
        if self._last_node_id:
            self.client.record_edge(self._last_node_id, node_id, edge_type="callback_sequence", taint="untrusted_input")
        self._last_node_id = node_id
        return node_id


__all__ = ["GraphGuardGenericCallback", "traceable"]
