# 安装与部署

本文档描述如何在**一台干净的机器**上从零跑起 GraphGuard-Agent。按顺序执行即可，不需要任何外部 API 密钥。

---

## 一、前置条件

| 项 | 要求 | 说明 |
|---|---|---|
| **Python** | **3.12.7**（开发与验证版本） | 低于 3.11 不可用 |
| **Node.js** | **20 或以上**（开发与验证使用 **25.2.1**） | 仅 `web-console/` 需要 |
| npm | 随 Node 安装（验证使用 11.6.2） | 同上 |
| 内存 | 8 GB 以上 | 启用 ML 检测时建议 16 GB |
| 磁盘 | 3 GB 以上 | 含 `torch` 时约 2.5 GB |
| GPU | 可选 | 不装 GPU 也可完整运行，ML 模块自动使用 CPU |

> 未安装 Node 也不影响中间件本体与 Streamlit 控制台的使用；只有 React 控制台需要。

---

## 二、从零开始的安装

```bash
# 1. 获取代码
git clone https://github.com/romancepoet4ever/GraphGuard-Agent.git
cd GraphGuard-Agent

# 2. 创建并激活虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 可选：跳过 ML 依赖（体积小、启动快）

`torch` 与 `transformers` 仅用于节点语义嵌入与 GNN 风险传播，缺失时相关模块会自动降级，其余检测与防护不受影响：

```bash
# 从 requirements 中排除两个 ML 包后安装
grep -v -E '^(torch|transformers)' requirements.txt > requirements-lite.txt
pip install -r requirements-lite.txt
```

### 配置环境变量（可选）

不配置也能运行。需要自定义端口、策略或模型 provider 时：

```bash
# Windows:      copy .env.example .env
cp .env.example .env
```

可用变量见 `.env.example`；面向业务应用接入的最小集合见 `env.live.example`。

### 数据目录

SQLite 数据库在首次启动时**自动创建**于 `data/trace_store/`，无需手动初始化。若目录不存在，程序会自动创建。

---

## 三、启动

中间件提供三套可访问的界面，职责不同：

| 界面 | 地址 | 定位 |
|---|---|---|
| **FastAPI 后端 API** | `http://127.0.0.1:8001` | **主路径**，所有能力都由它提供 |
| **React 控制台（web-console）** | `http://127.0.0.1:5174` | **主控制台**，推荐的图形界面 |
| Streamlit 控制台（frontend） | `http://127.0.0.1:8501` | legacy fallback，功能等价但已停止演进 |

### 3.1 启动 API（必须）

```bash
# 方式一：项目自带脚本
python -m scripts.run_server

# 方式二：直接用 uvicorn（等价）
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

验证：

```bash
curl http://127.0.0.1:8001/health
# {"status":"healthy","service":"AgentGraph Sentinel", ...}
```

接口文档：`http://127.0.0.1:8001/docs`

### 3.2 启动 React 控制台（推荐）

```bash
cd web-console
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

深链接：

```text
http://127.0.0.1:5174/traces/{trace_id}
http://127.0.0.1:5174/?trace_id={trace_id}
```

### 3.3 启动 Streamlit 控制台（可选 fallback）

```bash
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

---

## 四、无密钥的最小演示路径

以下命令**不需要任何 API 密钥**，可直接验证核心能力：

```bash
# 1) 离线检测示例：生成 trace、跑完整检测链、输出风险报告
python examples/basic_trace_demo.py

# 2) OpenTelemetry Span 适配示例
python examples/otel_span_demo.py

# 3) 运行时防护示例：输入 / 工具调用 / 工具结果 / 输出 四阶段
python examples/runtime_guard_demo.py
```

以上三个示例均已在干净环境验证可运行，产物落在 `data/uploaded_traces/`。

### 通过 API 跑一次完整分析（provider=mock）

先启动 API（见 3.1），然后：

```bash
python examples/api_trace_demo.py --provider mock
```

它会提交一份内置 trace，调用 `POST /api/v1/analyze`，并打印风险评分、命中规则与报告路径。`provider=mock` 走确定性的本地生成逻辑，不访问外部模型。

### 直接调用 HTTP 接口

```python
import json, requests

trace = json.load(open("data/demo_traces/prompt_injection.json", encoding="utf-8"))
resp = requests.post(
    "http://127.0.0.1:8001/api/v1/analyze",
    json={"trace": trace, "model": {"provider": "mock"}},
    timeout=120,
)
data = resp.json()
print(resp.status_code, data["provider"], data["trace_id"])
print(data["report"])
```

> `POST /api/v1/analyze` 必须提供 `trace` 或 `trace_id`，否则返回 400；`trace` 可取 `data/demo_traces/` 下的任意样本。

---

## 五、常见故障与恢复

### 端口被占用

```
[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8001)
```

查占用并处理：

```powershell
# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

```bash
# macOS / Linux
lsof -i :8001
kill -9 <PID>
```

也可改端口：`API_PORT=8002`，或启动时加 `--port 8002`。

### `import streamlit` 失败（protobuf 版本不符）

```
ImportError: cannot import name 'builder' from 'google.protobuf.internal'
```

原因：`protobuf < 3.20`。Streamlit 要求 `protobuf >= 3.20`。

```bash
pip install "protobuf>=4.25,<8"
```

> 该问题只影响 Streamlit 控制台，不影响 API 与 React 控制台。

### 依赖版本冲突（`pip install` 报错）

优先在**干净虚拟环境**中重装，避免与系统 Python 的包混用：

```bash
python -m venv venv2
venv2\Scripts\activate     # Windows
pip install -r requirements.txt
```

若只做检测与 API 开发，可跳过 ML 依赖（见第二节）。

### 外部模型服务不可用

`openai` / `openrouter` 依赖外部服务，可能因网络或配额失败。降级方式：

1. 报告生成改用 `provider=mock`，离线可用；
2. 检测逻辑本身不依赖外部模型（规则、污点、图异动、嵌入都在本地执行）。

### Windows 控制台输出乱码或 `UnicodeEncodeError`

`scripts/` 下的脚本已把 stdout 切到 UTF-8。若仍遇到，设置：

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

### `npm install` 权限错误

不要用 `npm install -g`。若全局缓存不可写，指定缓存目录：

```powershell
$env:npm_config_cache = "$env:TEMP\npm-cache"
npm install
```

---

## 六、验证安装是否成功

```bash
# 单元测试（前端测试目录需要 Streamlit 兼容的 protobuf，默认跳过）
# 注意：必须设置 OPENROUTER_API_KEY（任意非空值即可，不需要真实密钥），
#       否则 detection 路由会被禁用，导致 3 个用例失败。
export OPENROUTER_API_KEY=dummy     # Windows PowerShell: $env:OPENROUTER_API_KEY='dummy'

pytest tests -v --ignore=tests/frontend
```

预期结果：**96 passed**（已设置上述变量）。

```bash
# 健康检查
curl http://127.0.0.1:8001/health
```

关于路由状态：

- **未配置 `OPENROUTER_API_KEY`**：`traces` / `live` / `visualization` 为 `enabled`，`detection` 为 `disabled` —— 这是**正常状态**，安装是完整的。
- **配置任意密钥后**：四个路由全部 `enabled`。

`detection` 属旁路检测路由，被禁用不影响 `/api/v1/*` 主链路。
