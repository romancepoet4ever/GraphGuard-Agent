# 贡献指南

感谢关注 GraphGuard-Agent。本文说明如何搭建环境、提交改动，以及我们会如何审查。

---

## 一、环境准备

完整步骤见 [`docs/installation.md`](docs/installation.md)。最小步骤：

```bash
git clone https://github.com/romancepoet4ever/GraphGuard-Agent.git
cd GraphGuard-Agent
python -m venv venv
venv\Scripts\activate                      # Windows
pip install -r requirements.txt            # 已含 pytest；只做非 ML 开发时可排除 torch / transformers
```

需要 Python **3.11+**，前端需要 Node.js **20+**。

---

## 二、运行测试

提交前必须在本机跑通以下命令，并把结果粘贴到 PR 描述里。

### 后端

```bash
# 必须先设置该变量（任意非空值即可，不需要真实密钥），否则 detection 路由被禁用，
# 会有 3 个用例失败
export OPENROUTER_API_KEY=dummy            # Windows: $env:OPENROUTER_API_KEY='dummy'

pytest tests -v --ignore=tests/frontend
```

预期：**96 passed**。

`tests/frontend` 需要与 Streamlit 兼容的 `protobuf`（>= 3.20）；你的环境满足时可以一并运行：

```bash
pytest tests -v
```

### 前端

```bash
cd web-console
npm install
npm run build      # tsc -b && vite build，含类型检查
```

> 只跑 Python 测试就提 PR 是不完整的——前端改动必须附 `npm run build` 的输出。

### 单独跑某个模块

```bash
pytest tests/test_basic.py -v
pytest tests -v -k "policy"
```

---

## 三、编码规范

### 通用

- **不要引入真实密钥、内网地址或真实业务数据**。测试数据使用保留域名（`example.com`）与明显的假值。
- 新增或升级依赖时，同步更新 `DEPENDENCIES.md`、`THIRD_PARTY_NOTICES.md` 与 `sbom.spdx.json`。
- 涉及检测逻辑的改动，必须补充对应测试用例，并在 PR 里说明预期结果。

### Python

- 遵循 PEP 8，4 空格缩进，行宽不超过 120。
- 对外函数与公开方法标注类型提示。
- 检测器返回统一结构：`{"is_malicious": bool, "score": float, "details": dict}`。
- 异常处理遵循**失败开放**原则：新增的外部调用必须有超时与降级路径，不得让中间件阻塞业务。
- 不要新增 LLM 调用到运行时防护的热路径（`check_*` 系列必须保持本地、确定性、微秒级）。

### 前端（`web-console/`）

- TypeScript，组件使用函数式写法；不引入新的状态管理库。
- 所有 HTTP 调用集中在 `src/api/`，不在组件里直接拼接 URL。
- 保持 `npm run build` 零报错（含 `tsc` 类型检查）。

### 文档

- 中文文档使用全角标点；代码块标注语言。
- 修改行为时同步更新 `README.md` 与相关 `docs/`。

---

## 四、提交信息格式

采用 Conventional Commits：

```text
<type>(<scope>): <subject>

<body 可选，说明动机与影响>
```

常用 type：

| type | 用途 |
|---|---|
| `feat` | 新能力 |
| `fix` | 缺陷修复 |
| `docs` | 仅文档 |
| `refactor` | 不改变行为的重构 |
| `test` | 测试相关 |
| `chore` | 构建、依赖、杂务 |

示例：

```text
fix(detection): 修正工具越权规则对小写工具名的漏判

原正则只匹配 send_email 等小写形式，导致 SendEmail 被漏过。
补充大小写不敏感匹配，并新增 2 条测试用例。
```

要求：

- subject 不超过 72 字符，动词开头，不加句号；
- 一次提交只做一件事，不要把格式化与功能改动混在一起；
- 涉及破坏性变更时在 footer 写 `BREAKING CHANGE:`。

---

## 五、Pull Request 要求

PR 描述中**必须**包含以下内容，缺项会被退回：

1. **改动目的**：解决什么问题，为什么这样改。
2. **测试证据**：粘贴 `pytest tests -v --ignore=tests/frontend` 的结果；前端改动还需附 `npm run build` 输出。
3. **影响范围**：是否影响公开 API、是否影响既有策略判定、是否需要同步更新文档。
4. **安全检查**：确认未引入密钥、内网地址、真实业务数据。

提交前自检清单：

- [ ] 测试通过，结果已粘贴
- [ ] 未引入新的直接依赖，或已在 `DEPENDENCIES.md` 登记
- [ ] 无密钥、内网地址、真实业务数据
- [ ] 文档已同步更新
- [ ] 若改动检测逻辑，已补充测试用例与预期结果说明

---

## 六、代码归属与合并权限

### 合并权限

本项目由三人维护，分工见 [`GOVERNANCE.md`](GOVERNANCE.md)：

| 角色 | 人员 | 职责 |
|---|---|---|
| Maintainer | 黄俊杰 | 合并权、最终决策 |
| Reviewer | 黄俊杰、裴志轩 | PR 审查（批准人不得是 PR 作者） |
| Release Manager / Security Contact | 白宸旺 | 发版与漏洞响应 |

所有改动经 Pull Request 提交，**禁止直接向 `main` 推送**；作者不得自行批准自己的 PR。

### 贡献者来源声明（DCO）

本项目采用 **DCO（Developer Certificate of Origin）**，不使用 CLA。提交时请签名：

```bash
git commit -s -m "fix(detection): ..."
```

签名会在提交信息末尾追加：

```text
Signed-off-by: Your Name <your@email.com>
```

这表示你确认自己有权提交该改动，并同意以本项目的 Apache-2.0 许可证发布。未签名的 PR 不会被合并。

### 许可证

本项目以 **Apache-2.0** 授权。提交贡献即表示同意你的贡献以同一许可证发布（见 `LICENSE.txt`）。
