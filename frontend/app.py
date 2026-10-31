import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.government_demo_utils import DEMO_SCENARIOS, analyze_demo_trace, gov_pack_status, store_demo_result
from frontend.ui_theme import inject_theme, pill, section
from frontend.session_state import get_shared_trace_result
from frontend.security_status import render_security_status


st.set_page_config(
    page_title="GraphGuard-Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

st.markdown(
    """
    <div class="gg-hero">
      <h1>GraphGuard-Agent</h1>
      <p>
        面向高风险政务智能体的轻量接入式安全观测与运行时防护中间件。
        业务系统可通过 SDK、装饰器、Callback 或 Trace 上传接入；系统把一次 Agent
        运行过程建模为安全执行图，识别不可信输入如何影响证据检索、裁判评分和最终报告，
        并给出合规依据、风险路径和修复动作。
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

section("快速体验", "选择一个政务场景，一键生成安全执行图和风险报告。")
left, right = st.columns([2, 1])
with left:
    scenario = st.selectbox("演示场景", list(DEMO_SCENARIOS.keys()), index=1)
    st.caption(DEMO_SCENARIOS[scenario]["summary"])
with right:
    st.write("")
    st.write("")
    if st.button("运行 Demo 并查看图", type="primary", use_container_width=True):
        result = analyze_demo_trace(scenario)
        store_demo_result(result)
        st.success("已生成执行图、风险报告和修复建议。请在左侧进入“安全执行图”。")

result = get_shared_trace_result()
if result:
    report = result["risk_report"]
    st.caption(f"当前 Trace：{result['trace'].get('trace_id', 'unknown')}")
    render_security_status(result["trace"], (result.get("live_snapshot") or {}).get("events"))
    st.page_link("pages/7_Trace详情.py", label="查看当前 Trace 详情")
    if not report:
        st.info("Trace 已接收，风险报告尚未生成。")
        st.stop()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("当前场景", result["scenario_name"])
    c2.metric("风险类型", report["risk_type"])
    c3.metric("风险分数", f"{report['risk_score']:.2f}")
    c4.metric("审计编号", report.get("audit_id") or "未触发")

section("轻量接入式中间件", "不接管业务编排，只采集安全 Trace，并在图上完成检测、防护和审计。")
mw1, mw2, mw3, mw4 = st.columns(4)
with mw1:
    st.markdown("<div class='gg-card'><h3>Trace Upload</h3><p>已有 Agent 平台可直接上传 SecurityTrace，快速进入图检测闭环。</p></div>", unsafe_allow_html=True)
with mw2:
    st.markdown("<div class='gg-card'><h3>Python SDK</h3><p>在关键函数、工具调用、检索、评分和报告节点采集执行事件。</p></div>", unsafe_allow_html=True)
with mw3:
    st.markdown("<div class='gg-card'><h3>Callback Hook</h3><p>面向 LangChain/LangGraph，以回调方式接入，不重写主链路。</p></div>", unsafe_allow_html=True)
with mw4:
    st.markdown("<div class='gg-card'><h3>Runtime Guard</h3><p>在输入、工具调用、工具返回和最终输出前执行阻断、脱敏或审计。</p></div>", unsafe_allow_html=True)

section("核心创新", "从线性流程检测升级为 Agent 图状执行检测。")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        """
        <div class="gg-card">
          <h3>线性检测的问题</h3>
          <p>只看输入和输出，难以解释风险是否经过证据、记忆、裁判等中间节点传播。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        """
        <div class="gg-card">
          <h3>执行图建模</h3>
          <p>把用户输入、策略判断、证据检索、生成、评分、报告建成有向图。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        """
        <div class="gg-card">
          <h3>图上风险解释</h3>
          <p>标注风险源、敏感节点、高影响 sink 和红色传播路径，说明风险如何形成。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

section("四种检测方法", "每一种方法都在前端给出状态、分数、依据和解释。")
method_cols = st.columns(4)
methods = [
    ("图异动检测", "比较当前执行图与正常基线，识别异常边、异常 sink 和路径突变。"),
    ("节点嵌入检测", "对用户输入、证据、记忆、报告等节点做语义风险定位。"),
    ("污点传播分析", "追踪不可信输入、敏感证据、个人信息是否到达高影响节点。"),
    ("规则引擎", "使用 GOV-* 政务规则输出可解释命中依据和处置动作。"),
]
for col, (title, text) in zip(method_cols, methods):
    with col:
        st.markdown(f"<div class='gg-card'><h3>{title}</h3><p>{text}</p></div>", unsafe_allow_html=True)

section("政务场景适配", "Gov-Security Pack 将法规、数据分级、角色权限、阶段约束和审计留痕接入检测报告。")
status = gov_pack_status()
g1, g2, g3, g4, g5 = st.columns(5)
g1.metric("政策库", f"{status['policy_count']} 条")
g2.metric("数据分级", status["data_classification"])
g3.metric("角色权限", status["role_permissions"])
g4.metric("阶段约束", status["process_constraints"])
g5.metric("审计/脱敏", "enabled")

st.markdown(
    "".join(
        [
            pill("P-001 生成式 AI 服务治理"),
            pill("P-002 数据安全法"),
            pill("P-003 个人信息保护法"),
            pill("P-004 数据分类分级"),
            pill("P-005 政务数据共享"),
            pill("P-007 AI 安全治理框架"),
        ]
    ),
    unsafe_allow_html=True,
)

section("使用路径")
st.markdown(
    """
    <div class="gg-explain">
    1. 进入“Trace 列表”上传外部 SecurityTrace，或进入“实时监测”输入一段执行指令和外部政务材料。<br/>
    2. 系统将 Trace 转换为安全执行图，并运行图异动、节点嵌入、污点传播和规则引擎四类检测。<br/>
    3. 进入“Trace 详情”“安全执行图”“风险检测报告”查看调用链、风险路径、合规依据和审计编号。
    </div>
    """,
    unsafe_allow_html=True,
)
