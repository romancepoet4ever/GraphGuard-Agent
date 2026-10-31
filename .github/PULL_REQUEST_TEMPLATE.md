<!--
感谢提交 PR。请按下面结构填写，缺项会被退回（见 CONTRIBUTING.md 第五节）。
-->

## 改动说明

（解决了什么问题、为什么这样改。若与某个 Issue 相关，请在下方关联）

## 关联 Issue

Closes #

## 测试证据（必填）

请在下方粘贴**实际运行输出**，不要只写「测试通过」。

```bash
# 后端
# Windows: $env:OPENROUTER_API_KEY='dummy'
export OPENROUTER_API_KEY=dummy
pytest tests -v --ignore=tests/frontend
```

```text
（粘贴输出，应包含 96 passed）
```

```bash
# 前端（若改动了 web-console/）
cd web-console && npm run build
```

```text
（粘贴输出）
```

## 自检清单

- [ ] 测试全部通过，结果已粘贴在上方
- [ ] 未引入新的直接依赖，或已在 `DEPENDENCIES.md` 登记
- [ ] 无密钥、内网地址、真实业务数据
- [ ] 文档已同步更新（`README.md` / `docs/` / `CHANGELOG.md`）
- [ ] 若改动检测逻辑，已补充对应测试用例与预期结果说明

## 影响范围

- [ ] 影响公开 API（请说明是否破坏兼容）
- [ ] 影响检测规则或 `config/policy_packs/`（请说明对判定的影响）
- [ ] 影响依赖或许可证（请说明是否重生成 `sbom.spdx.json`）
- [ ] 仅内部重构，外部行为无变化

## 备注

（ reviewer 需要额外知道的信息，如已知限制、后续计划）
