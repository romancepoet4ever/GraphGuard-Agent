import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.government_demo_utils import gov_pack_status
from frontend.ui_theme import inject_theme, pill, section
from src.policy.policy_pack_loader import PolicyPackLoader


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency feedback
        raise RuntimeError("缺少 PyYAML，无法读取策略配置。") from exc
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def severity_tone(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "risk"
    if severity in {"medium", "warning"}:
        return "warn"
    return "ok"


st.set_page_config(page_title="策略规则", page_icon="GraphGuard", layout="wide")
inject_theme()

st.title("政务策略与检测规则")
st.write(
    "本页面展示 GraphGuard-Agent 如何把通用 Agent 安全检测与政务场景规则结合。"
    "规则用于解释风险来源、合规依据和建议动作，不以原始配置文件形式展示。"
)

status = gov_pack_status()
section("Gov-Security Pack 状态", "策略包来自 tools 目录下政务安全材料的整理结果，并被融合进前端报告和检测引擎。")
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("政策条目", f"{status['policy_count']} 条")
s2.metric("数据分级", status["data_classification"])
s3.metric("角色权限", status["role_permissions"])
s4.metric("流程约束", status["process_constraints"])
s5.metric("审计能力", "已启用")

policy_data = load_yaml(ROOT / "config" / "gov_policy" / "policy_index.yaml")
loader = PolicyPackLoader()
available = list(loader.available())
current_trace = (st.session_state.get("government_demo_result") or {}).get("trace") or {}
current_pack = loader.normalize((current_trace.get("metadata") or {}).get("policy_pack"))
selected_pack = st.selectbox("Policy Pack", available, index=available.index(current_pack) if current_pack in available else 0)
pack = loader.load(selected_pack)
st.caption(f"当前策略包：{pack.name} · 版本：{pack.version}")

section("检测规则", "展示所选策略包的真实配置；government_weather 包含 WX-01 至 WX-06 气象业务风险规则。")
rules = pack.rules
rule_rows = []
for rule in rules:
    rule_rows.append(
        {
            "规则编号": rule.get("id", ""),
            "规则名称": rule.get("name", ""),
            "风险类型": rule.get("type", ""),
            "等级": rule.get("severity", ""),
            "建议动作": rule.get("action", ""),
            "合规依据": "、".join(rule.get("policy_refs") or []),
        }
    )

if rule_rows:
    st.dataframe(rule_rows, use_container_width=True, hide_index=True)
    st.markdown(
        "".join(
            [
                pill("critical/high：优先阻断或隔离", "risk"),
                pill("medium：告警并复核", "warn"),
                pill("low：记录审计", "ok"),
            ]
        ),
        unsafe_allow_html=True,
    )
else:
    st.warning("所选策略包没有规则，请检查 config/policy_packs。")

section("规则卡片", "用于现场讲解：每条规则都不是孤立关键词，而是会结合图路径和 sink 节点判断。")
for rule in rules:
    tone = severity_tone(str(rule.get("severity", "")).lower())
    st.markdown(
        f"""
        <div class="gg-card" style="min-height:0; margin-bottom:12px">
          <h3>{rule.get("id", "")} {rule.get("name", "")}</h3>
          <p>
            {pill("等级：" + str(rule.get("severity", "")), tone)}
            {pill("类型：" + str(rule.get("type", "")))}
            {pill("动作：" + str(rule.get("action", "")))}
          </p>
          <p><b>判断逻辑：</b>{rule.get("condition") or "结合 source/sink、节点标签、污点传播和命中模式进行综合判定。"}</p>
          <p><b>合规依据：</b>{"、".join(rule.get("policy_refs") or ["未配置"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

section("政策依据", "政策条目用于报告中的 compliance_refs 字段，帮助评审理解为何这是政务场景风险。")
policies = policy_data.get("policies") or []
policy_rows = []
for policy in policies:
    policy_rows.append(
        {
            "编号": policy.get("id", ""),
            "名称": policy.get("title", ""),
            "发布/归口": policy.get("issuer", ""),
            "覆盖领域": "、".join(policy.get("domains") or []),
            "关联规则": "、".join(policy.get("related_rules") or []),
            "控制措施": "、".join(policy.get("recommended_controls") or []),
        }
    )

if policy_rows:
    st.dataframe(policy_rows, use_container_width=True, hide_index=True)
else:
    st.info("未读取到政策索引。")

section("四类检测方法如何使用规则", "规则引擎不是简单敏感词过滤，而是把文本信号放回 Agent 执行图里验证。")
c1, c2, c3, c4 = st.columns(4)
c1.markdown("<div class='gg-card'><h3>图异常检测</h3><p>识别异常边、异常 sink、跨阶段访问和与基线不一致的工具调用。</p></div>", unsafe_allow_html=True)
c2.markdown("<div class='gg-card'><h3>节点嵌入检测</h3><p>定位提示注入、报告污染、敏感证据和个人信息等语义风险节点。</p></div>", unsafe_allow_html=True)
c3.markdown("<div class='gg-card'><h3>污点传播分析</h3><p>追踪不可信输入、敏感政务数据、密钥和个人信息是否到达高影响节点。</p></div>", unsafe_allow_html=True)
c4.markdown("<div class='gg-card'><h3>规则引擎</h3><p>输出 GOV-* 命中依据、风险等级、审计编号和修复动作。</p></div>", unsafe_allow_html=True)

section("调试节点", "新增或修改规则后，用一个离线 Trace 快速验证规则是否生效。")
st.markdown(
    """
    <div class="gg-explain">
    1. 修改 config/government_rules.yaml 后，重新打开本页确认规则表能正常读取。<br/>
    2. 在“Trace 列表”页选择一个相关场景并重新分析，查看风险报告中的命中规则。<br/>
    3. 如果规则没有命中，检查 node_type、security_tags、sensitivity、trust_level 和 edge taint 是否与规则条件一致。<br/>
    4. 如果前端显示旧结果，重新点击“分析并设为当前 Trace”，刷新 session 中的检测结果。
    </div>
    """,
    unsafe_allow_html=True,
)
