---
name: 缺陷报告
about: 报告可复现的功能异常、崩溃或错误结果
title: "[Bug] "
labels: bug
assignees: ''
---

<!--
提交前请确认：
1. 已按 docs/installation.md 完成安装；
2. 已用最新 Release 版本复现（见 SUPPORT.md 的支持期限说明）；
3. 这不是安全漏洞 —— 安全问题请勿公开提交，按 SECURITY.md 私下报告。
-->

## 环境信息

- **版本**（tag 或 commit hash）：
- **操作系统**：
- **Python 版本**：
- **安装方式**：`requirements.txt` / 排除 ML 依赖的 `requirements-lite.txt` / 其他
- **运行模式**：`observe` / `enforce`
- **Policy Pack**：`generic_default` / 自建（请说明路径）
- **启动方式**：`python -m scripts.run_server` / `uvicorn` / 其他

## 复现步骤

1.
2.
3.

## 期望行为

（你预期发生什么）

## 实际行为

（实际发生了什么，包括完整的报错信息）

## 相关 Trace ID

```text
trace_xxxxxxxxxxxx
```

> 若能从 `/api/v1/traces` 或控制台拿到 trace_id，请附上；这决定了能否定位到具体执行链路。

## 日志片段

```text

```

> ⚠️ 提交前请先脱敏：不要粘贴真实业务数据、内部地址、API 密钥或个人信息。系统中默认以 `redacted` 档位采集，但你手动复制的日志可能包含原文。

## 补充信息

（是否尝试过修改配置、是否只在特定输入下出现、是否与某个工具调用相关等）
