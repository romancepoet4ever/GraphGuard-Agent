# 系统架构

GraphGuard-Agent 观测并防护一个**已存在**的 Agent，但不拥有它的编排。

---

## 一、定位与边界

### 1.1 它做什么

```text
既有业务 Agent
  -> SDK / 装饰器 / Callback / Span Hook / OpenTelemetry / Trace 上传
  -> 有序 TraceEvent 采集
  -> SQLite 持久化 + 物化 SecurityTrace
  -> 确定性污点分析、路径分析与 Policy Pack 判定
  -> 运行时 alert / sanitize / block + 审计报告
  -> React 控制台 / Streamlit 控制台 / 业务安全摘要
```

### 1.2 它**不**接管什么（核心设计主张）

| 不接管的部分 | 归属 |
|---|---|
| 业务 Agent 的注册与调度 | 业务系统 |
| 模型选择与推理参数 | 业务系统 |
| 业务权限校验与身份认证 | 业务系统 |
| 业务流程编排与状态机 | 业务系统 |
| 业务数据的存储与生命周期 | 业务系统 |

本中间件是**旁路观测 + 关键点防护**：它读取执行链路、给出判定、按策略决定放行或处置，但不改变业务 Agent 的控制流（`enforce` 模式下的阻断与脱敏除外）。

---

## 二、组件与职责

| 组件 | 路径 | 职责 | **不**负责 |
|---|---|---|---|
| **接入 SDK** | `sdk/python/graphguard/` | Trace/Span 生命周期、本地脱敏、运行时四阶段判定、异步导出 | 业务编排、模型调用 |
| **API 服务** | `api/` | 请求编排与路由（traces / live / detection / visualization） | 检测算法本身 |
| **图构建** | `src/core/graph_builder.py` | 把 SecurityTrace 构建为有向图 | 打分与判定 |
| **存储** | `src/core/live_trace_store.py`、`trace_store.py` | 事件幂等写入、物化最新 Trace 与报告 | 分析逻辑 |
| **检测层** | `src/detection/` | 规则、污点、图异动、节点嵌入，输出分数与证据 | **不执行处置** |
| **策略层** | `src/policy/` | Policy Pack 加载、数据分级、权限与流程约束 | 不产生风险分 |
| **防护与审计** | `src/defense/` | 审计记录与处置落地 | 不判定风险 |
| **智能检测 Agent** | `src/agents/` | 汇总证据生成报告与修复建议 | 不参与热路径判定 |
| **适配层** | `src/adapters/` | SecurityTrace、OpenTelemetry、业务对象到通用图的映射 | 不改变业务语义 |
| **配置** | `config/` | 服务配置与 Policy Pack（YAML） | 不包含业务数据 |
| **主控制台** | `web-console/` | React/Vite 可视化与交互 | 独立服务，仅调用 API |
| **备用控制台** | `frontend/` | Streamlit legacy 界面 | 同上 |

**分层原则**：检测层只打分、不处置；防护层只处置、不打分；两者由 `api/` 与 `src/agents/` 编排。这样替换检测算法不会影响处置路径。

---

## 三、数据流

```text
[业务 Agent]
   │ ① SDK 埋点 / Callback / OTel Span / Trace 上传
   ▼
[TraceEvent 队列]  event_id 唯一，乱序到达按序归一
   │ ②
   ▼
[SQLite]  live_events（append-only） → live_traces（物化）
   │ ③
   ▼
[SecurityTrace]  结构化执行轨迹
   │ ④ graph_builder
   ▼
[安全执行图]  节点 = observation / tool_call / generation / output
   │ ⑤ 检测层并行
   ├─ rule_engine        （策略规则命中）
   ├─ taint_analysis     （源 → 汇 传播路径）
   ├─ graph_anomaly      （与基线图的编辑距离）
   └─ node_embedding     （节点语义异常）
   │ ⑥ 风险融合
   ▼
[风险报告]  分数 / 命中规则 / 证据链 / 建议动作
   │ ⑦
   ├─ 运行时：allow / alert / sanitize / block
   └─ 持久化：报告导出（Markdown / PDF）+ 审计记录
```

**每一步的失败处理**：②③ 失败时 SDK 回退本地 JSON；⑤ 的 ML 子模块缺失时自动降级；⑦ 导出失败不阻断业务（fail-open）。

---

## 四、控制流：observe 与 enforce

```text
业务 Agent 调用
   │
   ▼
check_input ──► check_tool_call ──► check_tool_result ──► check_output
   │                  │                    │                  │
   └──────────────┬───┴────────────────────┴──────────────────┘
                  ▼
          决策：allow / alert / sanitize / block
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   observe 模式         enforce 模式
   （只记录与告警）      （阻断或脱敏后返回）
```

- **四个阶段都是本地确定性判断**，不调用外部模型，保证微秒级与稳定性。
- **默认 `observe`**：不改变业务 Agent 的输入、工具调用与输出。
- **`enforce` 需手动开启**：按 Policy Pack 的 action 执行阻断或脱敏。

---

## 五、部署图

```text
┌─────────────────────────────┐        ┌──────────────────────────────┐
│ 业务应用进程                 │        │ GraphGuard API（:8001）       │
│  ├─ 业务 Agent               │  HTTP  │  ├─ /api/v1/traces           │
│  └─ GraphGuard SDK ──────────┼───────►│  ├─ /api/v1/analyze          │
│     （埋点 + 运行时防护）     │        │  ├─ /api/v1/reports/{id}     │
└─────────────────────────────┘        │  └─ /api/v1/otel/analyze     │
                                        │       │                      │
┌─────────────────────────────┐        │       ▼                      │
│ React 控制台（:5174）        │◄───────┤  SQLite（data/trace_store/）  │
└─────────────────────────────┘        └──────────────────────────────┘
┌─────────────────────────────┐                 ▲
│ Streamlit 控制台（:8501）    │◄────────────────┘
└─────────────────────────────┘
```

| 进程 | 端口 | 是否必需 |
|---|---|---|
| GraphGuard API | 8001 | ✅ 必需，所有能力由它提供 |
| React 控制台 | 5174 | 可选（主控制台） |
| Streamlit 控制台 | 8501 | 可选（legacy fallback） |

---

## 六、存储与失败模型

- 事件**仅追加**，按 `event_id` 幂等；重复上报通过唯一约束与 `IntegrityError` 处理。
- SQLite 物化最新 Trace 与报告；数据库文件位于 `data/trace_store/`，首次启动自动创建。
- SDK 保留本地 JSON 回退，默认 **fail-open**：GraphGuard 不可用时不中断业务 Agent。
- 防护热路径不依赖外部 LLM，也不采集隐藏思维链。
