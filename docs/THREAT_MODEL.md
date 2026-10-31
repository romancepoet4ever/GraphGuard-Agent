# 威胁模型

GraphGuard-Agent 是安全中间件，本文件说明它**防什么**、**不防什么**，以及**自身的安全边界**。

结构：资产 → 攻击者与能力 → 攻击面 → 信任边界 → 缓解措施 → 残留风险。

---

## 一、资产清单

| 资产 | 位置 | 泄露或篡改的后果 |
|---|---|---|
| 执行轨迹（TraceEvent / SecurityTrace） | `data/trace_store/`、`data/security_traces/` | 暴露业务数据流、工具调用参数、模型输入 |
| 安全执行图与风险评分 | 内存 + SQLite | 攻击者可据此规避检测阈值 |
| 检测规则与策略 | `config/policy_packs/generic_default/` | 篡改规则 = 让检测失效 |
| 报告与导出物 | 报告接口、`data/` 下产物 | 报告污染，误导决策者 |
| 接入凭据 | `GRAPHGUARD_API_KEY`、模型 provider 密钥 | 伪造上报、消耗配额 |
| 业务 Agent 的控制流 | 不在本仓库 | 本中间件**不接管**，故不持有 |

---

## 二、攻击者与能力

| 攻击者 | 能力 | 主要意图 |
|---|---|---|
| **A1 外部数据提供者** | 控制网页、文档、检索结果的内容 | 通过间接提示注入改变 Agent 行为 |
| **A2 恶意工具/服务** | 控制工具返回值 | 在工具结果中夹带指令或伪造数据 |
| **A3 知识库投毒者** | 可写入被检索的资料 | 让生成器引用伪造事实 |
| **A4 恶意用户** | 可构造输入 | 角色覆盖、越权索取、套取敏感数据 |
| **A5 内部误用者** | 有仓库/部署访问权 | 改规则、关防护、导出数据 |
| **A6 供应链攻击者** | 控制上游依赖 | 通过依赖植入代码 |

不在威胁范围：**拥有主机 root / 数据库管理员权限的攻击者**（本层防护无法对抗）。

---

## 三、攻击面

| 攻击面 | 入口 | 相关组件 |
|---|---|---|
| 用户输入 | `check_input`、`POST /api/v1/analyze` | `sdk/python/graphguard/runtime_guard.py`、`api/routers/traces.py` |
| 外部数据 / 检索结果 | Trace 中的 observation 节点 | `src/detection/ipi_detector.py`、`rule_engine.py` |
| 工具调用 | `check_tool_call` | `config/policy_packs/generic_default/tool_policy.yaml` |
| 工具返回 | `check_tool_result` | `src/detection/taint_analysis.py` |
| 输出 / 报告 | `check_output`、报告导出 | `src/utils/report_exporter.py` |
| 上报接口 | `POST /api/v1/traces`、`POST /api/v1/otel/analyze` | `api/routers/traces.py` |
| 策略文件 | `config/policy_packs/` | `src/policy/` |
| 依赖 | `requirements.txt`、`web-console/package.json` | 构建与运行时 |

---

## 四、信任边界

```text
[不受信] 用户输入 / 外部网页 / 检索结果 / 工具返回
    │  ← 边界 1：所有进入图的数据一律视为不可信，由检测层判定
    ▼
[受信] GraphGuard 检测与策略（本地、确定性）
    │  ← 边界 2：防护热路径不调用外部模型
    ▼
[受信] 业务 Agent 执行
    │  ← 边界 3：本中间件旁路接入，不改变业务控制流
    ▼
[不受信] 输出与报告（可能含未验证结论）
```

**三条边界的设计含义**：

1. **边界 1**：不假设任何输入是安全的，包括工具返回值。
2. **边界 2**：判定逻辑本地执行，避免"检测器本身被外部模型操纵"。
3. **边界 3**：中间件失败不得阻断业务（fail-open 默认），代价是"极端情况下可能漏防"。

---

## 五、缓解措施

### 5.1 GraphGuard 防什么

| 威胁 | 机制 | 规则 / 代码位置 | 覆盖 |
|---|---|---|---|
| 间接提示注入 | 规则匹配 + 语义检测 | `GG-PI-001`、`src/detection/ipi_detector.py` | 强（英文）/ 弱（中文） |
| 角色覆盖 | 用户输入中的角色覆写检测 | `GG-ROLE-001` | 覆盖明确模式 |
| 敏感数据外泄 | 污点传播：外部源 → 公开汇 | `GG-LEAK-001`、`src/detection/taint_analysis.py` | 覆盖已建模的源与汇 |
| 个人信息公开 | 输出侧 PII 识别与掩码 | `GG-PII-001` | 覆盖常见 PII 模式 |
| 知识库投毒 | 被污染材料进入生成/报告时隔离 | `GG-POISON-001` | 覆盖检索路径 |
| 报告污染 / 未验证结论 | 对未验证声明降级或标注 | `GG-OUT-001` | 覆盖结论落入持久输出 |
| 工具越权 | 高危工具白名单 + 污点联动阻断 | `tool_policy.yaml`（`raw_db_query` / `read_secret` / `send_email` / `shell`） | 高危工具 + 污点上下文 |
| 执行路径异常 | 图编辑距离对比 | `src/detection/graph_anomaly.py` | 依赖基线图质量 |
| 节点级语义异常 | 嵌入分类 | `src/detection/node_embedding.py`、`gnn_model.py` | 需 ML 依赖，缺失时降级 |

### 5.2 GraphGuard 自身的安全边界

| 设计取舍 | 具体行为 | 原因 |
|---|---|---|
| **旁路接入** | 不接管业务 Agent 的调度、模型选择、权限校验、业务流程 | 轻量接入的前提；接管即耦合 |
| **默认 fail-open** | 检测链路异常时不阻断业务；可设 `GRAPHGUARD_FAIL_OPEN=false` 改为失败关闭 | 可用性优先；安全团队可自行切换 |
| **默认 observe** | 只观测与告警，不改变输入/工具调用/输出；`enforce` 需手动开启 | 降低误伤风险 |
| **隐私采集档位** | `metadata_only` / `redacted`（默认）/ `full`；`full` 需手动开启 | 最小必要采集 |
| **防护热路径不调外部模型** | 四阶段 `check_*` 为本地确定性判断 | 避免引入延迟与外部依赖 |
| **不采集隐藏思维链** | 只记录事件与结构化字段 | 隐私与合规 |
| **事件幂等** | `event_id` 唯一约束 | 防重复上报污染图 |

---

## 六、残留风险与已知限制

| 残留风险 | 说明 | 缓解方向 |
|---|---|---|
| **中文注入覆盖弱于英文** | 规则与语义检测对英文识别率更高 | 增加中英文规则对，扩充中文样本 |
| **工具越权只告警不阻断** | 统一由通用规则归类为 `review`，不自动 block | 在 `tool_policy.yaml` 中按业务手动提升为 `block` |
| **fail-open 的代价** | 中间件崩溃时业务继续运行，但失去防护 | 生产环境设 `FAIL_OPEN=false` 并配监控 |
| **ML 依赖缺失时降级** | 无 `torch`/`transformers` 时节点嵌入与 GNN 失效 | 安装完整依赖，或接受规则+污点两层防护 |
| **基线图质量依赖历史数据** | 图异动检测需可信基线 | 定期人工复核基线 |
| **策略可被有权限者修改** | 内部误用者（A5）可关闭规则 | 规则变更走 PR + CODEOWNERS 审查 |
| **无防御的内在威胁** | 拥有主机/数据库权限者可读全量 Trace | 部署侧隔离与访问控制 |
| **报告结论可能被过度信任** | 风险评分是辅助判断，不是判决 | 报告中标注 `review` 语义与证据链 |

---

## 七、与本文件相关的其它文档

- 安全报告渠道与响应时限：[`SECURITY.md`](../SECURITY.md)
- 支持范围：[`SUPPORT.md`](../SUPPORT.md)
- 架构与边界：[`architecture.md`](architecture.md)
- 测试与覆盖情况：[`testing.md`](testing.md)
