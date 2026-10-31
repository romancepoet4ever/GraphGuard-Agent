from __future__ import annotations

from typing import Any

import streamlit as st

from frontend.government_demo_utils import SecurityTraceAdapter, build_call_tree, build_method_summary, build_risk_scores
from frontend.live_api import DEFAULT_GRAPHGUARD_API, get_live_trace
from src.utils.graph_utils import calculate_graph_metrics


def store_live_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    trace = snapshot["trace"]
    report_bundle = snapshot.get("report") or {}
    report = report_bundle.get("risk_report") or report_bundle
    adapter = SecurityTraceAdapter()
    graph = adapter.trace_to_security_graph(trace)
    result = {
        "scenario_name": trace.get("scenario", "live_trace"),
        "trace_path": f"live_api:{trace.get('trace_id')}",
        "trace": trace,
        "graph": graph,
        "graph_data": snapshot.get("graph_data") or adapter.graph_to_visualization_data(graph, report.get("risk_path", [])),
        "risk_report": report,
        "risk_scores": snapshot.get("risk_scores") or build_risk_scores(graph, report),
        "method_summary": build_method_summary(report),
        "metrics": calculate_graph_metrics(graph),
        "call_tree": build_call_tree(trace),
        "live_snapshot": snapshot,
    }
    st.session_state["selected_trace_id"] = trace.get("trace_id")
    st.session_state["selected_live_trace_id"] = trace.get("trace_id")
    st.session_state["government_demo_result"] = result
    st.session_state["live_latest_seq"] = snapshot.get("latest_seq", 0)
    return result


def get_shared_trace_result(api_url: str = DEFAULT_GRAPHGUARD_API) -> dict[str, Any] | None:
    """Return the selected Trace, preferring the Live API over file scanning."""
    query_trace_id = st.query_params.get("trace_id")
    selected_trace_id = (
        query_trace_id
        or st.session_state.get("selected_live_trace_id")
        or st.session_state.get("selected_trace_id")
    )
    cached = st.session_state.get("government_demo_result")
    cached_id = ((cached or {}).get("trace") or {}).get("trace_id")
    if selected_trace_id and selected_trace_id != cached_id:
        try:
            return store_live_snapshot(get_live_trace(str(selected_trace_id), api_url))
        except Exception:
            st.error("无法读取所选 Trace；不会用其他 Trace 的旧报告替代。请检查实时 API 连接后重试。")
            return None
    return cached
