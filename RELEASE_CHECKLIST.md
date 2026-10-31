# 发布检查清单

发版前逐项执行并打勾。任何一项不通过，不得发布。

本清单与 [`GOVERNANCE.md`](GOVERNANCE.md) 第三节的发版流程一致，由 Release Manager 执行。

---

## 0. 前置检查

- [ ] 确认在 `main` 分支，且与远端一致

```bash
git checkout main
git pull --ff-only
git status --porcelain     # 必须为空
```

- [ ] 工作区无未提交改动，无未跟踪的临时文件

```bash
git status --short --untracked-files=all
```

---

## 1. 测试

- [ ] 后端测试全绿（**96 passed**）

```bash
# Windows: $env:OPENROUTER_API_KEY='dummy'
export OPENROUTER_API_KEY=dummy
pytest tests -v --ignore=tests/frontend
```

- [ ] 前端构建通过

```bash
cd web-console && npm ci && npm run build
```

- [ ] 无密钥演示路径可跑通

```bash
python examples/basic_trace_demo.py
python examples/api_trace_demo.py --provider mock
```

---

## 2. 依赖与许可证

- [ ] `requirements.txt` 与实际导入的包一致，无失效项

```bash
python -c "import importlib.metadata as m; print(len(m.distributions()))"
```

- [ ] `DEPENDENCIES.md` 的直接依赖数量与实际一致（服务端 24 / 前端 9）
- [ ] `THIRD_PARTY_NOTICES.md` 条目数与 `licenses/` 文件数一致
- [ ] `licenses/` 中每个文件都被 `THIRD_PARTY_NOTICES.md` 引用，无孤儿文件
- [ ] 新增的依赖已补进上述三份文件

---

## 3. SBOM

- [ ] 重新生成 `sbom.spdx.json`（依赖有变动时必须重新生成）

```bash
syft <requirements 导出文件> -o spdx-json=sbom.spdx.json
```

- [ ] 组件数量与 `DEPENDENCIES.md` 对得上
- [ ] 无 `NOASSERTION` 许可证字段
- [ ] 生成时间与工具信息已写入

---

## 4. 文档与版本号

- [ ] `CHANGELOG.md` 已更新，版本号与本次 tag 一致
- [ ] 以下位置的版本号一致，均为本次发布版本：

| 位置 | 当前值 |
|---|---|
| `README.md` 徽章 | v0.1.0 |
| `CHANGELOG.md` 最新条目 | 0.1.0 |
| `docs/COMPATIBILITY.md` 首行 | v0.1.0 |
| `web-console/package.json` version | v0.1.0 |

- [ ] `docs/testing.md` 的「测试环境」已更新为本次提交 hash

---

## 5. 敏感内容检查（**最重要**）

- [ ] 提交内容中不含运行数据

```bash
git ls-files data/ | grep -v '^data/demo_traces/' | grep -v '^data/uploaded_traces/uploaded_example_'
```

预期：**无输出**。除 `data/demo_traces/` 的演示样本外，`data/` 下不应有任何被跟踪的文件。

- [ ] 无 `.env`、无密钥文件被跟踪

```bash
git ls-files | grep -E '(^|/)\.env$|\.pem$|\.key$' 
```

预期：**无输出**。

- [ ] 无硬编码密钥、内网地址、真实个人信息

```bash
git grep -nE '(sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH) PRIVATE KEY)' -- ':!docs'
```

预期：**无输出**（示例中的假密钥需带明显的 `demo` / `example` 标记）。

- [ ] 无数据库文件、日志文件被跟踪

```bash
git ls-files | grep -E '\.(sqlite|sqlite3|db|log)$'
```

预期：**无输出**。

---

## 6. 打 tag 与发布

- [ ] 固定版本号与 commit

```bash
git rev-parse HEAD
```

- [ ] 计算关键文件的 hash 并记录在发布说明中

```bash
sha256sum LICENSE.txt sbom.spdx.json
```

- [ ] 创建附注 tag

```bash
git tag -a v0.1.0 -m "GraphGuard-Agent v0.1.0"
```

- [ ] 推送 tag

```bash
git push origin v0.1.0
```

- [ ] 在 GitHub 创建 Release，正文取自 `CHANGELOG.md` 对应版本条目

---

## 7. 发布后

- [ ] GitHub Release 页面可见，tag 指向正确的提交
- [ ] `CHANGELOG.md` 新增 `## [Unreleased]` 段（若已发布则滚动）
- [ ] `docs/SUPPORT` 相关版本表已更新（`SUPPORT.md` 第二节）
- [ ] 在仓库公告主要变更与升级注意事项

---

## 附：常见卡点

| 现象 | 原因 | 处理 |
|---|---|---|
| 部分用例失败 | 未设 `OPENROUTER_API_KEY` | 设成 `dummy` 后重跑 |
| `pytest: command not found` | 依赖未安装 | `pip install -r requirements.txt` |
| `npm ci` 失败 | `package-lock.json` 与 `package.json` 不同步 | `npm install` 后提交 lock 文件 |
| SBOM 组件数对不上 | 依赖已变但 SBOM 未重生成 | 重新生成并核对 |
