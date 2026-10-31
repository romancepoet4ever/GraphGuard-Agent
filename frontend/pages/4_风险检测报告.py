import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.government_demo_utils import (
    export_agent_report_markdown,
    export_agent_report_pdf,
    generate_agent_report,
    get_agent_report,
    store_agent_report,
)
from frontend.session_state import get_shared_trace_result
from frontend.ui_theme import inject_theme, pill, section


st.set_page_config(page_title="风险检测报告", page_icon="📋", layout="wide")
inject_theme()

st.title("风险检测报告")

result = get_shared_trace_result()
if not result:
    st.info("请先在“实时监测”或“Demo 场景运行”页面生成一次检测结果。")
    st.stop()

report = result["risk_report"]
if not report:
    st.info("风险报告尚未生成；当前不能判定为无风险。")
    st.stop()

section("总览结论")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Trace", report["trace_id"])
c2.metric("风险类型", report["risk_type"])
c3.metric("严重级别", report["severity"])
c4.metric("风险分数", f"{report['risk_score']:.2f}")

if report.get("audit_id"):
    st.markdown(f"<div class='gg-callout'><b>审计留痕编号：</b>{report['audit_id']}。高风险检测已写入审计日志。</div>", unsafe_allow_html=True)

if report["is_attack"]:
    st.error(report["explanation"])
else:
    st.success(report["explanation"])

section("四种检测方法", "每种检测方法都给出状态、分数和用户可读解释。")
tabs = st.tabs([item["method"] for item in result["method_summary"]])
for tab, item in zip(tabs, result["method_summary"]):
    with tab:
        a, b = st.columns([1, 3])
        with a:
            st.metric("状态", item["status"])
            st.metric("分数", f"{item['score']:.2f}")
        with b:
            st.markdown(f"<div class='gg-card'><h3>{item['method']}</h3><p>{item['principle']}</p><p><b>检测依据：</b>{item['evidence']}</p></div>", unsafe_allow_html=True)

section("风险路径")
if report["risk_path"]:
    rows = []
    for index, node_id in enumerate(report["risk_path"], start=1):
        node_data = result["graph"].nodes[node_id]
        rows.append(
            {
                "顺序": index,
                "节点": node_id,
                "名称": node_data.get("label", node_id),
                "类型": node_data.get("node_type", ""),
                "阶段": node_data.get("stage", ""),
                "数据级别": node_data.get("sensitivity", ""),
                "可见性": node_data.get("visibility", ""),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.success("未发现 source 到 sink 的高风险传播路径。")

section("命中规则")
if report["matched_rules"]:
    st.dataframe(
        [
            {
                "规则编号": rule.get("id", ""),
                "规则名称": rule.get("name", ""),
                "风险类型": rule.get("type", ""),
                "严重级别": rule.get("severity", ""),
                "处置动作": rule.get("action", ""),
                "合规依据": "，".join(rule.get("policy_refs") or []),
            }
            for rule in report["matched_rules"]
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.success("当前 trace 未命中政务高风险规则。")

section("合规依据", "这些依据来自 Gov-Security Pack 的结构化政策索引。")
policy_evidence = report.get("policy_evidence") or []
if policy_evidence:
    for item in policy_evidence:
        st.markdown(
            f"""
            <div class="gg-card">
              <h3>{item.get('policy_id', '')} {item.get('title', '')}</h3>
              <p><b>要求摘要：</b>{item.get('requirement', '')}</p>
              <p><b>建议控制：</b>{'，'.join(item.get('recommended_controls') or [])}</p>
              <p class="gg-muted">{item.get('source_url', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.success("当前场景未触发额外合规依据。")

section("数据级别与阶段约束")
constraint_rows = []
for node_id, data in result["graph"].nodes(data=True):
    constraint_rows.append(
        {
            "节点": node_id,
            "名称": data.get("label", node_id),
            "阶段": data.get("stage", ""),
            "数据级别": data.get("sensitivity", ""),
            "可见性": data.get("visibility", ""),
            "政策标签": "，".join(data.get("policy_refs") or []),
        }
    )
st.dataframe(constraint_rows, use_container_width=True, hide_index=True)

violations = report.get("process_violations") or []
if violations:
    st.warning("发现阶段约束冲突：")
    st.dataframe(
        [
            {
                "节点": item.get("node_id", ""),
                "阶段": item.get("stage", ""),
                "数据级别": item.get("sensitivity", ""),
                "说明": item.get("reason", ""),
            }
            for item in violations
        ],
        use_container_width=True,
        hide_index=True,
    )

section("节点风险排行")
node_rows = []
for node_id, score in sorted(result["risk_scores"].items(), key=lambda item: item[1], reverse=True):
    node_data = result["graph"].nodes[node_id]
    node_rows.append(
        {
            "节点": node_id,
            "名称": node_data.get("label", node_id),
            "类型": node_data.get("node_type", ""),
            "风险分": f"{score:.2f}",
            "标签": "，".join(node_data.get("security_tags") or []),
        }
    )
st.dataframe(node_rows, use_container_width=True, hide_index=True)

st.markdown(
    "".join(
        [
            pill("规则命中不是最终结论"),
            pill("最终风险来自图路径传播"),
            pill("合规依据用于解释处置动作"),
            pill("审计编号用于追溯"),
        ]
    ),
    unsafe_allow_html=True,
)

section("智能检测 Agent 报告", "可选择 Mock、OpenAI 或 OpenRouter，对四类检测结果进行政务化综合研判。")
provider_col, model_col, button_col = st.columns([1, 1.5, 1])
with provider_col:
    provider = st.selectbox(
        "模型接口",
        ["mock", "openrouter", "openai"],
        help="Mock 用于无密钥稳定演示；OpenRouter 和 OpenAI 会使用 .env 中配置的密钥。",
    )
with model_col:
    model = st.text_input("模型名（可选）", value="", placeholder="留空则使用 .env 默认模型")
with button_col:
    st.write("")
    st.write("")
    if st.button("生成智能报告", type="primary", use_container_width=True):
        try:
            agent_report = generate_agent_report(result["trace"], provider=provider, model=model or None)
            store_agent_report(agent_report)
            st.success("智能检测 Agent 报告已生成，并已写入 Trace Store。")
        except Exception as exc:
            st.error(f"生成失败：{exc}")

agent_report = get_agent_report()
if agent_report:
    risk = agent_report.get("risk_report", {})
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("报告接口", agent_report.get("provider", "mock"))
    a2.metric("风险类型", risk.get("risk_type", "none"))
    a3.metric("风险分数", f"{float(risk.get('risk_score', 0.0) or 0.0):.2f}")
    a4.metric("建议动作", risk.get("recommended_action", "allow"))
    st.markdown(
        f"""
        <div class="gg-card" style="min-height:0">
          <h3>智能检测 Agent 研判</h3>
          <p style="white-space:pre-wrap">{agent_report.get('agent_report', '未生成报告。')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    md = export_agent_report_markdown(agent_report)
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "下载 Markdown 报告",
            data=md.encode("utf-8"),
            file_name=f"{agent_report.get('trace_id', 'trace')}_risk_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with dl2:
        try:
            pdf = export_agent_report_pdf(agent_report)
            st.download_button(
                "下载 PDF 报告",
                data=pdf,
                file_name=f"{agent_report.get('trace_id', 'trace')}_risk_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.info(f"PDF 导出暂不可用：{exc}")
else:
    st.markdown(
        """
        <div class="gg-explain">
        Mock 模式不需要密钥，适合现场稳定演示；OpenRouter 会读取 .env 中的 OPENROUTER_API_KEY；
        OpenAI 模式可用于 OpenAI 或 StepFun 等 OpenAI-compatible 接口。
        </div>
        """,
        unsafe_allow_html=True,
    )
