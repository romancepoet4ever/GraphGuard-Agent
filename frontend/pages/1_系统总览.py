import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.government_demo_utils import DEMO_SCENARIOS, gov_pack_status
from frontend.ui_theme import inject_theme, pill, section


st.set_page_config(page_title="系统总览", page_icon="🛡️", layout="wide")
inject_theme()

st.title("系统总览")
st.write(
    "GraphGuard-Agent 是面向政务 AI Agent 的轻量接入式安全观测与运行时防护中间件。"
    "它通过 SDK、装饰器、Callback 或 Trace 上传采集执行链路，再用图结构解释风险如何传播、如何阻断、如何留痕。"
)

section("系统状态")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("政务 Demo", len(DEMO_SCENARIOS))
c2.metric("接入方式", "SDK/Trace")
c3.metric("图输入", "SecurityTrace")
c4.metric("图引擎", "NetworkX")
c5.metric("规则体系", "GOV-*")

section("轻量接入能力", "系统不替代业务 Agent，也不做调度平台，只在安全观测、防护和审计层接入。")
i1, i2, i3, i4 = st.columns(4)
i1.markdown("<div class='gg-card'><h3>Trace Upload</h3><p>上传标准 SecurityTrace，完成离线审计。</p></div>", unsafe_allow_html=True)
i2.markdown("<div class='gg-card'><h3>Python SDK</h3><p>用装饰器或显式 API 采集关键函数、工具、检索和报告节点。</p></div>", unsafe_allow_html=True)
i3.markdown("<div class='gg-card'><h3>Callback Hook</h3><p>接入 LangChain/LangGraph 回调层，保留原业务链路。</p></div>", unsafe_allow_html=True)
i4.markdown("<div class='gg-card'><h3>Runtime Guard</h3><p>在高风险输入、工具调用和最终输出前执行阻断、脱敏或审计。</p></div>", unsafe_allow_html=True)

section("Gov-Security Pack 状态", "政策法规、数据分级、角色权限、阶段约束和审计能力已结构化接入。")
status = gov_pack_status()
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("政策库", f"{status['policy_count']} 条")
s2.metric("数据分级", status["data_classification"])
s3.metric("角色权限", status["role_permissions"])
s4.metric("阶段约束", status["process_constraints"])
s5.metric("审计/脱敏", "enabled")

st.markdown(
    "".join(
        [
            pill("生成式 AI 服务治理"),
            pill("数据安全"),
            pill("个人信息保护"),
            pill("政务数据共享"),
            pill("数据分类分级"),
            pill("AI 安全治理框架"),
        ]
    ),
    unsafe_allow_html=True,
)

section("核心创新：从线性检测到图状执行检测")
left, right = st.columns(2)
with left:
    st.markdown(
        """
        <div class="gg-card">
          <h3>传统线性检测</h3>
          <p>按输入、工具调用、输出顺序逐段检查，容易漏掉跨节点传播、间接影响和裁判污染。</p>
          <p class="gg-muted">典型视角：user_input -> agent_output</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with right:
    st.markdown(
        """
        <div class="gg-card">
          <h3>GraphGuard-Agent</h3>
          <p>把输入、策略、证据、记忆、裁判和报告建成有向图，检查风险源是否到达高影响 sink。</p>
          <p class="gg-muted">典型视角：source -> decision -> retrieval -> generation -> sink</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

section("四种检测方法")
tabs = st.tabs(["图异动检测", "节点嵌入检测", "污点传播分析", "规则引擎"])
with tabs[0]:
    st.markdown("<div class='gg-card'><h3>图异动检测</h3><p>比较当前执行图与正常训练基线，关注异常边、异常 sink、路径长度突变和高影响节点。</p></div>", unsafe_allow_html=True)
with tabs[1]:
    st.markdown("<div class='gg-card'><h3>节点嵌入检测</h3><p>对用户输入、证据检索、记忆写入、最终报告等节点进行语义风险定位。</p></div>", unsafe_allow_html=True)
with tabs[2]:
    st.markdown("<div class='gg-card'><h3>污点传播分析</h3><p>追踪不可信输入、敏感证据、个人信息、投毒材料是否沿边传播到用户可见或高影响节点。</p></div>", unsafe_allow_html=True)
with tabs[3]:
    st.markdown("<div class='gg-card'><h3>规则引擎</h3><p>通过编号化 GOV-* 规则给出可解释的命中依据、严重级别、政策依据和建议动作。</p></div>", unsafe_allow_html=True)

section("政务场景")
for name, item in DEMO_SCENARIOS.items():
    st.markdown(f"<div class='gg-callout'><b>{name}</b><br/><span class='gg-muted'>{item['summary']}</span></div>", unsafe_allow_html=True)
