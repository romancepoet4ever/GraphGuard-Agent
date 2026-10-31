# GraphGuard-Agent Evaluation V3 正式测试结果

> 历史冻结证据：本文记录 2026-10-12 V3 批次的结果，不是当前回归。

- 最终状态：**PASS**
- 报告有效性：`True`

## 有效性审计

有效性门禁：6/6 通过。

## V3 数据

冻结 validation 60 条、test 240 条；test 中攻击 120 条、正常 120 条。

## GraphGuard Core 回归

当前源码回归状态：PASS。旧 V2 public benchmark 未伪装为当前 V3 重跑。

## 气象图上下文规则

Rule：precision 100.0%，recall 83.3%，F1 90.9%。

## 气象污点路径

Taint：precision 100.0%，recall 50.0%，F1 66.7%。

## 气象结构异常

Anomaly：precision 100.0%，recall 33.3%，F1 50.0%。

## 气象语义检测

真实语义 provider：BLOCKED_EXTERNAL；未使用规则或 mock 冒充语义结果。

## 气象融合

GovernmentRiskEngine：precision 100.0%，recall 83.3%，F1 90.9%。

## government_weather Policy Pack

Policy pack ablation 状态：PASS；独立组件 ablation：UNSUPPORTED_CURRENT_IMPLEMENTATION。

## Runtime Guard 结果驱动评价

原始汇总记录 disabled/observe/enforce 与 20 条 enforce 成功样例，但这 20 条未在 2026-10-30 审计中逐例完成人工安全复核。按总任务书，ASR、prevention、block/sanitize 聚合值不作为当前正式防护率结论；仅保留下文有独立证据的正常业务非干扰结果。

## 气象真实业务链

服务探针 11/11；浏览器模式状态 PASS。

## Deferred / Resume / Cancellation

生命周期用例 2/2 通过，同一 Trace 的 resume/cancellation 由真实服务测试验证。

## Observe 非干扰

业务等价率 100.0%，raw/provenance 等价率 100.0%，tool selection 保持率 100.0%。

## 性能

input_guard p95=0.6758 ms；pre_tool_guard p95=1.1175 ms；post_tool_guard p95=1.5956 ms；output_guard p95=2.1348 ms。受控业务流最大 absolute delta=1.9157 ms；不作真实 E2E overhead 外推。

## 跨应用回归

2026-10-12 冻结评测：graphguard=PASS (93 tests)；evaluation_v3=PASS (66 tests)；weather_v3=PASS (307 tests)；interrogation_contract=PASS (16 tests)。不合并为当前总数。

## 外部依赖状态

Semantic=BLOCKED_EXTERNAL；Qwen=BLOCKED_EXTERNAL。

## 局限性

- The controlled dataset is synthetic and balanced; it does not estimate production prevalence.
- The real semantic provider and production Qwen smoke were unavailable and remain BLOCKED_EXTERNAL.
- The legacy public benchmark runner is absent; historical V2 values are not reused as current V3 results.
- GovernmentRiskEngine does not expose independent module switches, so component ablation is explicitly unsupported.
- Latency rows are controlled local measurements; browser/service startup, network I/O, and deferred waits are excluded.
- Direct SDK enforcement leaves the prompt-injection input alert to the integration layer; Weather E2E verifies that integration blocks it.
