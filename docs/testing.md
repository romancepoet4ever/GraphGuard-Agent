# 测试与评测

本文件记录如何运行测试、验证环境、结果与已知未覆盖项。

每项结果都要标注状态，不留空。

| 状态 | 含义 |
|---|---|
| `PASS` | 已运行，结果符合预期 |
| `PARTIAL` | 部分通过，或可查但不可完整复现 |
| `PARTIAL` | 部分可查、部分不可复现 |
| `NOT_TESTED` | 未测试 |

---

## 如何运行

### 准备工作

```bash
# 1. 安装依赖（已包含 pytest）
pip install -r requirements.txt

# 2. 设置密钥变量（任意非空值即可，不需要真实密钥）
#    Windows PowerShell:
$env:OPENROUTER_API_KEY = 'dummy'
#    macOS / Linux:
export OPENROUTER_API_KEY=dummy
```

> 未设置该变量时 `detection` 路由会被禁用，部分用例会失败。

### 运行后端测试

```bash
# 全量（排除前端目录）
pytest tests -v --ignore=tests/frontend

# 单个模块
pytest tests/sdk -v
pytest tests/policy_packs -v

# 按关键字
pytest tests -k "runtime_guard"
```

### 运行前端测试

```bash
# 需要与 Streamlit 兼容的 protobuf（>= 3.20）
pytest tests/frontend -v
```

### 前端构建检查

```bash
cd web-console
npm ci
npm run build
```

---

## 测试环境

| 项 | 值 |
|---|---|
| 提交 | `91c96b9` |
| 操作系统 | Windows 11 |
| Python | **3.12.7** |
| torch | 2.14.1 |
| transformers | 5.20.2 |
| streamlit | 1.66.1 |
| protobuf | **7.36.2**（需 >= 3.20） |
| fastapi / uvicorn | 0.162.0 / 0.54.0 |
| networkx | 3.7 |
| pydantic | 2.14.1 |
| Policy Pack | `generic_default` |
| 检测阈值 | `GRAPH_ANOMALY_THRESHOLD=0.3`、`NODE_RISK_THRESHOLD=0.7` |
| 演示数据 | `data/demo_traces/` 8 个场景样本 |

> 上述依赖版本取自**干净虚拟环境**（`pip install -r requirements.txt`，安装 122 个包，耗时约 13 分钟）。在系统 Python 上运行可能因全局包冲突（如 protobuf 版本过低）出现与项目无关的失败。

---

## 结果

分套件报告，**不合计为单一总测试数**。

| 套件 | 用例 | 状态 | 说明 |
|---|---:|---|---|
| Core（`tests/`） | **96** | `PASS` | `pytest tests` |
| Evaluation（`evaluation/tests/`） | 66 | `PASS` | 需 `evaluation/v3/` 与 v3 数据集 |
| Weather（下游气象应用） | 307 | `PASS` | 下游业务系统，独立仓库 |
| Interrogation（下游谈话训练应用） | 16 | `PASS` | 下游业务系统，独立仓库 |

用例数、样本数、执行次数、探针数与套件数含义不同，禁止相加为"总测试数"。

历史 `482` 是 `93 + 66 + 307 + 16` 的算术汇总，混合了不同语义的套件，已废弃。

### 关于评测结果的复现性

`evaluation/` 目录包含数据集（18 个文件）、结果（47 个文件）与图表（60 个文件），但**评测脚本（`evaluation/core`、`evaluation/runners`）不在本仓库内**。

因此公开的评测数字属于「**结果可查、过程不可复现**」：

- 结果产物与图表可在 `evaluation/results/`、`evaluation/figures/` 中查阅；
- 无法从本仓库独立重跑出同样的数字；
- 因此标记为 `PARTIAL`，不标记为 `PASS`。

### README 关键指标的来源状态

`README.md` 的「关键指标」一节数值取自 `evaluation/results/guard_revalidation_original_400/summary.json`（Runtime Guard）与 `evaluation/results/final/summary.json`（公开文本数据集、公开 Trace 场景与性能）。

| 项 | 状态 |
|---|---|
| 可核对 | **是** —— 表中 Recall/Precision/F1 与延迟，均可与上述文件逐项对上 |
| 可重跑 | **否** —— 评测脚本（runner）不在仓库，无法重新生成 |

引用这些数字时应注明对应数据文件，不表述为独立实验结果。

---

## 已知未覆盖项

| 未覆盖项 | 说明 |
|---|---|
| 真实 LLM provider 下的报告质量 | 测试只覆盖 `provider=mock`，`openai` / `openrouter` 依赖外部服务 |
| 中文提示注入的检测效果 | 规则与语义检测对英文注入识别率更高，中文覆盖较弱 |
| 并发与压力场景 | 未做多进程、高并发 Trace 写入的压测 |
| 长时间运行 | 未测内存与本地存储的长期增长 |
| 前端端到端 | 无 Playwright / Cypress 类 UI 自动化，只有构建检查 |
| `enforce` 模式下的业务影响 | 阻断与脱敏对业务链路的影响未量化 |
| 多实例部署 | 未验证多个中间件实例共享同一数据库的行为 |

---

## 复现本文件的步骤

1. 按 [`docs/installation.md`](installation.md) 在干净环境完成安装
2. 设置 `OPENROUTER_API_KEY=dummy`
3. 运行 `pytest tests -v`，应得到 **96 passed**
4. 若 `tests/frontend` 能收集，额外运行验证
5. 对照上表核对每一项结果与本文件是否一致

> 若你的结果与上表不符，请按 [`SUPPORT.md`](../SUPPORT.md) 提交 Issue，并附上本文件「测试环境」一节所列信息。

---

## 证据索引

每条对外主张与其证据的映射。**指不到证据的主张不应出现在文档里。**

| 主张 | 证据位置 | 可否复现 |
|---|---|---|
| 四类检测均可用 | `src/detection/`（`rule_engine.py`、`taint_analysis.py`、`graph_anomaly.py`、`node_embedding.py`）；`tests/policy_packs/`、`tests/scenarios/` | 是 |
| Runtime Guard 四阶段生效 | `sdk/python/graphguard/runtime_guard.py`；`tests/sdk/test_runtime_guard_policy_pack.py`（6 个用例） | 是 |
| `enforce` 模式下按策略阻断或脱敏 | 同上；`config/policy_packs/generic_default/tool_policy.yaml` | 是（单元级） |
| 支持异构智能体接入 | `examples/` 下 7 个接入示例（callback / plugin / langchain / otel / api / runtime guard / basic） | 是 |
| API 与三个控制台可启动 | [`docs/installation.md`](installation.md)；CI `frontend` job 的构建结果；本文件「结果」表 | 是 |
| 依赖可安装、测试通过 | CI 运行记录（GitHub Actions）；本文件「结果」 | 是 |
| 默认脱敏采集与 fail-open | `GRAPHGUARD_CAPTURE_MODE=redacted`、`GRAPHGUARD_FAIL_OPEN=true` 的默认值；`.env.example` | 是 |
| 公开数据集 Recall/F1（BIPIA 等 5 个） | `evaluation/results/final/summary.json` → `public_text_metrics` | 可核对；不可重跑 |
| 正常业务非干扰（enforce 下 120/120 通过，误阻断 0） | `evaluation/results/v3/` 冻结正常集 | 可核对；不可重跑 |
| 单次 Guard 判定与 Trace 分析延迟 | `evaluation/results/final/summary.json` → `performance` | 可核对；不可重跑 |

> 「可核对；不可重跑」表示：数值能与仓库内的评测产物逐项对上，但无法通过本仓库重新生成该产物。

---
