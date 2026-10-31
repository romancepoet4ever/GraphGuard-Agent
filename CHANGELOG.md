# 更新日志

本文件记录本项目每个发布版本的用户可感知变化。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

后续版本的变更将记录在此。

## [0.1.0] - 2026-10-28

首个公开发布版本。

### 新增

- **四种接入方式**：SDK 埋点、框架 Callback、OpenTelemetry Span 适配、Trace 上传（`POST /api/v1/traces`）
- **四类检测**：规则匹配、污点传播、图异动、节点语义嵌入；四类结果进入统一风险融合引擎
- **运行时防护（Runtime Guard）**：`check_input` / `check_tool_call` / `check_tool_result` / `check_output` 四阶段，支持 `observe`（仅观测）与 `enforce`（按策略阻断或脱敏）
- **Policy Pack 机制**：检测规则与数据分级由 YAML 描述，默认提供 `generic_default`
- **安全执行图**：将 SecurityTrace 构建为有向图，支持风险路径回溯与节点级解释
- **双控制台**：`web-console/` 提供 React/Vite 主控制台，`frontend/` 保留 Streamlit legacy 控制台
- **报告导出**：风险报告支持 Markdown 与 PDF（`GET /api/v1/reports/{trace_id}/export`）
- **合规产物**：`LICENSE.txt`（Apache-2.0）、`DEPENDENCIES.md`、`THIRD_PARTY_NOTICES.md`、`licenses/` 全文、`sbom.spdx.json`（SPDX-2.3）

### 安全

- 默认 `observe` 模式：只观测与告警，不改变业务 Agent 的输入、工具调用与输出
- 默认失败开放（fail-open）：导出或检测链路异常时不阻塞业务，可通过 `GRAPHGUARD_FAIL_OPEN=false` 改为失败关闭
- 默认 `redacted` 采集：敏感字段落盘前脱敏，`full` 模式需手动开启
- 防护热路径为本地确定性判断，不调用外部模型

### 测试

- `pytest tests --ignore=tests/frontend` → **96 passed**
- `tests/frontend` 需与 Streamlit 兼容的 `protobuf`（>= 3.20）

[Unreleased]: https://github.com/romancepoet4ever/GraphGuard-Agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/romancepoet4ever/GraphGuard-Agent/releases/tag/v0.1.0
