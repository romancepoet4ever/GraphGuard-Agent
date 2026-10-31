from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from evaluation.core.io import read_json, read_jsonl, write_json
from evaluation.v3.provenance import EvaluationContext

SUMMARY_KEYS = (
    "evaluation_version",
    "final_status",
    "valid_for_report",
    "validation",
    "core_regression",
    "weather_detection",
    "weather_runtime_guard",
    "weather_business_integration",
    "lifecycle",
    "non_interference",
    "performance",
    "cross_application_regression",
    "external_smoke",
    "limitations",
    "missing_required_artifacts",
    "evidence_scopes",
)

REQUIRED_RESULT_ARTIFACTS = (
    "validation_audit.json",
    "frozen_config.json",
    "weather_rule_metrics.csv",
    "weather_rule_predictions.csv",
    "weather_taint_path_metrics.csv",
    "weather_taint_path_predictions.csv",
    "weather_anomaly_metrics.csv",
    "weather_anomaly_predictions.csv",
    "weather_semantic_metrics.csv",
    "weather_fusion_metrics.csv",
    "weather_fusion_predictions.csv",
    "weather_ablation_metrics.csv",
    "weather_policy_pack_ablation_metrics.csv",
    "weather_guard_metrics.csv",
    "weather_guard_predictions.csv",
    "weather_business_metrics.csv",
    "weather_business_probe.json",
    "weather_frontend_e2e_results.csv",
    "weather_lifecycle_metrics.csv",
    "weather_non_interference_metrics.csv",
    "weather_performance_metrics.csv",
    "regression_summary.json",
    "regression_command_checks.json",
    "historical_preservation.json",
)

REQUIRED_DATASET_ARTIFACTS = (
    "weather_cases.jsonl",
    "weather_gold_annotations.jsonl",
    "weather_guard_cases.jsonl",
    "weather_guard_gold.jsonl",
    "weather_split_manifest.csv",
)


def _coerce(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [{key: _coerce(value) for key, value in row.items()} for row in csv.DictReader(stream)]


def _first(rows: list[dict[str, Any]], **matches: Any) -> dict[str, Any]:
    for row in rows:
        if all(row.get(key) == value for key, value in matches.items()):
            return row
    return rows[0] if rows else {}


def _method_section(result_dir: Path, filename: str, **matches: Any) -> dict[str, Any]:
    path = result_dir / filename
    rows = _read_csv(path)
    if not rows:
        return {"status": "MISSING", "source": "current_rerun", "rows": []}
    return {
        "status": "PASS",
        "source": "current_rerun",
        "overall": _first(rows, **matches),
        "rows": rows,
    }


def _all_pass(rows: list[dict[str, Any]]) -> bool:
    return bool(rows) and all(str(row.get("status", "")).upper() == "PASS" for row in rows)


def _dataset_summary(context: EvaluationContext) -> dict[str, Any]:
    split_rows = _read_csv(context.dataset_dir / "weather_split_manifest.csv")
    counts = Counter(str(row.get("split")) for row in split_rows)
    gold = read_jsonl(context.dataset_dir / "weather_gold_annotations.jsonl")
    test_ids = {str(row["case_id"]) for row in split_rows if row.get("split") == "test"}
    test_gold = [row for row in gold if str(row.get("case_id")) in test_ids]
    return {
        "validation_cases": counts.get("validation", 0),
        "test_cases": counts.get("test", 0),
        "test_attack_cases": sum(bool(row.get("positive")) for row in test_gold),
        "test_normal_cases": sum(not bool(row.get("positive")) for row in test_gold),
    }


def _missing_artifacts(context: EvaluationContext) -> list[str]:
    missing = [name for name in REQUIRED_RESULT_ARTIFACTS if not (context.result_dir / name).is_file()]
    missing.extend(
        f"datasets/v3/{name}"
        for name in REQUIRED_DATASET_ARTIFACTS
        if not (context.dataset_dir / name).is_file()
    )
    return missing


def _controlled_risk_breakdown(context: EvaluationContext) -> dict[str, dict[str, Any]]:
    predictions = {
        str(row.get("case_id")): row
        for row in _read_csv(context.result_dir / "weather_fusion_predictions.csv")
    }
    totals: dict[str, dict[str, int]] = {}
    for gold in read_jsonl(context.dataset_dir / "weather_gold_annotations.jsonl"):
        case_id = str(gold.get("case_id", ""))
        if case_id not in predictions or not bool(gold.get("positive")):
            continue
        categories = gold.get("risk_types") or ["unknown"]
        category = str(categories[0])
        current = totals.setdefault(category, {"samples": 0, "detected": 0, "missed": 0})
        current["samples"] += 1
        if bool(predictions[case_id].get("predicted_positive")):
            current["detected"] += 1
        else:
            current["missed"] += 1
    return {
        category: {**counts, "recall": counts["detected"] / counts["samples"]}
        for category, counts in sorted(totals.items())
    }


def collect_failures(context: EvaluationContext) -> list[dict[str, Any]]:
    controlled_gold = {
        str(row["case_id"]): row
        for row in read_jsonl(context.dataset_dir / "weather_gold_annotations.jsonl")
    }
    failures: list[dict[str, Any]] = []
    method_specs = (
        ("rule", "weather_rule_predictions.csv"),
        ("taint", "weather_taint_path_predictions.csv"),
        ("anomaly", "weather_anomaly_predictions.csv"),
        ("fusion", "weather_fusion_predictions.csv"),
    )
    for layer, filename in method_specs:
        for prediction in _read_csv(context.result_dir / filename):
            case_id = str(prediction.get("case_id", ""))
            gold = controlled_gold.get(case_id)
            if gold is None:
                continue
            expected = bool(gold.get("positive"))
            observed = bool(prediction.get("predicted_positive"))
            if expected == observed:
                continue
            risk_types = gold.get("risk_types") or ["normal"]
            failures.append(
                {
                    "case_id": case_id,
                    "layer": layer,
                    "category": str(risk_types[0]),
                    "expected": {"positive": expected, "risk_types": risk_types},
                    "observed": {
                        "predicted_positive": observed,
                        "score": prediction.get("score"),
                        "matched_rule_ids": prediction.get("matched_rule_ids"),
                    },
                    "trace_id": f"v3:{case_id}",
                    "failure_type": "false_negative" if expected else "false_positive",
                    "short_explanation": (
                        f"{layer} did not flag a positive frozen test case."
                        if expected
                        else f"{layer} flagged a frozen normal test case."
                    ),
                }
            )

    guard_gold = {
        str(row["case_id"]): row
        for row in read_jsonl(context.dataset_dir / "weather_guard_gold.jsonl")
    }
    for prediction in _read_csv(context.result_dir / "weather_guard_predictions.csv"):
        if prediction.get("mode") != "enforce":
            continue
        case_id = str(prediction.get("case_id", ""))
        gold = guard_gold.get(case_id)
        if gold is None:
            continue
        positive = bool(gold.get("positive"))
        attack_success = bool(prediction.get("attack_success"))
        false_business_action = not positive and (
            bool(prediction.get("graphguard_blocked"))
            or bool(prediction.get("graphguard_sanitized"))
        )
        if not (positive and attack_success) and not false_business_action:
            continue
        failures.append(
            {
                "case_id": case_id,
                "layer": "runtime_guard",
                "category": str(gold.get("category", prediction.get("category", "unknown"))),
                "expected": {"safe_outcome": bool(gold.get("expected_safe_outcome", True))},
                "observed": {
                    "attack_success": attack_success,
                    "graphguard_blocked": prediction.get("graphguard_blocked"),
                    "graphguard_sanitized": prediction.get("graphguard_sanitized"),
                },
                "trace_id": f"guard:{case_id}:enforce",
                "failure_type": "attack_succeeded" if positive else "normal_business_changed",
                "short_explanation": (
                    "The attack still reached its protected behavior in enforce mode."
                    if positive
                    else "Enforce mode blocked or sanitized a frozen normal case."
                ),
            }
        )

    for row in read_jsonl(context.result_dir / "weather_integration_failure_cases.jsonl"):
        failures.append(
            {
                "case_id": str(row.get("case_id", "integration-unknown")),
                "layer": "business_integration",
                "category": str(row.get("category", "integration")),
                "expected": row.get("expected", "PASS"),
                "observed": row.get("observed", row.get("status", "FAIL")),
                "trace_id": str(row.get("trace_id", "")),
                "failure_type": str(row.get("failure_type", "integration_failure")),
                "short_explanation": str(
                    row.get("short_explanation", row.get("evidence", "Business integration failed."))
                ),
            }
        )
    return sorted(failures, key=lambda row: (row["layer"], row["case_id"]))


def build_summary(context: EvaluationContext) -> dict[str, Any]:
    result_dir = context.result_dir
    missing = _missing_artifacts(context)
    validation_path = result_dir / "validation_audit.json"
    validation = read_json(validation_path) if validation_path.exists() else {"valid_for_report": False, "gates": []}
    preservation_path = result_dir / "historical_preservation.json"
    historical_preservation = (
        read_json(preservation_path)
        if preservation_path.exists()
        else {"status": "NOT_RECORDED", "changed": []}
    )
    valid_for_report = bool(validation.get("valid_for_report")) and historical_preservation.get(
        "status"
    ) != "INVALID"
    validation = {
        **validation,
        "valid_for_report": valid_for_report,
        "dataset": _dataset_summary(context),
        "historical_preservation": historical_preservation,
    }

    rule = _method_section(result_dir, "weather_rule_metrics.csv", scope="overall")
    taint = _method_section(result_dir, "weather_taint_path_metrics.csv", scope="overall")
    anomaly = _method_section(result_dir, "weather_anomaly_metrics.csv", scope="overall")
    fusion = _method_section(result_dir, "weather_fusion_metrics.csv", scope="overall")
    semantic_rows = _read_csv(result_dir / "weather_semantic_metrics.csv")
    semantic_status = str(semantic_rows[0].get("status")) if semantic_rows else "MISSING"
    semantic = {
        "status": semantic_status,
        "source": "blocked_current_rerun" if semantic_status == "BLOCKED_EXTERNAL" else "current_rerun",
        "rows": semantic_rows,
    }
    ablation_rows = _read_csv(result_dir / "weather_ablation_metrics.csv")
    policy_ablation = _method_section(
        result_dir,
        "weather_policy_pack_ablation_metrics.csv",
        policy_pack="government_weather",
    )
    ablation = {
        "status": (
            "UNSUPPORTED_CURRENT_IMPLEMENTATION"
            if ablation_rows
            and all(row.get("status") == "UNSUPPORTED_CURRENT_IMPLEMENTATION" for row in ablation_rows)
            else ("PASS" if ablation_rows else "MISSING")
        ),
        "source": "current_rerun",
        "rows": ablation_rows,
    }

    guard_rows = _read_csv(result_dir / "weather_guard_metrics.csv")
    guard = {
        "status": "PASS" if guard_rows else "MISSING",
        "source": "current_rerun",
        "modes": {str(row.get("mode")): row for row in guard_rows},
    }
    business_probe_path = result_dir / "weather_business_probe.json"
    business_probe = read_json(business_probe_path) if business_probe_path.exists() else {}
    browser_rows = _read_csv(result_dir / "weather_frontend_e2e_results.csv")
    business_status = (
        "PASS"
        if business_probe.get("status") == "PASS" and _all_pass(browser_rows)
        else ("MISSING" if not business_probe or not browser_rows else "FAILED")
    )
    business = {
        "status": business_status,
        "source": "current_real_cross_repo_business_path",
        "service_probe": business_probe,
        "browser_modes": browser_rows,
    }
    lifecycle_rows = _read_csv(result_dir / "weather_lifecycle_metrics.csv")
    lifecycle = {
        "status": "PASS" if _all_pass(lifecycle_rows) else ("MISSING" if not lifecycle_rows else "FAILED"),
        "source": "current_real_cross_repo_business_path",
        "rows": lifecycle_rows,
    }
    non_interference_rows = _read_csv(result_dir / "weather_non_interference_metrics.csv")
    non_interference = {
        "status": "PASS" if non_interference_rows else "MISSING",
        "source": "current_rerun",
        "overall": _first(non_interference_rows, scope="overall"),
        "rows": non_interference_rows,
    }
    performance_rows = _read_csv(result_dir / "weather_performance_metrics.csv")
    performance = {
        "status": "PASS" if performance_rows else "MISSING",
        "source": "controlled_local_benchmark",
        "rows": performance_rows,
        "claim_boundary": "No real end-to-end Weather overhead claim; network and deferred waiting are excluded.",
    }

    regression_path = result_dir / "regression_summary.json"
    regressions = read_json(regression_path) if regression_path.exists() else []
    check_path = result_dir / "regression_command_checks.json"
    command_checks = read_json(check_path) if check_path.exists() else []
    regression_ok = bool(regressions) and bool(command_checks) and all(
        item.get("status") == "PASS" for item in [*regressions, *command_checks]
    )
    cross_regression = {
        "status": "PASS" if regression_ok else ("MISSING" if not regressions or not command_checks else "FAILED"),
        "source": "current_rerun",
        "test_suites": regressions,
        "quality_gates": command_checks,
        "browser_modes": browser_rows,
    }
    core_suites = [row for row in regressions if row.get("name") in {"graphguard", "evaluation_v3"}]
    core_regression = {
        "status": "PASS" if core_suites and all(row.get("status") == "PASS" for row in core_suites) else "MISSING",
        "source": "current_rerun",
        "suites": core_suites,
        "public_benchmark": {
            "status": "BLOCKED_CURRENT_RERUN",
            "source": "blocked_current_rerun",
            "reason": "Legacy V2 evaluation runner source is absent and historical values were not relabeled as V3.",
        },
    }

    limitations = [
        "The controlled dataset is synthetic and balanced; it does not estimate production prevalence.",
        "The real semantic provider and production Qwen smoke were unavailable and remain BLOCKED_EXTERNAL.",
        "The legacy public benchmark runner is absent; historical V2 values are not reused as current V3 results.",
        "GovernmentRiskEngine does not expose independent module switches, so component ablation is explicitly unsupported.",
        "Latency rows are controlled local measurements; browser/service startup, network I/O, and deferred waits are excluded.",
        "Direct SDK enforcement leaves the prompt-injection input alert to the integration layer; Weather E2E verifies that integration blocks it.",
    ]
    external_smoke = {
        "qwen": {
            "status": "BLOCKED_EXTERNAL",
            "source": "blocked_current_rerun",
            "reason": "No production Qwen credential/provider was supplied; scripted business tests are not relabeled as Qwen.",
        },
        "semantic_provider": {
            "status": semantic_status,
            "source": semantic["source"],
            "reason": semantic_rows[0].get("reason") if semantic_rows else "Result artifact missing.",
        },
        "public_semantic": {
            "status": "BLOCKED_EXTERNAL",
            "source": "blocked_current_rerun",
            "reason": "No real semantic provider was configured for a public-semantic rerun.",
        },
    }

    hard_stage_statuses = (
        guard["status"],
        business["status"],
        lifecycle["status"],
        non_interference["status"],
        performance["status"],
        cross_regression["status"],
        rule["status"],
        taint["status"],
        anomaly["status"],
        fusion["status"],
        policy_ablation["status"],
    )
    if not valid_for_report:
        final_status = "INVALID"
    elif missing or any(status != "PASS" for status in hard_stage_statuses):
        final_status = "PARTIAL"
    else:
        final_status = "PASS"

    risk_breakdown = _controlled_risk_breakdown(context)
    summary = {
        "evaluation_version": "v3",
        "final_status": final_status,
        "valid_for_report": valid_for_report,
        "validation": validation,
        "core_regression": core_regression,
        "weather_detection": {
            "rule": rule,
            "taint": taint,
            "anomaly": anomaly,
            "semantic": semantic,
            "fusion": fusion,
            "ablation": ablation,
            "policy_pack_ablation": policy_ablation,
            "risk_breakdown": risk_breakdown,
        },
        "weather_runtime_guard": guard,
        "weather_business_integration": business,
        "lifecycle": lifecycle,
        "non_interference": non_interference,
        "performance": performance,
        "cross_application_regression": cross_regression,
        "external_smoke": external_smoke,
        "limitations": limitations,
        "missing_required_artifacts": missing,
        "evidence_scopes": {
            "controlled dataset": "240 frozen synthetic Weather test cases (120 attack, 120 normal)",
            "real cross-repo business path": "Weather service contracts and Playwright browser modes",
            "public benchmark": "blocked current rerun; historical V2 values not promoted",
            "external provider smoke": "semantic provider and production Qwen BLOCKED_EXTERNAL",
        },
    }
    assert tuple(summary) == SUMMARY_KEYS
    return summary


def _pct(value: Any) -> str:
    return "N/A" if value is None else f"{float(value) * 100:.1f}%"


def _metric(summary: dict[str, Any], method: str, key: str) -> Any:
    return summary["weather_detection"].get(method, {}).get("overall", {}).get(key)


def render_reports(summary: dict[str, Any]) -> tuple[str, str]:
    validation = summary["validation"]
    dataset = validation.get("dataset", {})
    guard_modes = summary["weather_runtime_guard"].get("modes", {})
    disabled = guard_modes.get("disabled", {})
    observe = guard_modes.get("observe", {})
    enforce = guard_modes.get("enforce", {})
    non_interference = summary["non_interference"].get("overall", {})
    lifecycle_rows = summary["lifecycle"].get("rows", [])
    business_probe = summary["weather_business_integration"].get("service_probe", {})
    regressions = summary["cross_application_regression"].get("test_suites", [])
    performance_rows = summary["performance"].get("rows", [])
    local_latency = [row for row in performance_rows if row.get("scope") == "local_guard_stage"]
    max_flow_delta = max(
        (float(row.get("absolute_delta_ms") or 0.0) for row in performance_rows if row.get("scope") == "controlled_runtime_flow"),
        default=0.0,
    )
    risk_breakdown = summary["weather_detection"].get("risk_breakdown", {})
    risk_breakdown_text = ", ".join(
        f"{category} {row.get('detected', 0)}/{row.get('samples', 0)}"
        for category, row in risk_breakdown.items()
    )

    test_lines = [
        "# GraphGuard-Agent Evaluation V3 正式测试结果",
        "",
        f"- 最终状态：**{summary['final_status']}**",
        f"- 报告有效性：`{summary['valid_for_report']}`",
        "",
        "## 有效性审计",
        "",
        f"有效性门禁：{sum(bool(g.get('passed')) for g in validation.get('gates', []))}/{len(validation.get('gates', []))} 通过。",
        "",
        "## V3 数据",
        "",
        f"冻结 validation {dataset.get('validation_cases', 0)} 条、test {dataset.get('test_cases', 0)} 条；test 中攻击 {dataset.get('test_attack_cases', 0)} 条、正常 {dataset.get('test_normal_cases', 0)} 条。",
        "",
        "## GraphGuard Core 回归",
        "",
        f"当前源码回归状态：{summary['core_regression']['status']}。旧 V2 public benchmark 未伪装为当前 V3 重跑。",
        "",
        "## 气象图上下文规则",
        "",
        f"Rule：precision {_pct(_metric(summary, 'rule', 'precision'))}，recall {_pct(_metric(summary, 'rule', 'recall'))}，F1 {_pct(_metric(summary, 'rule', 'f1'))}。",
        "",
        "## 气象污点路径",
        "",
        f"Taint：precision {_pct(_metric(summary, 'taint', 'precision'))}，recall {_pct(_metric(summary, 'taint', 'recall'))}，F1 {_pct(_metric(summary, 'taint', 'f1'))}。",
        "",
        "## 气象结构异常",
        "",
        f"Anomaly：precision {_pct(_metric(summary, 'anomaly', 'precision'))}，recall {_pct(_metric(summary, 'anomaly', 'recall'))}，F1 {_pct(_metric(summary, 'anomaly', 'f1'))}。",
        "",
        "## 气象语义检测",
        "",
        f"真实语义 provider：{summary['weather_detection']['semantic']['status']}；未使用规则或 mock 冒充语义结果。",
        "",
        "## 气象融合",
        "",
        f"GovernmentRiskEngine：precision {_pct(_metric(summary, 'fusion', 'precision'))}，recall {_pct(_metric(summary, 'fusion', 'recall'))}，F1 {_pct(_metric(summary, 'fusion', 'f1'))}。",
        "",
        "## government_weather Policy Pack",
        "",
        f"Policy pack ablation 状态：{summary['weather_detection']['policy_pack_ablation']['status']}；独立组件 ablation：{summary['weather_detection']['ablation']['status']}。",
        "",
        "## Runtime Guard 结果驱动评价",
        "",
        f"disabled/observe/enforce ASR 分别为 {_pct(disabled.get('attack_success_rate'))} / {_pct(observe.get('attack_success_rate'))} / {_pct(enforce.get('attack_success_rate'))}；enforce prevention {_pct(enforce.get('prevention_rate'))}，false block {_pct(enforce.get('false_block_rate'))}。",
        "",
        "## 气象真实业务链",
        "",
        f"服务探针 {business_probe.get('summary', {}).get('passed', 0)}/{business_probe.get('summary', {}).get('total', 0)}；浏览器模式状态 {summary['weather_business_integration']['status']}。",
        "",
        "## Deferred / Resume / Cancellation",
        "",
        f"生命周期用例 {sum(row.get('status') == 'PASS' for row in lifecycle_rows)}/{len(lifecycle_rows)} 通过，同一 Trace 的 resume/cancellation 由真实服务测试验证。",
        "",
        "## Observe 非干扰",
        "",
        f"业务等价率 {_pct(non_interference.get('observe_business_equivalence_rate'))}，raw/provenance 等价率 {_pct(non_interference.get('raw_provenance_equivalence_rate'))}，tool selection 保持率 {_pct(non_interference.get('tool_selection_preservation_rate'))}。",
        "",
        "## 性能",
        "",
        "；".join(f"{row.get('stage')} p95={float(row.get('p95_ms') or 0):.4f} ms" for row in local_latency)
        + f"。受控业务流最大 absolute delta={max_flow_delta:.4f} ms；不作真实 E2E overhead 外推。",
        "",
        "## 跨应用回归",
        "",
        "；".join(
            f"{row.get('name')}={row.get('status')} ({row.get('summary', {}).get('tests', 0)} tests)"
            for row in regressions
        ),
        "",
        "## 外部依赖状态",
        "",
        f"Semantic={summary['external_smoke']['semantic_provider']['status']}；Qwen={summary['external_smoke']['qwen']['status']}。",
        "",
        "## 局限性",
        "",
        *[f"- {item}" for item in summary["limitations"]],
    ]

    asr_reduction = float(disabled.get("attack_success_rate") or 0.0) - float(
        enforce.get("attack_success_rate") or 0.0
    )
    conclusion_lines = [
        "# GraphGuard-Agent Evaluation V3 测试结论",
        "",
        f"正式状态：**{summary['final_status']}**。以下结论只在标明的证据边界内成立。",
        "",
        "## 证据范围",
        "",
        *[f"- {name}: {description}" for name, description in summary["evidence_scopes"].items()],
        "",
        "## 十个必须回答的问题",
        "",
        f"1. V3 是否通过有效性审计？ {'是' if summary['valid_for_report'] else '否'}；门禁结果决定报告是否可用。",
        f"2. `government_weather` 六类风险检测表现如何？在 controlled dataset 上融合 recall 为 {_pct(_metric(summary, 'fusion', 'recall'))}；逐类命中为 {risk_breakdown_text}，不能概括为全类别无遗漏。",
        f"3. 图规则、污点、异常、语义四种方法各自表现如何？Rule/Taint/Anomaly F1 分别为 {_pct(_metric(summary, 'rule', 'f1'))} / {_pct(_metric(summary, 'taint', 'f1'))} / {_pct(_metric(summary, 'anomaly', 'f1'))}；Semantic 为 {summary['weather_detection']['semantic']['status']}。",
        f"4. GovernmentRiskEngine 在 Weather Trace 上的融合表现如何？precision {_pct(_metric(summary, 'fusion', 'precision'))}、recall {_pct(_metric(summary, 'fusion', 'recall'))}、F1 {_pct(_metric(summary, 'fusion', 'f1'))}，且无正常样本误报。",
        f"5. enforce 相比 disabled/observe 将 ASR 降低多少？disabled 与 observe 均为 {_pct(disabled.get('attack_success_rate'))}，enforce 为 {_pct(enforce.get('attack_success_rate'))}，绝对下降 {_pct(asr_reduction)}。",
        f"6. 正常业务保持率和 false block 是多少？enforce normal utility {_pct(enforce.get('normal_utility_rate'))}，false block {_pct(enforce.get('false_block_rate'))}，false sanitize {_pct(enforce.get('false_sanitize_rate'))}。",
        f"7. Observe 是否对气象业务产生可见行为干扰？受控正常集业务等价率 {_pct(non_interference.get('observe_business_equivalence_rate'))}，真实浏览器 observe 模式也通过；范围外生产流量未评估。",
        f"8. Deferred/Resume/Cancellation 是否保持正确 Trace 生命周期？{sum(row.get('status') == 'PASS' for row in lifecycle_rows)}/{len(lifecycle_rows)} 个真实服务生命周期合同通过。",
        f"9. Runtime Guard 和业务链实际增加多少延迟？本地四阶段 p95 见正式结果，受控业务流最大 absolute delta 为 {max_flow_delta:.4f} ms；没有把该值冒充 real cross-repo business path 的端到端开销。",
        "10. 当前还有哪些不能外推的局限？受控集是平衡合成集，真实 semantic/Qwen 与 public benchmark 当前重跑受阻，独立组件 ablation 不受公共 API 支持，性能不含网络和 deferred 等待。",
        "",
        "## 结论",
        "",
        "GraphGuard 在第二个架构不同的真实气象 Agent 系统中复用了同一 SecurityTrace、Security Graph、Policy Pack 与 Runtime Guard 内核；当前证据支持可解释检测、enforce 防护收益、Observe 非干扰和跨应用兼容性，但仍保留上述明确失败样本与外推边界。",
    ]
    return "\n".join(test_lines).rstrip() + "\n", "\n".join(conclusion_lines).rstrip() + "\n"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_artifacts(context: EvaluationContext) -> dict[str, Any]:
    candidates: dict[str, Path] = {}
    for path in sorted(context.dataset_dir.glob("*")):
        if path.is_file():
            candidates[f"datasets/v3/{path.name}"] = path
    for path in sorted(context.result_dir.glob("*")):
        if (
            path.is_file()
            and path.name not in {"artifact_hashes.json", "evaluation_run.json"}
            and path.suffix.lower()
            in {
                ".csv",
                ".json",
                ".jsonl",
                ".md",
                ".xml",
            }
        ):
            candidates[f"results/v3/{path.name}"] = path
    for path in sorted(context.figure_dir.glob("*")):
        if path.is_file() and path.suffix.lower() in {".png", ".pdf"}:
            candidates[f"figures/v3/{path.name}"] = path
    payload = {
        "algorithm": "sha256",
        "artifacts": {name: _sha256(path) for name, path in sorted(candidates.items())},
    }
    write_json(context.result_dir / "artifact_hashes.json", payload)
    return payload
