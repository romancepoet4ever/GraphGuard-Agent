# 治理与维护

本文件说明 GraphGuard-Agent 的维护者构成、权限边界、决策方式与变更流程。

---

## 一、维护者与职责

| 角色 | 人员 | GitHub | 职责 |
|---|---|---|---|
| **Maintainer（维护者）** | 黄俊杰 | `@Qtmenxia` | 决定项目方向与代码准入；合并 Pull Request；争议无法达成一致时作最终决定 |
| **Reviewer（审查者）** | 黄俊杰 | `@Qtmenxia` | 合并前的代码审查：逻辑、安全、测试与文档同步性；对 PR 给出批准或打回 |
| **Reviewer（审查者）** | 裴志轩 | `@xuan3689` | 同上 |
| **Release Manager（发版负责人）** | 白宸旺 | `@romancepoet4ever` | 版本发布：更新 CHANGELOG、打 tag、发布 Release、执行发布前检查清单 |
| **Security Contact（安全联系人）** | 白宸旺 | `@romancepoet4ever` | 接收并处理漏洞报告；决定修复优先级与披露时机 |

各路径的审查负责人见 [`.github/CODEOWNERS`](.github/CODEOWNERS)。

联系方式：

- 安全报告：**2968091737@qq.com**（渠道与时限详见 [`SECURITY.md`](SECURITY.md)）
- 其他事务：通过 GitHub Issue / Pull Request

---

## 二、审查与合并规则

- 所有改动必须经 Pull Request 提交；`main` 分支受保护，**禁止直接推送**。
- 每个 PR 至少需要 **1 次审查批准**，且批准人**不得是该 PR 的作者**。
- 本项目有两位 Reviewer（黄俊杰、裴志轩），可互相审查：

| PR 作者 | 审查人 | 合并人 |
|---|---|---|
| 裴志轩 | 黄俊杰 | 黄俊杰 |
| 黄俊杰 | 裴志轩 | 黄俊杰（凭裴志轩批准后合并） |
| 白宸旺 | 黄俊杰或裴志轩 | 黄俊杰 |
| 外部贡献者 | 黄俊杰或裴志轩 | 黄俊杰 |

- 合并权归 Maintainer 黄俊杰。合并动作以"已有非作者批准"为前提，合并本身不构成审查。
- 审查意见必须在 PR 中留痕（GitHub review 记录），不接受口头或私下批准。

---

## 三、发版流程

由 Release Manager 白宸旺执行：

1. 确认发布分支测试全绿：`pytest tests --ignore=tests/frontend` → **96 passed**
2. 更新 `CHANGELOG.md`，写明版本号与变更摘要
3. 核对 `DEPENDENCIES.md`、`THIRD_PARTY_NOTICES.md`、`sbom.spdx.json` 与当前依赖是否一致
4. 按 `RELEASE_CHECKLIST.md` 逐项打勾
5. 按语义化版本打 tag（如 `v0.1.0`）并发布 GitHub Release
6. 发布后在本仓库公告主要变更与升级注意事项

---

## 四、安全响应

由 Security Contact 白宸旺负责，时限与 [`SECURITY.md`](SECURITY.md) 保持一致：

| 阶段 | 目标 |
|---|---|
| 确认收到 | 3 个工作日内 |
| 初步评估 | 7 个工作日内 |
| 严重漏洞修复发布 | 14 天内 |

安全修复可跳过常规发版节奏，优先发布补丁版本。

---

## 五、权限授予与撤销

### 授予

新增维护者需同时满足：

1. 有持续的实质性贡献（代码、文档或安全响应），且至少 **3 个已合并的 PR**；
2. 现有维护者一致同意；
3. 在本文件中登记，并写明具体职责范围。

### 撤销

出现以下任一情形，由 Maintainer 发起撤销并记录理由：

- 连续 **6 个月**无实质性参与；
- 严重违反 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)；
- 泄露未公开的漏洞细节或使用者数据；
- 主动申请退出。

撤销决定需以 Issue 或 PR 形式留痕，不接受私下通知。

---

## 六、决策与争议处理

- **日常技术决策**：在对应 Issue / PR 中讨论，由 Maintainer 汇总结论。
- **无法达成一致**：由 Maintainer 黄俊杰作最终决定，并在 Issue 中记录决定与理由。
- **重大变更**（公开 API 破坏性变更、许可证变更、治理结构调整）：需三名维护者一致同意，并在仓库中留档。
- **涉及行为准则的争议**：按 `CODE_OF_CONDUCT.md` 处理。

---

## 七、角色代理

三人团队中若某角色暂时缺位（如 Release Manager 不可用），可由 Maintainer 临时代理，但需在发版记录中注明代理关系与时间范围。

> 本文件按实际人员编写，不虚构额外治理层级。人员或职责变更须通过 PR 修改本文件。
