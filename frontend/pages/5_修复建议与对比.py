import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.session_state import get_shared_trace_result
from frontend.ui_theme import inject_theme, pill, section


st.set_page_config(page_title="修复建议与对比", page_icon="🧰", layout="wide")
inject_theme()

st.title("修复建议与对比")
st.write("本页把检测结果转化为可执行防护动作，说明应该阻断哪里、脱敏哪里、隔离哪里，以及修复前后执行图风险有什么变化。")

result = get_shared_trace_result()
if not result:
    st.info("请先在“实时监测”或“Demo 场景运行”页面生成一次检测结果。")
    st.stop()

report = result["risk_report"]
if not report:
    st.info("风险报告尚未生成，暂无可验证的修复建议。")
    st.stop()

section("推荐动作")
c1, c2, c3, c4 = st.columns(4)
c1.metric("推荐动作", report["recommended_action"])
c2.metric("风险分数", f"{report['risk_score']:.2f}")
c3.metric("风险类型", report["risk_type"])
c4.metric("审计编号", report.get("audit_id") or "未触发")

st.markdown(
    "".join(
        [
            pill("block：阻断", "risk"),
            pill("sanitize：净化/脱敏", "warn"),
            pill("isolate：上下文隔离", "warn"),
            pill("audit：审计留痕"),
        ]
    ),
    unsafe_allow_html=True,
)

section("修复建议")
suggestions = report.get("repair_suggestions") or []
if suggestions:
    for index, item in enumerate(suggestions, start=1):
        edge_text = ""
        if item.get("edge"):
            edge_text = f"<p class='gg-muted'>建议处理边：{item['edge'][0]} -> {item['edge'][1]}</p>"
        st.markdown(
            f"""
            <div class="gg-card">
              <h3>{index}. {item.get('action', 'review')}</h3>
              <p>{item.get('description', '')}</p>
              {edge_text}
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.success("当前场景不需要额外修复动作。")

section("修复前后对比")
left, right = st.columns(2)
with left:
    st.markdown("<div class='gg-card'><h3>修复前</h3><p>风险源可能沿执行图传播到敏感证据、裁判评分或最终报告。</p></div>", unsafe_allow_html=True)
    if report["risk_path"]:
        st.markdown(
            f"<div class='gg-callout'><b>风险路径：</b>{' → '.join(report['risk_path'])}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.success("未形成高风险路径。")
with right:
    action = report["recommended_action"]
    if action == "block_sensitive_content":
        text = "在敏感证据进入用户可见输出前阻断或脱敏，改为最小化摘要。"
    elif action == "isolate_referee_context":
        text = "裁判节点只接收结构化事实，不接收用户原始指令或角色扮演内容。"
    elif action == "downgrade_or_label_unverified_claim":
        text = "未证实陈述降级为待核实信息，禁止进入最终事实结论。"
    elif action == "quarantine_poisoned_material":
        text = "疑似投毒材料进入隔离区，检索前执行来源校验与指令剥离。"
    elif action == "mask_personal_information":
        text = "对手机号、身份证号、住址、姓名等个人信息执行脱敏或摘要化输出。"
    elif action == "block_or_sanitize":
        text = "拦截越权指令，或在风险源后插入 sanitizer 净化节点。"
    else:
        text = "维持当前流程，并保留审计记录。"
    st.markdown(f"<div class='gg-card'><h3>修复后</h3><p>{text}</p></div>", unsafe_allow_html=True)

section("一句话说明")
st.markdown(
    """
    <div class="gg-explain">
    GraphGuard-Agent 的修复重点不是只删除敏感词，而是在执行图上切断不可信输入到高影响节点的传播路径，
    同时保留合规依据和审计留痕。
    </div>
    """,
    unsafe_allow_html=True,
)
