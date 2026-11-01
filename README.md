# GraphGuard-Agent
## 面向高风险业务智能体的轻量接入式安全观测与运行时防护中间件

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)

---

## 🎯 项目简介

GraphGuard-Agent 是面向高风险业务智能体的**轻量接入式**安全观测与运行时防护中间件。它把 Agent 的执行链路构建成一张安全执行图，在图上检测提示注入、敏感数据泄露、工具越权、知识库投毒、输出操纵等风险，并给出实时告警、运行时处置、风险路径解释与审计报告。

**它不接管业务 Agent 的注册、调度、模型选择或编排**，只做旁路观测与关键点防护。

核心链路：

```text
业务 Agent / LangChain / LangGraph / 自研服务
  -> GraphGuard SDK / Callback / Trace Upload
  -> SecurityTrace
  -> 安全执行图
  -> 规则引擎 / 污点传播 / 图异动 / 节点语义嵌入
  -> 风险融合与运行时处置（allow / alert / sanitize / block）
  -> 报告导出（Markdown / PDF）与审计
```

### 关键接口

```text
POST /api/v1/traces
POST /api/v1/analyze
GET  /api/v1/reports/{trace_id}
GET  /api/v1/reports/{trace_id}/export?format=markdown|pdf
GET  /api/v1/traces
POST /api/v1/otel/analyze
```

系统同时支持 OpenTelemetry-like Span JSON 适配：把已有观测系统的 span 数据转换成 SecurityTrace 后，进入同一套检测流程。

## ✨ 主要特性

以下每条都可在本仓库内验证：

1. **旁路接入，不接管编排**：通过 SDK / Callback / Trace 上传接入，业务 Agent 的调度与模型选择不受影响（验证：`examples/` 中的接入示例可独立运行）。
2. **四类检测同图协同**：规则、污点传播、图异动、节点语义嵌入在同一张安全执行图上融合打分（验证：`src/detection/` 四个模块 + `data/demo_traces/` 10 个样本）。
3. **运行时四阶段防护**：`check_input` / `check_tool_call` / `check_tool_result` / `check_output`，支持 `observe` 与 `enforce` 两种模式（验证：`sdk/python/graphguard/runtime_guard.py` 及测试用例）。
4. **Policy Pack 可插拔**：规则、数据分级与处置动作由 YAML 描述，默认使用 `generic_default`（验证：`config/policy_packs/`）。
5. **风险可解释、可导出**：每次告警可回溯到具体节点、边与命中规则，并可导出 Markdown / PDF 报告（验证：`/api/v1/reports/{trace_id}` 与 `src/utils/report_exporter.py`）。

报告生成支持三种 provider：`mock`（无密钥、可离线演示）、`openai`（OpenAI 兼容接口）、`openrouter`。

## 🏗️ 系统架构

```text
┌─────────────────────────────────────────────┐
│ Web Console（React/Vite，主控制台）         │
│ Streamlit 控制台（legacy 备用）             │
├─────────────────────────────────────────────┤
│ FastAPI 后端 API 服务（:8001）              │
│ ┌─────────────────────────────────────────┐ │
│ │ 核心：Graph Security Engine             │ │
│ │  ├─ 轨迹图构建器                        │ │
│ │  ├─ 图异动检测（GED 算法）              │ │
│ │  ├─ 节点嵌入检测（BERT）                │ │
│ │  ├─ 污点传播分析（图着色）              │ │
│ │  ├─ GNN 风险传播                        │ │
│ │  └─ 动态图手术                          │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ 外部工具层（LangGraph Agent）               │
└─────────────────────────────────────────────┘
```

**模块边界**：`api/` 只做请求编排与路由；`src/detection/` 只负责打分、不执行处置；`src/defense/` 负责审计与处置落地；`sdk/python/graphguard/` 是唯一面向业务应用的接入面。中间件**不修改**业务 Agent 的输入、工具调用与输出（`enforce` 模式下按策略阻断或脱敏除外）。

## 📦 安装部署

### 环境要求

- Python 3.11+
- 8GB+ RAM
- （可选）NVIDIA GPU（用于加速ML模型）
### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/romancepoet4ever/GraphGuard-Agent.git
cd GraphGuard-Agent

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量（可选，不配置也能运行）
#    .env.example      完整模板，含模型 provider 与检测阈值
#    env.live.example  业务应用接入的最小集合
#    Windows: copy .env.example .env
cp .env.example .env

# 5. 创建必要目录
mkdir -p logs data/attack_samples data/benign_traces

# 6. 启动后端服务（二选一，均监听 8001）
python -m scripts.run_server
# 或：python -m uvicorn api.main:app --host 127.0.0.1 --port 8001

# 7. 启动前端（新终端）
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501

#访问：

#前端界面：http://localhost:8501

#API文档：http://localhost:8001/docs
```
```bash
#🚀 快速体验
#命令行演示（需先启动 API；该接口依赖模型生成执行图，需配置 OPENROUTER_API_KEY）
python scripts/demo_attack.py                      # 运行全部场景
python scripts/demo_attack.py email_exfiltration   # 只运行单个场景
                                                   # 可选：email_exfiltration / benign / file_stealing

#Web界面演示
#访问 http://localhost:8501

# 选择"攻击演示"页面

# 选择攻击场景（如"邮件泄露攻击"）

# 点击"执行检测（AGS防护）"

# 查看可视化检测结果
```

### 主控制台（Web Console，推荐）

产品主控制台是 `web-console/` 下的独立 React/Vite 应用；`frontend/` 的 Streamlit 版保留为 legacy 备用。

```powershell
cd web-console
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

深链接：

```text
http://127.0.0.1:5174/traces/{trace_id}
http://127.0.0.1:5174/?trace_id={trace_id}
```

旧的查询参数形式仍会被接受，并跳转到 `/traces/{trace_id}`。业务应用接入时设置
`GRAPHGUARD_CONSOLE_URL=http://127.0.0.1:5174`，`GRAPHGUARD_API_URL=http://127.0.0.1:8001`
仅用于事件上报。

## 🔗 与下游系统的关系

本仓库是 GraphGuard-Agent **中间件本体**，不包含任何业务应用。

出于保密与合规要求，本项目已进行脱敏处理：本仓库不展示、不包含任何具体下游智能体的名称、代码、配置、数据或截图，因此不会出现政务、气象等业务智能体。相关接入验证在独立、受控环境中完成，不属于本仓库的发行内容。

- 中间件通过 SDK / Callback / Trace 上传接入业务 Agent；业务 Agent 的代码、配置与数据始终留在各自仓库，不随本仓库分发。
- 团队在下游智能体系统上做过接入验证，但这些下游系统独立部署、未纳入本仓库，出于保密与脱敏要求不在本仓库展示。
- `examples/` 中的示例不依赖任何具体业务系统，可独立运行。

## 📚 使用指南
### 实时检测

```python

import requests

response = requests.post(
    "http://localhost:8001/api/detection/analyze",
    json={
        "user_input": "总结这个网页",
        "external_data": "<html>...potentially malicious content...</html>"
    }
)

result = response.json()
print(f"风险评分: {result['result']['overall_risk_score']:.2%}")
print(f"建议措施: {result['result']['recommended_action']}")
```

> 该接口属旁路检测路由，需配置 `OPENROUTER_API_KEY`；未配置时路由会自动禁用（返回 404），不影响 `/api/v1/*` 主链路。

### 图可视化

访问"图可视化"页面，输入内容后点击"生成执行图"即可查看：

执行流程的完整图结构

每个节点的风险评分

交互式拖拽和缩放

## 🧪 测试与评测

### 运行测试

```bash
# 依赖安装（含 pytest）
pip install -r requirements.txt

# 必须先设置该变量（任意非空值即可，不需要真实密钥）；
# 未设置时 detection 路由被禁用，会有 3 个用例失败
export OPENROUTER_API_KEY=dummy          # Windows PowerShell: $env:OPENROUTER_API_KEY='dummy'

pytest tests -v --ignore=tests/frontend
```

当前基线：**Core 96 passed**。分套件结果见 [`docs/testing.md`](docs/testing.md)。
`tests/frontend` 需要与 Streamlit 兼容的 `protobuf`（>=3.20）。

> 如需覆盖率，先额外安装 `pytest-cov`，再使用 `pytest tests -v --cov=src`。

### 关键指标

数据出处：`evaluation/results/final/summary.json`（公开文本数据集与性能）。

**公开文本数据集（2,162 条）**

| 数据集 | 攻击 / 正常 | Recall | Precision | F1 |
|---|---|---|---|---|
| BIPIA | 200 / 200 | 1.000 | 0.893 | 0.943 |
| InjecAgent | 300 / 200 | 0.283 | 1.000 | 0.442 |
| PoisonedRAG | 100 / 100 | 1.000 | 1.000 | 1.000 |
| SafeRAG | 200 / 200 | 0.095 | 0.864 | 0.171 |
| deepset | 263 / 399 | 0.190 | 1.000 | 0.319 |

**公开 Trace 场景**：8 个场景、470 条 Trace（BIPIA 100、InjecAgent 150、PoisonedRAG 100、SafeRAG 120），路径检出率均为 1.0。

**性能（单线程）**

| 操作 | 规模 | 平均延迟 | P95 |
|---|---|---|---|
| Guard 判定 | 单次 | 0.005 ms | 0.005 ms |
| Trace 分析 | 10 节点 | 0.051 ms | 0.106 ms |
| Trace 分析 | 100 节点 | 0.354 ms | 0.398 ms |
| Trace 分析 | 500 节点 | 2.44 ms | 3.38 ms |

## 📁 项目结构

```text
GraphGuard-Agent/
├── sdk/python/graphguard/   # 接入层：埋点 SDK、Runtime Guard、框架集成
├── api/                     # FastAPI 后端（traces / live / detection / visualization）
├── src/                     # 核心引擎
│   ├── adapters/            # SecurityTrace 与 OpenTelemetry 适配
│   ├── core/                # 图构建、Trace 存储、事件重建
│   ├── detection/           # 检测引擎与风险融合
│   ├── policy/              # 策略加载、数据分级、权限与流程约束
│   ├── defense/             # 审计记录与防护
│   ├── agents/              # 智能检测 Agent 与模型客户端
│   ├── models/              # 数据模型
│   └── utils/               # 报告导出、图工具、日志
├── config/                  # 配置与 Policy Pack
├── web-console/             # React/Vite 主控制台
├── frontend/                # Streamlit legacy 控制台
├── lib/                     # 前端本地资源（vis-network / tom-select）
├── tests/                   # 测试
├── examples/                # 接入示例
├── scripts/                 # 运行与调试脚本
└── docs/                    # 文档
```

## 🛠️ 开发指南

### 添加新检测器

1. 在 `src/detection/` 下新建模块，对外暴露检测函数或类，返回包含 `is_malicious`、`score`、`details` 的结果字典。
2. 接入检测链：规则型检测接入 `src/detection/` 下风险融合引擎的规则分派（`_evaluate_rule`）；文本/旁路型检测接入 `api/routers/detection.py` 的融合逻辑。
3. 同步更新前端展示，并补充对应测试用例。

### 添加新攻击场景

编辑 `frontend/pages/2_攻击演示.py` 中的 `scenarios` 字典。

## ⚠️ 已知限制

- **中文提示注入覆盖弱于英文**：规则与语义检测对英文注入的识别率明显更高。
- **工具越权只告警不阻断**：该类风险统一由通用规则 `AGS-GENERIC-001` 归类为 `review`，不自动 block。
- **外部模型验收不可复现**：`evaluation/` 保留了数据集、结果产物与评测脚本（`evaluation/runners`、`evaluation/scripts`），但真实外部模型（Semantic / Qwen）的验收不在本仓库范围内。
- **ML 检测依赖可选依赖**：`torch` / `transformers` 缺失时，节点嵌入与 GNN 模块自动降级，其余检测与防护不受影响。
- **Streamlit 控制台有 protobuf 版本要求**：`google.protobuf` 需 >= 3.20，否则 `import streamlit` 失败。
- **真实模型 provider 依赖外部服务**：`mock` 模式可完全离线演示；`openai` / `openrouter` 的稳定性与配额由外部服务决定。

> 发现问题？缺陷与建议请提交到 [Issues](https://github.com/romancepoet4ever/GraphGuard-Agent/issues)，安全漏洞请按 [SECURITY.md](SECURITY.md) 私下报告；支持范围与响应预期见 [SUPPORT.md](SUPPORT.md)。

## 🔬 附录：核心算法实现

#### 1. 图异动检测（MELON 升级）

```python
# 基于图编辑距离（GED）
def detect_anomaly(G_orig, G_mask):
    ged = graph_edit_distance(G_orig, G_mask)
    anomaly_score = ged / max_nodes
    return anomaly_score > threshold
```

原理：

G_orig：包含外部数据的执行图

G_mask：外部数据被遮蔽的对照图

如果外部数据仅是数据，两图应同构

如果包含攻击指令，G_orig会出现额外节点（如send_email）

#### 2. 节点嵌入检测

```python
# 在Observation节点植入BERT分类器
def scan_observation(text):
    # 规则快速检测
    if match_malicious_patterns(text):
        return True, 1.0
    
    # BERT深度检测
    probs = bert_classifier(text)
    return probs['malicious'] > 0.7
```

#### 3. 污点传播分析

```python
# 图着色算法
def taint_propagation(G):
    # 源头着色
    trust_levels = {
        'user_input': GREEN,
        'web_search': RED
    }
    
    # 沿边传播
    for node in topological_sort(G):
        if any(pred is RED for pred in predecessors(node)):
            trust_levels[node] = RED
```

#### 4. 动态图手术

```python
# 插入Sanitizer节点
def graph_surgery(G, risk_scores):
    for node in high_risk_nodes:
        sanitizer = create_sanitizer_node()
        redirect_edge(node, sanitizer)
```

## 📚 参考

- MELON: "Prompt Injection attack against LLM-integrated Applications"
- InstructDetector: "Detecting Prompt Injection Attacks"
- Spotlighting: "Spotlighting for LLMs with Safety and Reliability"
