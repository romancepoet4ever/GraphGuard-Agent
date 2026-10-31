# GraphGuard-Agent Evaluation V3 测试结论

> 本文是 2026-10-12 冻结 V3 的历史结论。

正式状态：**PASS**。以下结论只在标明的证据边界内成立。

## 证据范围

- controlled dataset: 240 frozen synthetic Weather test cases (120 attack, 120 normal)
- real cross-repo business path: Weather service contracts and Playwright browser modes
- public benchmark: blocked current rerun; historical V2 values not promoted
- external provider smoke: semantic provider and production Qwen BLOCKED_EXTERNAL

## 十个必须回答的问题

1. V3 是否通过有效性审计？ 是；门禁结果决定报告是否可用。
2. `government_weather` 六类风险检测表现如何？在 controlled dataset 上融合 recall 为 83.3%；逐类命中为 knowledge_poisoning 20/20, missing_provenance 20/20, prompt_injection 20/20, report_pollution 20/20, sensitive_data_leakage 20/20, tool_overreach 0/20，不能概括为全类别无遗漏。
3. 图规则、污点、异常、语义四种方法各自表现如何？Rule/Taint/Anomaly F1 分别为 90.9% / 66.7% / 50.0%；Semantic 为 BLOCKED_EXTERNAL。
4. GovernmentRiskEngine 在 Weather Trace 上的融合表现如何？precision 100.0%、recall 83.3%、F1 90.9%，且无正常样本误报。
5. enforce 相比 disabled/observe 的 ASR 是否可作为正式防护率？本轮审计结论是否。原始汇总留下 20 条 enforce 成功样例，但未做逐例人工安全审计，故 ASR/防护率聚合值从当前正式结论中排除。
6. 正常业务保持率和 false block 是多少？enforce normal utility 100.0%，false block 0.0%，false sanitize 0.0%。
7. Observe 是否对气象业务产生可见行为干扰？受控正常集业务等价率 100.0%，真实浏览器 observe 模式也通过；范围外生产流量未评估。
8. Deferred/Resume/Cancellation 是否保持正确 Trace 生命周期？2/2 个真实服务生命周期合同通过。
9. Runtime Guard 和业务链实际增加多少延迟？本地四阶段 p95 见正式结果，受控业务流最大 absolute delta 为 1.9157 ms；没有把该值冒充 real cross-repo business path 的端到端开销。
10. 当前还有哪些不能外推的局限？受控集是平衡合成集，真实 semantic/Qwen 与 public benchmark 当前重跑受阻，独立组件 ablation 不受公共 API 支持，性能不含网络和 deferred 等待。

## 结论

GraphGuard 在第二个架构不同的气象 Agent 应用中复用了同一 SecurityTrace、Security Graph、Policy Pack 与 Runtime Guard 内核；当前证据支持可解释检测、Observe 在受控正常集上非干扰和跨应用契约兼容性。由于 20 条成功样例未人工审计，不再将汇总攻击防护收益列为本轮正式结论；工具越权 0/20、外部 Provider 阻塞和非生产性能方式仍保留。
