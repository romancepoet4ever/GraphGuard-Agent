import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.components.graph_renderer import render_graph
from frontend.session_state import get_shared_trace_result
from frontend.ui_theme import inject_theme, pill, section


st.set_page_config(page_title="安全执行图", page_icon="🕸️", layout="wide")
inject_theme()

st.title("安全执行图")
st.write("本页是核心展示：把 Agent 的执行过程画成图，并用颜色、形状和边高亮解释风险如何传播。")

result = get_shared_trace_result()
if not result:
    st.info("请先在“实时监测”或“Demo 场景运行”页面生成一次检测结果。")
    st.stop()

report = result["risk_report"]
section("图上风险摘要")
c1, c2, c3, c4 = st.columns(4)
c1.metric("场景", result["scenario_name"])
c2.metric("风险类型", report["risk_type"])
c3.metric("风险分数", f"{report['risk_score']:.2f}")
c4.metric("传播边数", max(0, len(report["risk_path"]) - 1))

st.markdown(
    "".join(
        [
            pill("SRC：风险源", "warn"),
            pill("SINK：用户可见或高影响节点", "warn"),
            pill("LOCK：敏感/高敏数据"),
            pill("SAN：净化节点"),
            pill("红色粗边：风险传播路径", "risk"),
            pill("绿色/橙色/红色边框：低/中/高风险"),
        ]
    ),
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="gg-explain">
    图不是简单流程图。它展示了不可信输入、证据检索、生成输出、裁判评分和最终报告之间的影响关系。
    当风险源沿边到达 SINK，系统会把对应路径高亮为红色。
    </div>
    """,
    unsafe_allow_html=True,
)

section("Agent 执行图")
render_graph(result["graph_data"], result["risk_scores"])

section("风险传播路径")
if report["risk_path"]:
    path_rows = []
    for index, node_id in enumerate(report["risk_path"], start=1):
        node_data = result["graph"].nodes[node_id]
        path_rows.append(
            {
                "顺序": index,
                "节点": node_id,
                "名称": node_data.get("label", node_id),
                "类型": node_data.get("node_type", ""),
                "数据级别": node_data.get("sensitivity", ""),
                "风险标签": "，".join(node_data.get("security_tags") or []),
                "展示内容": node_data.get("display_content", ""),
            }
        )
    st.dataframe(path_rows, use_container_width=True, hide_index=True)
else:
    st.success("当前场景未形成高风险传播路径。")

section("节点说明")
rows = []
for node in result["graph_data"]["nodes"]:
    rows.append(
        {
            "节点": node["id"],
            "名称": node["label"],
            "类型": node["type"],
            "角色说明": "风险源" if node["is_source"] else ("高影响节点" if node["is_sink"] else "过程节点"),
            "风险标签": "，".join(node["security_tags"]),
            "展示内容": node["display_content"],
        }
    )
st.dataframe(rows, use_container_width=True, hide_index=True)
