# 当前基线

本文件记录 v0.1.0 的运行环境、测试结果与服务契约。

## 运行环境

- 必需 Python：3.11+（验证版本 3.12.7）
- Node.js：20+（验证版本 25.2.1）
- 依赖声明：见 `requirements.txt`
- 策略包：`generic_default`

## 测试结果

分套件报告，不合计为单一总测试数。

| 套件 | 用例 | 状态 |
|---|---:|---|
| Core（`tests/`） | 96 | PASS |
| Evaluation（`evaluation/tests/`） | 66 | PASS |
| Weather（独立仓库） | 307 | PASS |
| Interrogation（独立仓库） | 16 | PASS |

运行测试需设置 `OPENROUTER_API_KEY`（任意非空值即可）。

## 服务契约

| 服务 | 地址 |
|---|---|
| GraphGuard API | `http://127.0.0.1:8001` |
| Web Console（React） | `http://127.0.0.1:5174` |
| Streamlit 控制台（备用） | `http://127.0.0.1:8501` |

## 数据目录

| 目录 | 用途 |
|---|---|
| `data/trace_store/` | SQLite 数据库，首次启动自动创建 |
| `data/demo_traces/` | 演示用 Trace 样本 |
| `data/security_traces/` | SDK 导出的轨迹文件 |
| `logs/` | 运行日志 |

这些目录只在运行时写入，不随仓库分发。
