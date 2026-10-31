from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.core.io import write_csv, write_jsonl
from evaluation.core.metrics import binary, multiclass, set_pr
from evaluation.core.schemas import EvaluationResult
from evaluation.v3.weather_trace_factory import build_weather_trace, to_networkx
from src.detection.government_risk_engine import GovernmentRiskEngine

ENGINE_CLASS = "src.detection.government_risk_engine.GovernmentRiskEngine"


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["case_id"]): row for row in rows}


def evaluate_fusion(
    cases: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    policy_pack: str = "government_weather",
) -> EvaluationResult:
    engine = GovernmentRiskEngine(policy_pack=policy_pack)
    gold_by_id = _index(gold)
    predictions: list[dict[str, Any]] = []
    path_hits = path_total = 0
    protected_explained = protected_total = 0
    rule_precision: list[float] = []
    rule_recall: list[float] = []
    for case in cases:
        graph = to_networkx(build_weather_trace(case))
        report = engine.analyze(graph, write_audit=False)
        annotation = gold_by_id[str(case["case_id"])]
        matched = sorted(
            str(rule.get("id"))
            for rule in report.get("matched_rules", [])
            if str(rule.get("id", "")).startswith("WX-")
        )
        precision, recall = set_pr(annotation.get("rule_ids", []), matched)
        if precision is not None:
            rule_precision.append(precision)
        if recall is not None:
            rule_recall.append(recall)

        predicted_path = list(report.get("risk_path") or [])
        predicted_types = [
            str(graph.nodes[node].get("node_type") or graph.nodes[node].get("type"))
            for node in predicted_path
            if node in graph
        ]
        if annotation.get("paths"):
            path_total += 1
            path_hits += int(predicted_types in annotation["paths"])
        spec = case.get("scenario_spec") or {}
        if spec.get("protected_sink"):
            protected_total += 1
            protected_explained += int(
                bool(report.get("explanation")) and bool(matched or report.get("risk_path"))
            )
        predictions.append(
            {
                "case_id": case["case_id"],
                "policy_pack": policy_pack,
                "engine_class": ENGINE_CLASS,
                "predicted_positive": bool(report.get("is_attack")),
                "score": float(report.get("risk_score") or 0.0),
                "risk_type": str(report.get("risk_type") or "none"),
                "matched_rule_ids": matched,
                "risk_path": predicted_path,
                "risk_paths": list(report.get("risk_paths") or []),
                "recommended_action": str(report.get("recommended_action") or "allow"),
                "full_report": report,
            }
        )

    labels = [bool(gold_by_id[row["case_id"]]["positive"]) for row in predictions]
    predicted = [bool(row["predicted_positive"]) for row in predictions]
    gold_types = [
        (gold_by_id[row["case_id"]].get("risk_types") or ["none"])[0]
        for row in predictions
    ]
    predicted_types = [str(row["risk_type"]) for row in predictions]
    metric = {
        "method": "fusion_real_engine",
        "scope": "overall",
        "policy_pack": policy_pack,
        **binary(labels, predicted),
        **multiclass(gold_types, predicted_types),
        "attack_state_accuracy": sum(a == b for a, b in zip(labels, predicted, strict=True))
        / len(labels)
        if labels
        else None,
        "critical_recall": binary(labels, predicted)["recall"],
        "path_coverage": path_hits / path_total if path_total else None,
        "false_critical_rate": binary(labels, predicted)["fpr"],
        "wx_rule_coverage": sum(rule_recall) / len(rule_recall) if rule_recall else None,
        "wx_rule_precision": sum(rule_precision) / len(rule_precision) if rule_precision else None,
        "protected_sink_explanation_rate": protected_explained / protected_total
        if protected_total
        else None,
    }
    return EvaluationResult(metrics=[metric], predictions=predictions)


def evaluate_policy_pack_ablation(
    cases: list[dict[str, Any]], gold: list[dict[str, Any]]
) -> EvaluationResult:
    metrics: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    for pack in ("generic_default", "government_weather"):
        result = evaluate_fusion(cases, gold, policy_pack=pack)
        metrics.extend({**row, "ablation": "policy_pack"} for row in result.metrics)
        predictions.extend(result.predictions)
    return EvaluationResult(metrics=metrics, predictions=predictions)


def evaluate_component_ablation(
    cases: list[dict[str, Any]], gold: list[dict[str, Any]]
) -> EvaluationResult:
    del cases, gold
    rows = [
        {
            "component": component,
            "status": "UNSUPPORTED_CURRENT_IMPLEMENTATION",
            "reason": (
                "GovernmentRiskEngine public API does not expose an independently switchable "
                f"{component[1:]} module."
            ),
        }
        for component in ("-RULE", "-TAINT", "-ANOMALY", "-SEMANTIC")
    ]
    return EvaluationResult(
        metrics=rows,
        predictions=[],
        status="partial",
        limitations=["Component switches were not simulated or monkeypatched."],
    )


def _csv_safe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: json.dumps(value, ensure_ascii=False, sort_keys=True)
            if isinstance(value, (dict, list))
            else value
            for key, value in row.items()
            if key != "full_report"
        }
        for row in rows
    ]


def write_fusion_artifacts(
    output_dir: Path,
    fusion: EvaluationResult,
    component: EvaluationResult,
    policy: EvaluationResult,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "fusion_metrics": output_dir / "weather_fusion_metrics.csv",
        "fusion_predictions": output_dir / "weather_fusion_predictions.csv",
        "fusion_reports": output_dir / "weather_fusion_reports.jsonl",
        "ablation": output_dir / "weather_ablation_metrics.csv",
        "policy_ablation": output_dir / "weather_policy_pack_ablation_metrics.csv",
    }
    write_csv(paths["fusion_metrics"], _csv_safe(fusion.metrics))
    write_csv(paths["fusion_predictions"], _csv_safe(fusion.predictions))
    write_jsonl(
        paths["fusion_reports"],
        [
            {"case_id": row["case_id"], "report": row["full_report"]}
            for row in fusion.predictions
        ],
    )
    write_csv(paths["ablation"], _csv_safe(component.metrics))
    write_csv(paths["policy_ablation"], _csv_safe(policy.metrics))
    return list(paths.values())


def run_fusion_evaluation(
    cases: list[dict[str, Any]], gold: list[dict[str, Any]], output_dir: Path
) -> dict[str, Any]:
    test_cases = [row for row in cases if row["split"] == "test"]
    ids = {row["case_id"] for row in test_cases}
    test_gold = [row for row in gold if row["case_id"] in ids]
    fusion = evaluate_fusion(test_cases, test_gold)
    component = evaluate_component_ablation(test_cases, test_gold)
    policy = evaluate_policy_pack_ablation(test_cases, test_gold)
    artifacts = write_fusion_artifacts(output_dir, fusion, component, policy)
    return {
        "status": "completed",
        "artifacts": [str(path) for path in artifacts],
        "fusion": fusion,
        "component_ablation": component,
        "policy_ablation": policy,
    }
