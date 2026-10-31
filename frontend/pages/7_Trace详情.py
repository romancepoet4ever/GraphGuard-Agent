import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.government_demo_utils import build_call_tree
from frontend.session_state import get_shared_trace_result
from frontend.security_status import render_security_status
from frontend.ui_theme import inject_theme, pill, section


def _rule_label(rule):
    if isinstance(rule, dict):
        parts = [
            str(rule.get("id") or "").strip(),
            str(rule.get("name") or "").strip(),
            str(rule.get("severity") or "").strip(),
        ]
        parts = [part for part in parts if part]
        return " / ".join(parts) if parts else str(rule)
    return str(rule)


def _node_id(value):
    if isinstance(value, dict):
        for key in ("id", "node_id", "source", "target"):
            if value.get(key):
                return str(value[key])
    return str(value)


st.set_page_config(page_title="Trace 详情", page_icon="GraphGuard", layout="wide")
inject_theme()

st.title("Trace 详情")
st.write(
    "本页面向业务、安全和评审人员解释一次 Agent 运行过程：它从哪里接收输入，"
    "调用了哪些工具或模型，哪些节点变成风险源，风险又是否到达用户可见或高影响节点。"
)

result = get_shared_trace_result()
if not result:
    st.info("请先在“Trace 列表”“实时监测”或“Demo 场景运行”页面生成一次检测结果。")
    st.stop()

trace = result["trace"]
report = result["risk_report"]
graph = result["graph"]

section("Trace 元信息", "这些字段用于审计追溯和多系统对账，不依赖某一种 Agent 框架。")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Trace ID", trace.get("trace_id", "unknown"))
m2.metric("会话 ID", trace.get("session_id", "unknown"))
m3.metric("业务场景", trace.get("scenario", result.get("scenario_name", "unknown")))
m4.metric("节点/边", f"{len(trace.get('nodes') or [])}/{len(trace.get('edges') or [])}")
render_security_status(trace, (result.get("live_snapshot") or {}).get("events"))
if not report:
    st.info("Trace 已接收，风险报告尚未生成；当前不能判定为无风险。")
    st.stop()

st.markdown(
    "".join(
        [
            pill("source：风险源", "warn"),
            pill("sink：用户可见或高影响节点", "warn"),
            pill("sensitive：敏感政务数据"),
            pill("taint：污点传播标记"),
            pill("policy_refs：合规依据"),
        ]
    ),
    unsafe_allow_html=True,
)

section("检测结论", "结论由四类检测方法综合生成：图异常、节点风险、污点传播、规则引擎。")
c1, c2, c3, c4 = st.columns(4)
c1.metric("风险类型", report["risk_type"])
c2.metric("风险分数", f"{report['risk_score']:.2f}")
matched_rule_labels = [_rule_label(rule) for rule in report.get("matched_rules") or []]
c3.metric("命中规则", ", ".join(matched_rule_labels) or "未命中")
c4.metric("审计编号", report.get("audit_id") or "未生成")

st.markdown(
    f"""
    <div class="gg-explain">
    {report.get("explanation", "当前 Trace 未形成明确高危路径。")}
    </div>
    """,
    unsafe_allow_html=True,
)

section("调用链视图", "缩进表示父子调用关系；风险排查时优先查看高敏节点、外部输入节点和最终输出节点。")
tree_rows = build_call_tree(trace)
if tree_rows:
    display_rows = []
    for row in tree_rows:
        display_rows.append(
            {
                "层级": row["depth"],
                "调用节点": f"{'  ' * row['depth']}{row['label']}",
                "节点类型": row["node_type"],
                "可信级别": row["trust_level"],
                "数据级别": row["sensitivity"],
                "节点 ID": row["node_id"],
            }
        )
    st.dataframe(display_rows, use_container_width=True, hide_index=True)
else:
    st.info("当前 Trace 没有足够边信息生成调用链，仍可在下方查看节点列表。")

section("风险路径", "只有风险从源头传播到 sink 时，系统才会把它提升为高优先级处置对象。")
risk_path = report.get("risk_path") or []
risk_path_ids = [_node_id(item) for item in risk_path]
if risk_path_ids:
    path_rows = []
    for idx, node_id in enumerate(risk_path_ids, start=1):
        node = graph.nodes[node_id] if node_id in graph.nodes else {}
        path_rows.append(
            {
                "顺序": idx,
                "节点": node.get("label", node_id),
                "类型": node.get("node_type", ""),
                "可信级别": node.get("trust_level", ""),
                "数据级别": node.get("sensitivity", ""),
                "说明": node.get("display_content", ""),
            }
        )
    st.dataframe(path_rows, use_container_width=True, hide_index=True)
else:
    st.success("当前 Trace 没有形成从风险源到高影响节点的传播路径。")

section("节点明细", "每个节点都是 Agent 执行图中的一个安全观察点，不直接展示原始长文本。")
node_rows = []
for node_id, node in graph.nodes(data=True):
    node_rows.append(
        {
            "节点 ID": node_id,
            "名称": node.get("label", node_id),
            "类型": node.get("node_type", ""),
            "角色": node.get("agent", ""),
            "可信级别": node.get("trust_level", ""),
            "数据级别": node.get("sensitivity", ""),
            "是否风险源": "是" if node.get("is_source") else "否",
            "是否 sink": "是" if node.get("is_sink") else "否",
            "标签": "、".join(node.get("security_tags") or []),
            "展示内容": node.get("display_content", ""),
        }
    )
st.dataframe(node_rows, use_container_width=True, hide_index=True)

section("调试节点", "如果详情页与图展示不一致，优先检查当前 session 中是否加载了同一个 Trace。")
st.markdown(
    """
    <div class="gg-explain">
    1. 先在本页确认 Trace ID，再到“安全执行图”页查看顶部 Trace/场景指标是否一致。<br/>
    2. 如果调用链断开，检查 SecurityTrace edges 是否覆盖关键节点之间的 influences / calls / returns 关系。<br/>
    3. 如果敏感数据未被识别，检查节点 sensitivity、security_tags、policy_refs 是否写入。<br/>
    4. 如果只看到输入到输出两点，说明 SDK 接入粒度不够，需要在工具调用、检索、评分和报告节点补采集点。
    </div>
    """,
    unsafe_allow_html=True,
)
