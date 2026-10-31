import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.government_demo_utils import (
    analyze_trace_file,
    list_available_traces,
    save_uploaded_trace,
    store_demo_result,
)
from frontend.ui_theme import inject_theme, pill, section


st.set_page_config(page_title="Trace 列表", page_icon="GraphGuard", layout="wide")
inject_theme()

st.title("Trace 列表与上传")
st.write(
    "这里是 GraphGuard-Agent 的轻量接入入口。业务系统只需要生成 SecurityTrace，"
    "即可导入本平台完成执行图建模、四类检测、风险路径定位和政务合规报告生成。"
)

section("接入方式", "同一套检测能力可以接收离线样例、SDK 采集结果、LangChain/LangGraph 回调结果和第三方系统上传。")
c1, c2, c3, c4 = st.columns(4)
c1.markdown("<div class='gg-card'><h3>离线 Demo</h3><p>用于回归测试，快速展示正常与攻击场景差异。</p></div>", unsafe_allow_html=True)
c2.markdown("<div class='gg-card'><h3>Python SDK</h3><p>通过装饰器或显式记录节点，把业务调用链导出为 SecurityTrace。</p></div>", unsafe_allow_html=True)
c3.markdown("<div class='gg-card'><h3>Callback Hook</h3><p>面向 LangChain/LangGraph，在不接管编排逻辑的前提下采集运行事件。</p></div>", unsafe_allow_html=True)
c4.markdown("<div class='gg-card'><h3>Trace Upload</h3><p>外部 Agent 平台可直接上传标准 Trace 文件，作为安全中间件接入。</p></div>", unsafe_allow_html=True)

section("上传 SecurityTrace", "上传后系统会立即转换为 Agent 执行图，并输出风险分数、命中规则和传播路径。")
uploaded = st.file_uploader("选择 SecurityTrace 文件", type=["json"], help="文件需要包含 trace_id、nodes、edges 等字段。页面不会展示原始 JSON。")
if uploaded is not None:
    try:
        saved_path = save_uploaded_trace(uploaded)
        result = analyze_trace_file(saved_path)
        store_demo_result(result)
        st.success("Trace 已导入并完成检测。可以进入“Trace 详情”“安全执行图”或“风险检测报告”继续查看。")
        report = result["risk_report"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Trace ID", result["trace"].get("trace_id", "unknown"))
        m2.metric("风险类型", report["risk_type"])
        m3.metric("风险分数", f"{report['risk_score']:.2f}")
        m4.metric("风险路径", f"{len(report.get('risk_path') or [])} 节点")
    except Exception as exc:  # pragma: no cover - Streamlit runtime feedback
        st.error(f"导入失败：{exc}")

section("可用 Trace", "选择任一 Trace 作为当前分析对象；风险分数越高，越需要查看风险路径和修复建议。")
rows = list_available_traces()
if not rows:
    st.info("还没有可分析的 Trace。请先上传文件，或运行 examples 目录下的 SDK 示例生成样例。")
    st.stop()

left, right = st.columns([2, 1])
with left:
    selected_label = st.selectbox(
        "选择 Trace",
        [f"{row['trace_id']} | {row['scenario']} | {row['source']}" for row in rows],
    )
    selected = rows[[f"{row['trace_id']} | {row['scenario']} | {row['source']}" for row in rows].index(selected_label)]
with right:
    st.write("")
    st.write("")
    if st.button("分析并设为当前 Trace", type="primary", use_container_width=True):
        result = analyze_trace_file(selected["path"])
        store_demo_result(result)
        st.success("已切换当前 Trace。")

st.markdown(
    "".join(
        [
            pill("demo：内置演示样例"),
            pill("uploaded：外部业务系统上传"),
            pill("api_store：通过 HTTP API 提交"),
            pill("interrogation_agent：真实政务训练 Web 链路"),
            pill("ok：未形成高危传播路径", "ok"),
            pill("warning：存在需要复核的风险", "warn"),
            pill("critical：存在高危路径", "risk"),
        ]
    ),
    unsafe_allow_html=True,
)

table_rows = []
for row in rows:
    table_rows.append(
        {
            "Trace ID": row["trace_id"],
            "项目": row["project"],
            "场景": row["scenario"],
            "来源": row["source"],
            "风险类型": row["risk_type"],
            "风险分数": "未知" if row["risk_score"] is None else f"{row['risk_score']:.2f}",
            "状态": row["status"],
            "风险路径": row["path"],
            "生成时间": row["created_at"],
        }
    )
st.dataframe(table_rows, use_container_width=True, hide_index=True)

section("调试节点", "接入失败时按下面顺序定位，能最快判断问题在文件、Schema、Adapter 还是检测器。")
st.markdown(
    """
    <div class="gg-explain">
    1. 先确认 Trace 文件包含 nodes 和 edges，且每条边的 source/target 都能找到对应节点。<br/>
    2. 如果上传失败，运行：python -m py_compile frontend/government_demo_utils.py src/adapters/security_trace_adapter.py。<br/>
    3. 如果图为空，检查节点是否有 id、label、node_type；检查边是否有 source、target、edge_type。<br/>
    4. 如果风险分数异常，进入“策略规则”页查看 GOV-* 规则是否覆盖当前场景。
    </div>
    """,
    unsafe_allow_html=True,
)
