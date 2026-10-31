import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.government_demo_utils import DEMO_SCENARIOS, analyze_demo_trace, store_demo_result
from frontend.ui_theme import inject_theme, pill, section


st.set_page_config(page_title="Demo 场景运行", page_icon="▶️", layout="wide")
inject_theme()

st.title("Demo 场景运行")
st.write("选择一个内置政务安全场景，快速演示 GraphGuard-Agent 如何把 Agent 执行过程转成图，并标注风险传播路径。")

section("内置政务安全场景")
scenario = st.selectbox("选择场景", list(DEMO_SCENARIOS.keys()), index=1, help="每个场景都对应一个 SecurityTrace。")
st.markdown(f"<div class='gg-explain'>{DEMO_SCENARIOS[scenario]['summary']}</div>", unsafe_allow_html=True)

if st.button("运行场景并生成图", type="primary", use_container_width=True):
    result = analyze_demo_trace(scenario)
    store_demo_result(result)
    st.success("场景已运行。请继续查看安全执行图、风险检测报告和修复建议。")

result = st.session_state.get("government_demo_result")
if not result:
    st.info("请先运行一个场景。")
    st.stop()

report = result["risk_report"]
graph = result["graph"]
metrics = result["metrics"]

section("当前检测结果")
c1, c2, c3, c4 = st.columns(4)
c1.metric("场景", result["scenario_name"])
c2.metric("节点数", graph.number_of_nodes())
c3.metric("边数", graph.number_of_edges())
c4.metric("风险分数", f"{report['risk_score']:.2f}")

if report["is_attack"]:
    st.error(f"检测到风险：{report['risk_type']}，建议动作：{report['recommended_action']}")
else:
    st.success("未发现高风险传播路径，可作为正常训练基线。")
st.write(report["explanation"])

st.markdown(
    "".join(
        [
            pill("SecurityTrace 输入"),
            pill("NetworkX 执行图"),
            pill("GOV-* 规则"),
            pill("合规依据"),
            pill("审计留痕"),
        ]
    ),
    unsafe_allow_html=True,
)

section("图指标")
st.table(
    [
        {"指标": "节点数", "值": str(metrics.get("num_nodes", graph.number_of_nodes())), "说明": "本次执行图中的 Agent 步骤数量。"},
        {"指标": "边数", "值": str(metrics.get("num_edges", graph.number_of_edges())), "说明": "步骤之间的控制流、上下文流或风险传播关系。"},
        {"指标": "平均度", "值": f"{metrics.get('avg_degree', 0):.2f}", "说明": "图连接密度，越高说明链路越复杂。"},
        {"指标": "最长路径", "值": str(metrics.get("longest_path", "-")), "说明": "最长执行链，可辅助识别多步链式风险。"},
    ]
)

section("四种检测方法结果")
st.dataframe(
    [
        {
            "检测方法": item["method"],
            "状态": item["status"],
            "分数": f"{item['score']:.2f}",
            "依据说明": item["evidence"],
        }
        for item in result["method_summary"]
    ],
    use_container_width=True,
    hide_index=True,
)

section("命中规则")
if report["matched_rules"]:
    st.dataframe(
        [
            {
                "规则编号": rule.get("id", ""),
                "规则名称": rule.get("name", ""),
                "风险类型": rule.get("type", ""),
                "严重级别": rule.get("severity", ""),
                "建议动作": rule.get("action", ""),
                "合规依据": "，".join(rule.get("policy_refs") or []),
            }
            for rule in report["matched_rules"]
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.success("未命中高风险规则。")
