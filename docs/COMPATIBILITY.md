# 兼容性矩阵

本仓库只有一个组件（GraphGuard-Agent 中间件本体），因此矩阵的维度是运行环境。

下表只列实际跑过的组合，并注明在哪里跑过。

---

## 一、主组件兼容性

| GraphGuard 版本 | Python | Node.js（`web-console/`） | Policy Pack | 验证方式 |
|---|---|---|---|---|
| **v0.1.0** | **3.12.7** | **25.2.1** | `generic_default` | ✅ 本地实测通过（Windows 11） |
| v0.1.0 | **3.11** | — | `generic_default` | ✅ CI 通过（ubuntu-latest，`pytest tests --ignore=tests/frontend`） |
| v0.1.0 | **3.12** | — | `generic_default` | ✅ CI 通过（ubuntu-latest，同上） |
| v0.1.0 | — | **20** | — | ✅ CI 通过（ubuntu-latest，`npm ci` + `npm run build`） |
| v0.1.0 | — | **25.2.1** | — | ✅ 本地构建通过（Windows 11） |

**说明**：

- **Python**：3.11 在 CI 上跑通；3.12 在 CI 与本地 Windows 11 均跑通。两套环境的用例结果一致。
- **Node.js**：仅用于 `web-console/`；不启动 React 控制台时不需要 Node。
- **Policy Pack**：仓库提供 `generic_default`（`config/policy_packs/generic_default/`）。自建 Policy Pack 需自行验证。

---

## 二、CI 验证矩阵

每次推送 `main` 触发 `.github/workflows/ci.yml`，四个 job 覆盖以下组合：

| Job | 运行环境 | 执行内容 | 结果 |
|---|---|---|---|
| `Python 3.11` | ubuntu-latest + Python 3.11 | `pytest tests -v --ignore=tests/frontend` | ✅ 通过 |
| `Python 3.12` | ubuntu-latest + Python 3.12 | 同上 | ✅ 通过 |
| `Frontend build` | ubuntu-latest + Node 20 | `npm ci` + `npm run build` | ✅ 通过 |
| `Dependency audit` | ubuntu-latest + Python 3.12 | `pip-audit -r requirements.txt` | ✅ 通过 |

---

## 三、组件级兼容

### 3.1 SDK（`sdk/python/graphguard/`）

| 项 | 范围 | 状态 |
|---|---|---|
| 运行模式 | `observe`、`enforce` | 通过测试用例 |
| 上报方式 | 同步 HTTP 导出、异步批量导出、本地 JSON 回退 | 通过测试用例 |
| 依赖 | 无强制第三方依赖（仅标准库 + 项目内模块） | 实测通过 |

### 3.2 存储

| 项 | 范围 | 状态 |
|---|---|---|
| SQLite | Python 内置 `sqlite3`（验证环境 3.45.3） | 实测通过 |
| SQL 特性 | 仅标准 SQL；幂等性通过 `event_id` 唯一约束 + `IntegrityError` 处理实现 | 实测通过 |
| 数据库位置 | `data/trace_store/`（首次启动自动创建） | 实测通过 |

### 3.3 控制台

| 项 | 范围 | 状态 |
|---|---|---|
| React 控制台（`web-console/`） | Node 20（CI）、Node 25.2.1（本地） | `npm ci` + `npm run build` 均通过 |
| Streamlit 控制台（`frontend/`） | 需 `protobuf >= 3.20` | 实测通过（protobuf 7.36.2） |
| 端口约定 | API `8001`、React `5174`、Streamlit `8501` | 实测通过 |

---

## 四、与其它版本的组合规则

- **中间件与 SDK 需同主版本**（v0.1.x 之间可混用）。
- **Policy Pack 与中间件版本绑定**：`generic_default` 的字段结构随主版本演进，升级中间件时需同步更新自建 Policy Pack。
- **不保证向后兼容的部分**：`src/` 内部模块路径、`report` 字典的具体字段名。公开 API（`/api/v1/*`）的破坏性变更会在 `CHANGELOG.md` 中标注。

---

## 五、如何验证你所在的组合

```bash
# 1. 版本自检
python -V
node -v          # 仅在使用 React 控制台时需要

# 2. 依赖与测试
pip install -r requirements.txt
export OPENROUTER_API_KEY=dummy
pytest tests -v --ignore=tests/frontend

# 3. 无密钥演示
python examples/basic_trace_demo.py
```

若结果与 [`docs/testing.md`](testing.md) 不一致，请按 [`SUPPORT.md`](../SUPPORT.md) 提交 Issue，并附上 `python -V`、`node -v`、操作系统与完整报错。

---

## 六、更新说明

本文件在以下情形需要更新：

- 新增 Python 或 Node 版本到 CI 矩阵时（同步更新第二节）；
- 新增 Policy Pack 时；
- 新增验证过的操作系统或运行时组合时；
- 发布新的 GraphGuard 主版本时。
