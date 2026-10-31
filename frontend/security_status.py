"""Present recorded runtime actions without mistaking recommendations for enforcement."""
from __future__ import annotations

from typing import Any

import streamlit as st


def runtime_security_status(trace: dict[str, Any], events: list[dict[str, Any]] | None = None) -> dict[str, str]:
    metadata = trace.get("metadata") or {}
    summary = metadata.get("security_summary") or {}
    mode = summary.get("mode") or metadata.get("graphguard_mode") or metadata.get("mode") or "unknown"
    recorded = [event.get("payload") or {} for event in events or [] if event.get("event_type") == "guard_decision"]
    effective = [item for item in recorded if item.get("action_taken")]
    top = max(effective, key=lambda item: float(item.get("risk_score") or 0), default={})
    return {
        "mode": str(mode),
        "action_taken": str(summary.get("action_taken") or top.get("action_taken") or "unknown"),
        "policy_pack": str(metadata.get("policy_pack") or "unknown"),
    }


def render_security_status(trace: dict[str, Any], events: list[dict[str, Any]] | None = None) -> None:
    status = runtime_security_status(trace, events)
    mode, action, policy = st.columns(3)
    mode.metric("防护模式", status["mode"])
    action.metric("实际处置", status["action_taken"])
    policy.metric("Policy Pack", status["policy_pack"])
    st.caption("observe 仅观测告警；enforce 可阻断或脱敏。实际处置仅展示业务适配器记录，unknown 表示尚无执行证据，不等于安全。")
