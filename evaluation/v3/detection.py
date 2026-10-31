from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import networkx as nx

from evaluation.core.io import write_csv
from evaluation.core.metrics import average_precision, binary, roc_auc, set_pr
from evaluation.core.schemas import EvaluationResult
from evaluation.v3.weather_trace_factory import (
    build_anomaly_pair,
    build_weather_trace,
    to_networkx,
)
from src.detection.government_risk_engine import GovernmentRiskEngine
from src.detection.graph_anomaly import GraphAnomalyDetector
from src.detection.taint_analysis import TaintAnalyzer


def _gold_index(gold: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["case_id"]): row for row in gold}


def _metric_rows(
    predictions: list[dict[str, Any]], gold_by_id: dict[str, dict[str, Any]], method: str
) -> list[dict[str, Any]]:
    labels = [bool(gold_by_id[row["case_id"]]["positive"]) for row in predictions]
    predicted = [bool(row["predicted_positive"]) for row in predictions]
    scores = [float(row.get("score") or 0.0) for row in predictions]
    overall = {
        "method": method,
        "scope": "overall",
        **binary(labels, predicted),
        "auroc": roc_auc(labels, scores),
        "auprc": average_precision(labels, scores),
    }
    rows = [overall]
    for rule_id in [f"WX-{index:02d}" for index in range(1, 7)]:
        selected = [
            row
            for row in predictions
            if gold_by_id[row["case_id"]].get("rule_ids") == [rule_id]
            or not gold_by_id[row["case_id"]].get("positive")
        ]
        if not selected:
            continue
        selected_labels = [
            gold_by_id[row["case_id"]].get("rule_ids") == [rule_id] for row in selected
        ]
        selected_predictions = [
            rule_id in row.get("matched_rule_ids", [])
            if method == "rule"
            else bool(row["predicted_positive"])
            for row in selected
        ]
        rows.append(
            {
                "method": method,
                "scope": rule_id,
                **binary(selected_labels, selected_predictions),
                "auroc": None,
                "auprc": None,
            }
        )
    return rows


def evaluate_rule(cases: list[dict[str, Any]], gold: list[dict[str, Any]]) -> EvaluationResult:
    engine = GovernmentRiskEngine(policy_pack="government_weather")
    gold_by_id = _gold_index(gold)
    predictions: list[dict[str, Any]] = []
    rule_precisions: list[float] = []
    rule_recalls: list[float] = []
    path_hits = 0
    path_total = 0
    for case in cases:
        graph = to_networkx(build_weather_trace(case))
        report = engine.analyze(graph, write_audit=False)
        matched_rule_ids = sorted(
            {
                str(rule.get("id"))
                for rule in report.get("matched_rules", [])
                if str(rule.get("id", "")).startswith("WX-")
            }
        )
        annotation = gold_by_id[str(case["case_id"])]
        precision, recall = set_pr(annotation.get("rule_ids", []), matched_rule_ids)
        if precision is not None:
            rule_precisions.append(precision)
        if recall is not None:
            rule_recalls.append(recall)
        expected_paths = annotation.get("paths") or []
        if expected_paths:
            path_total += 1
            predicted_path = report.get("risk_path") or []
            predicted_types = [
                str(graph.nodes[node].get("node_type") or graph.nodes[node].get("type"))
                for node in predicted_path
                if node in graph
            ]
            if any(predicted_types == expected for expected in expected_paths):
                path_hits += 1
        predictions.append(
            {
                "case_id": case["case_id"],
                "method": "rule",
                "engine_class": (
                    "src.detection.government_risk_engine.GovernmentRiskEngine"
                ),
                "predicted_positive": bool(report.get("is_attack")),
                "score": float(report.get("risk_score") or 0.0),
                "risk_type": str(report.get("risk_type") or "none"),
                "matched_rule_ids": matched_rule_ids,
                "risk_path": list(report.get("risk_path") or []),
                "risk_paths": list(report.get("risk_paths") or []),
                "recommended_action": str(report.get("recommended_action") or "allow"),
            }
        )
    metrics = _metric_rows(predictions, gold_by_id, "rule")
    metrics[0].update(
        {
            "rule_id_precision": sum(rule_precisions) / len(rule_precisions)
            if rule_precisions
            else None,
            "rule_id_recall": sum(rule_recalls) / len(rule_recalls) if rule_recalls else None,
            "path_coverage": path_hits / path_total if path_total else None,
        }
    )
    return EvaluationResult(metrics=metrics, predictions=predictions)


def evaluate_taint(cases: list[dict[str, Any]], gold: list[dict[str, Any]]) -> EvaluationResult:
    analyzer = TaintAnalyzer()
    gold_by_id = _gold_index(gold)
    predictions: list[dict[str, Any]] = []
    for case in cases:
        graph = to_networkx(build_weather_trace(case))
        report = analyzer.analyze(graph)
        paths = list(report.get("paths") or [])
        score = float((report.get("summary") or {}).get("max_taint") or 0.0)
        predictions.append(
            {
                "case_id": case["case_id"],
                "method": "taint",
                "predicted_positive": bool(paths),
                "score": score,
                "matched_rule_ids": [],
                "predicted_paths": paths,
                "node_taint_scores": dict(
                    (report.get("summary") or {}).get("node_taint_scores") or {}
                ),
            }
        )
    metrics = _metric_rows(predictions, gold_by_id, "taint")
    return EvaluationResult(
        metrics=metrics,
        predictions=predictions,
        limitations=["TaintAnalyzer does not emit canonical WX rule identifiers."],
    )


def _anomaly_scores(
    pairs: list[tuple[str, nx.DiGraph, nx.DiGraph]],
) -> list[dict[str, Any]]:
    detector = GraphAnomalyDetector(threshold=0.0, max_ged_time_s=0.01)
    rows = []
    for case_id, baseline, observed in pairs:
        report = detector.detect_detailed(baseline, observed)
        rows.append(
            {
                "case_id": case_id,
                "score": float(report.get("score") or 0.0),
                "signals": report.get("signals") or [],
                "diff": report.get("diff") or {},
                "anomaly_variant": observed.graph.get("anomaly_variant", "baseline"),
            }
        )
    return rows


def select_anomaly_threshold(
    validation_pairs: list[tuple[str, nx.DiGraph, nx.DiGraph]],
    gold: list[dict[str, Any]],
) -> float:
    gold_by_id = _gold_index(gold)
    rows = _anomaly_scores(validation_pairs)
    candidates = sorted({0.0, 1.0, *(float(row["score"]) for row in rows)})
    ranked: list[tuple[float, float, float]] = []
    labels = [bool(gold_by_id[row["case_id"]]["positive"]) for row in rows]
    for threshold in candidates:
        metric = binary(labels, [row["score"] >= threshold for row in rows])
        ranked.append((float(metric["f1"] or 0.0), -float(metric["fpr"] or 0.0), threshold))
    return float(max(ranked)[2])


def evaluate_anomaly(
    test_pairs: list[tuple[str, nx.DiGraph, nx.DiGraph]],
    gold: list[dict[str, Any]],
    threshold: float,
) -> EvaluationResult:
    gold_by_id = _gold_index(gold)
    scored = _anomaly_scores(test_pairs)
    predictions = [
        {
            **row,
            "method": "anomaly",
            "predicted_positive": row["score"] >= threshold,
            "matched_rule_ids": [],
            "frozen_threshold": threshold,
        }
        for row in scored
    ]
    metrics = _metric_rows(predictions, gold_by_id, "anomaly")
    metrics[0].update(
        {"threshold_selected_on": "validation", "frozen_threshold": threshold}
    )
    return EvaluationResult(
        metrics=metrics,
        predictions=predictions,
        limitations=["Structural detector signals do not localize canonical WX lifecycle labels."],
    )


def _csv_safe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: json.dumps(value, ensure_ascii=False, sort_keys=True)
            if isinstance(value, (list, dict))
            else value
            for key, value in row.items()
        }
        for row in rows
    ]


def write_detection_artifacts(
    output_dir: Path,
    rule: EvaluationResult,
    taint: EvaluationResult,
    anomaly: EvaluationResult,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, result in (("rule", rule), ("taint_path", taint), ("anomaly", anomaly)):
        metrics_path = output_dir / f"weather_{name}_metrics.csv"
        predictions_path = output_dir / f"weather_{name}_predictions.csv"
        write_csv(metrics_path, _csv_safe(result.metrics))
        write_csv(predictions_path, _csv_safe(result.predictions))
        paths.extend([metrics_path, predictions_path])
    return paths


def run_controlled_detection(
    cases: list[dict[str, Any]], gold: list[dict[str, Any]], output_dir: Path
) -> dict[str, Any]:
    validation = [row for row in cases if row["split"] == "validation"]
    test = [row for row in cases if row["split"] == "test"]
    validation_ids = {row["case_id"] for row in validation}
    test_ids = {row["case_id"] for row in test}
    validation_gold = [row for row in gold if row["case_id"] in validation_ids]
    test_gold = [row for row in gold if row["case_id"] in test_ids]
    threshold = select_anomaly_threshold(
        [(case["case_id"], *build_anomaly_pair(case)) for case in validation],
        validation_gold,
    )
    rule = evaluate_rule(test, test_gold)
    taint = evaluate_taint(test, test_gold)
    anomaly = evaluate_anomaly(
        [(case["case_id"], *build_anomaly_pair(case)) for case in test],
        test_gold,
        threshold,
    )
    paths = write_detection_artifacts(output_dir, rule, taint, anomaly)
    return {
        "status": "completed",
        "anomaly_threshold": threshold,
        "artifacts": [str(path) for path in paths],
        "results": {"rule": rule, "taint": taint, "anomaly": anomaly},
    }
