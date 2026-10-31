import html
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.ui_theme import inject_theme, pill, section


def snippet(title: str, body: str) -> None:
    escaped = html.escape(body.strip())
    st.markdown(
        f"""
        <div class="gg-card" style="min-height:0">
          <h3>{title}</h3>
          <pre style="white-space:pre-wrap; overflow:auto; background:#0f172a; color:#e2e8f0; border-radius:8px; padding:14px; line-height:1.55; font-size:0.9rem;">{escaped}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="接入指南", page_icon="GraphGuard", layout="wide")
inject_theme()

st.title("轻量接入指南")
st.write(
    "GraphGuard-Agent 不接管业务 Agent 的编排逻辑，只作为安全观测和运行时防护中间件接入。"
    "业务系统继续使用自己的 LangChain、LangGraph、OpenAI/OpenRouter/StepFun 或其他模型调用链。"
)

section("三种接入模式", "从低风险演示到真实业务系统，可以逐步加深接入。")
cols = st.columns(3)
with cols[0]:
    st.markdown("<div class='gg-card'><h3>Trace Upload</h3><p>外部系统导出 SecurityTrace 后上传，适合快速接入、离线审计和竞赛演示。</p></div>", unsafe_allow_html=True)
with cols[1]:
    st.markdown("<div class='gg-card'><h3>Python SDK</h3><p>用装饰器或显式 API 记录关键节点，适合已有 Python Agent 服务。</p></div>", unsafe_allow_html=True)
with cols[2]:
    st.markdown("<div class='gg-card'><h3>Callback Hook</h3><p>以回调方式监听 LangChain/LangGraph 运行事件，适合不改主链路的渐进接入。</p></div>", unsafe_allow_html=True)

st.markdown(
    "".join(
        [
            pill("非侵入式"),
            pill("框架无关"),
            pill("SecurityTrace 标准化"),
            pill("运行时防护"),
            pill("政务合规报告"),
        ]
    ),
    unsafe_allow_html=True,
)

section("安装 SDK", "SDK 可独立安装，不要求业务项目与 GraphGuard 仓库位于同级目录。")
snippet(
    "Editable 安装",
    r"""
python -m pip install -e ./sdk/python
python -c "from graphguard import GraphGuardClient; print(GraphGuardClient)"
""",
)

section("方式一：上传 Trace", "适合先把闭环跑通：业务系统导出文件，GraphGuard 负责建图和检测。")
snippet(
    "运行上传样例",
    r"""
cd GraphGuard-Agent
D:\programs\AgentGraph_Sentinel\python.exe examples\basic_trace_demo.py
""",
)
st.markdown(
    """
    <div class="gg-explain">
    调试节点：脚本成功后会在 data/uploaded_traces 生成 Trace 文件。进入“Trace 列表”页，选择 uploaded 来源的 Trace 并点击分析。
    </div>
    """,
    unsafe_allow_html=True,
)

section("方式二：Python SDK", "适合在业务函数、工具调用、检索、评分、报告生成等位置采集节点。")
snippet(
    "最小接入代码",
    """
from graphguard import GraphGuardClient, traceable

gg = GraphGuardClient(
    project="my-agent",
    scenario="prompt_injection",
    policy_pack="generic_default",  # 政务场景可选 government_agent
    api_url="http://127.0.0.1:8001",
)
gg.start_trace({"session_id": "case-001", "source": "sdk"})

@traceable(client=gg, node_type="evidence_retrieval", sensitivity="highly_sensitive")
def retrieve_evidence(query: str):
    return "脱敏后的证据摘要"

retrieve_evidence("查询案件材料")
gg.save()
""",
)
snippet(
    "显式 Span",
    """
with gg.span("retrieve", node_type="tool_call", sensitivity="internal") as span:
    result = existing_tool_call()
    span.set_output_summary(result)
""",
)
st.markdown(
    """
    <div class="gg-explain">
    调试节点：如果图里只有输入和输出，说明采集点太少；建议至少覆盖 user_input、tool_call、evidence_retrieval、model_generation、referee_scoring、final_report。
    </div>
    """,
    unsafe_allow_html=True,
)

section("方式三：LangChain / LangGraph Hook", "适合保留原业务主链路，只在回调层把运行事件转成 SecurityTrace。")
snippet(
    "Callback 接入示例",
    """
from graphguard import GraphGuardClient
from graphguard.integrations.langchain import GraphGuardCallbackHandler

gg = GraphGuardClient(project="demo-agent", scenario="document_qa")
handler = GraphGuardCallbackHandler(gg)

# 将 handler 放入已有 LangChain 调用的 callbacks 参数。
# llm.invoke(messages, config={"callbacks": [handler]})
""",
)

section("observe / enforce", "observe 只观测告警；enforce 可在业务执行前阻断或在输出前脱敏。")
snippet(
    "业务侧配置",
    """
GRAPHGUARD_MODE=observe
GRAPHGUARD_POLICY_PACK=generic_default
GRAPHGUARD_CAPTURE_MODE=redacted

# 高风险演示时切换：
GRAPHGUARD_MODE=enforce
""",
)
snippet(
    "LangGraph 节点包装示例",
    """
from graphguard.integrations.langgraph import GraphGuardLangGraphHook

hook = GraphGuardLangGraphHook(gg)

def evidence_node(state):
    with hook.node("evidence_retrieval", state=state, node_type="evidence_retrieval", sensitivity="highly_sensitive"):
        return run_original_evidence_node(state)
""",
)

section("运行时防护", "在输入、工具调用、工具返回和最终输出前做轻量决策，保留 Mock 模式用于无密钥演示。")
snippet(
    "Runtime Guard 示例",
    r"""
cd GraphGuard-Agent
D:\programs\AgentGraph_Sentinel\python.exe examples\runtime_guard_demo.py
""",
)
st.markdown(
    """
    <div class="gg-explain">
    调试节点：如果 Runtime Guard 阻断了调用，检查命中的 GOV-* 规则和 action 字段；如果没有阻断，继续查看风险报告中的传播路径。
    </div>
    """,
    unsafe_allow_html=True,
)

section("方式四：FastAPI Trace 接口", "外部平台可以通过 HTTP 提交 Trace，并选择 Mock、OpenAI 或 OpenRouter 生成智能风险报告。")
snippet(
    "启动 API 服务",
    r"""
cd GraphGuard-Agent
D:\programs\AgentGraph_Sentinel\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001
""",
)
snippet(
    "Mock / OpenAI / OpenRouter 调试",
    r"""
# 默认 Mock，不需要密钥
D:\programs\AgentGraph_Sentinel\python.exe examples\api_trace_demo.py --provider mock

# OpenAI 或 StepFun 等 OpenAI-compatible 接口
$env:OPENAI_API_KEY="你的 Key"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"
D:\programs\AgentGraph_Sentinel\python.exe examples\api_trace_demo.py --provider openai

# OpenRouter
$env:OPENROUTER_API_KEY="你的 OpenRouter Key"
$env:OPENROUTER_MODEL="openai/gpt-4o-mini"
D:\programs\AgentGraph_Sentinel\python.exe examples\api_trace_demo.py --provider openrouter
""",
)
st.markdown(
    """
    <div class="gg-explain">
    调试节点：API 成功后，Trace 会进入 SQLite Store；回到“Trace 列表”页可看到 api_store 来源，并继续查看执行图和报告。
    </div>
    """,
    unsafe_allow_html=True,
)

section("方式五：OpenTelemetry-like Span JSON", "已有观测系统可以把 span JSON 转成 SecurityTrace，不需要改造成 GraphGuard 私有格式。")
snippet(
    "OTel Span 导入示例",
    r"""
cd GraphGuard-Agent
D:\programs\AgentGraph_Sentinel\python.exe examples\otel_span_demo.py
""",
)
st.markdown(
    """
    <div class="gg-explain">
    调试节点：导入后会生成 data/uploaded_traces/otel_demo_trace.json；进入“Trace 列表”选择该 Trace 查看执行图。
    </div>
    """,
    unsafe_allow_html=True,
)

section("报告导出", "API 和前端均支持导出 Markdown 与 PDF，便于提交审计材料和竞赛答辩附件。")
snippet(
    "报告导出接口",
    r"""
GET http://127.0.0.1:8001/api/v1/reports/{trace_id}/export?format=markdown
GET http://127.0.0.1:8001/api/v1/reports/{trace_id}/export?format=pdf
""",
)

section("与智能检测 Agent 的关系", "中间件先把运行过程标准化为图，后续智能检测 Agent 会在同一张图上使用四类检测方法和安全工具。")
st.markdown(
    """
    <div class="gg-card" style="min-height:0">
      <h3>推荐演进路线</h3>
      <p>第一步：离线 Trace 上传，验证展示闭环。</p>
      <p>第二步：Python SDK 采集真实业务关键节点。</p>
      <p>第三步：接入 LangChain/LangGraph Callback，补齐模型、工具、RAG、鉴权和密钥相关事件。</p>
      <p>第四步：由智能检测 Agent 综合四类检测结果，生成政务风险报告和修复建议。</p>
    </div>
    """,
    unsafe_allow_html=True,
)
