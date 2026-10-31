from __future__ import annotations

import time
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.components.graph_renderer import render_graph
from frontend.live_api import DEFAULT_GRAPHGUARD_API, get_live_trace, list_live_traces
from frontend.session_state import store_live_snapshot
from frontend.security_status import render_security_status
from frontend.ui_theme import inject_theme, section


st.set_page_config(page_title="实时 Agent 安全监测", page_icon="🛰️", layout="wide")
inject_theme()

st.title("实时 Agent 安全监测")
st.write(
    "启动任意已接入 GraphGuard SDK、Callback、Span Hook 或 OpenTelemetry 的 Agent，"
    "或上传 SecurityTrace 后，这里会显示真实执行链路。interrogation_agent 仅是其中一个政务示例。"
)

with st.sidebar:
    st.subheader("实时连接")
    api_url = st.text_input("GraphGuard API", value=DEFAULT_GRAPHGUARD_API)
    auto_refresh = st.checkbox("每 1 秒自动刷新", value=True, key="live_auto_refresh")
    st.caption("GraphGuard API 默认端口为 8001；本控制台不依赖特定业务 Agent。")

try:
    traces = list_live_traces(api_url)
except Exception as exc:
    st.error(f"无法连接 GraphGuard 实时接口：{exc}")
    st.code("python -m uvicorn api.main:app --host 127.0.0.1 --port 8001", language="bash")
    st.stop()

if not traces:
    st.info("当前没有 Trace。启动任意已接入 Agent、运行独立插件 Demo，或上传 SecurityTrace 后会自动出现。")
    if auto_refresh:
        time.sleep(1)
        st.rerun()
    st.stop()

labels = {
    item["trace_id"]: (
        f"{item.get('source', 'sdk')} | {item.get('project', 'unknown')} | "
        f"{item.get('scenario', 'default')} | {item.get('policy_pack', 'generic_default')} | "
        f"{item.get('status', 'unknown')} | {item.get('risk_type', 'none')} "
        f"({float(item.get('risk_score', 0.0)):.2f}) | {item['trace_id']}"
    )
    for item in traces
}
query_trace_id = st.query_params.get("trace_id")
trace_options = list(labels)
if query_trace_id and query_trace_id not in labels:
    labels[query_trace_id] = str(query_trace_id)
    trace_options.insert(0, query_trace_id)
default_trace_id = query_trace_id or st.session_state.get("selected_trace_id")
default_index = trace_options.index(default_trace_id) if default_trace_id in trace_options else 0
selected_id = st.selectbox(
    "选择正在运行或最近完成的 Trace",
    options=trace_options,
    index=default_index,
    format_func=lambda value: labels[value],
)
st.session_state["selected_trace_id"] = selected_id
st.session_state["selected_live_trace_id"] = selected_id
st.query_params["trace_id"] = selected_id

try:
    snapshot = get_live_trace(selected_id, api_url)
except Exception as exc:
    st.error(f"读取实时 Trace 失败：{exc}")
    st.stop()

store_live_snapshot(snapshot)

trace = snapshot.get("trace") or {}
report_bundle = snapshot.get("report") or {}
risk_report = report_bundle.get("risk_report") or report_bundle or {}
events = snapshot.get("events") or []
metadata = trace.get("metadata") or {}
status = snapshot.get("status") or metadata.get("live_status", "unknown")
is_completed = status in {"completed", "failed", "cancelled"}

section(
    "Trace 完成正式报告" if is_completed else "运行中增量结论",
    "正式报告已在 Trace 完成后固化。" if is_completed else "风险评分会随节点和边事件持续变化，当前结论并非最终报告。",
)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("运行状态", status)
c2.metric("节点数", len(trace.get("nodes") or []))
c3.metric("边数", len(trace.get("edges") or []))
c4.metric("风险分数", f"{float(risk_report.get('risk_score', 0.0) or 0.0):.2f}")
c5.metric("严重级别", risk_report.get("severity", "none"))
st.caption(
    f"来源：{trace.get('source', 'sdk')} · 项目：{trace.get('project', 'unknown')} · "
    f"场景：{trace.get('scenario', 'default')} · Policy Pack：{metadata.get('policy_pack', 'generic_default')}"
)
render_security_status(trace, events)

if risk_report.get("is_attack"):
    st.error(risk_report.get("explanation") or "检测到高风险执行路径。")
elif risk_report:
    st.success(risk_report.get("explanation") or "当前未形成高风险传播路径。")
else:
    st.info("Trace 已开始，检测报告将在首个节点到达后生成。")

left, right = st.columns([2.2, 1])
with left:
    section("实时安全执行图", "红色边表示当前识别出的风险传播路径；运行中节点可在悬浮信息中查看 runtime_status。")
    graph_data = snapshot.get("graph_data") or {"nodes": [], "edges": []}
    if graph_data.get("nodes"):
        render_graph(graph_data, snapshot.get("risk_scores") or {})
    else:
        st.info("等待节点事件。")

with right:
    section("当前风险")
    st.write(f"**风险类型：** {risk_report.get('risk_type', 'none')}")
    st.write(f"**建议动作：** {risk_report.get('recommended_action', 'allow')}")
    risk_path = risk_report.get("risk_path") or []
    st.write("**风险路径：**")
    st.code(" → ".join(risk_path) if risk_path else "尚未形成完整风险路径")

    st.write("**命中规则：**")
    matched_rules = risk_report.get("matched_rules") or []
    if matched_rules:
        for rule in matched_rules:
            st.warning(f"{rule.get('id', '')} · {rule.get('name', '')} · {rule.get('severity', '')}")
    else:
        st.caption("当前未命中高风险规则。")

    st.write("**修复建议：**")
    suggestions = risk_report.get("repair_suggestions") or report_bundle.get("recommended_actions") or []
    if suggestions:
        for item in suggestions:
            if isinstance(item, dict):
                st.info(f"{item.get('action', 'review')}：{item.get('description', '')}")
            else:
                st.info(str(item))
    else:
        st.caption("当前无需额外修复。")

section("执行事件时间线", "用于核对安全图是否来自真实业务执行，而不是轮末固定模板。")
rows = []
for event in reversed(events[-100:]):
    payload = event.get("payload") or {}
    node = payload.get("node") or {}
    decision = payload if event.get("event_type") == "guard_decision" else {}
    rows.append(
        {
            "序号": event.get("sequence"),
            "时间": event.get("timestamp", ""),
            "事件": event.get("event_type", ""),
            "节点": node.get("label") or node.get("id") or "",
            "节点状态": (node.get("metadata") or {}).get("runtime_status", ""),
            "建议动作": decision.get("recommended_action") or decision.get("action", ""),
            "实际处置": decision.get("action_taken", "unknown") if decision else "",
            "风险类型": decision.get("risk_type", ""),
        }
    )
st.dataframe(rows, use_container_width=True, hide_index=True)

with st.expander("完整风险报告 JSON"):
    st.json(report_bundle or {"message": "report pending"})

if auto_refresh:
    time.sleep(1)
    st.rerun()
