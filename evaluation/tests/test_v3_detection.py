from __future__ import annotations

from evaluation.v3.dataset_builder import build_weather_dataset
from evaluation.v3.detection import (
    evaluate_anomaly,
    evaluate_rule,
    evaluate_taint,
    select_anomaly_threshold,
)
from evaluation.v3.weather_trace_factory import build_anomaly_pair


def _subset(split: str, count: int = 24) -> tuple[list[dict], list[dict]]:
    bundle = build_weather_dataset()
    cases = [row for row in bundle.controlled_cases if row["split"] == split][:count]
    ids = {row["case_id"] for row in cases}
    gold = [row for row in bundle.controlled_gold if row["case_id"] in ids]
    return cases, gold


def test_rule_evaluation_uses_real_engine_and_emits_locations() -> None:
    cases, gold = _subset("test")
    result = evaluate_rule(cases, gold)

    assert result.status == "completed"
    assert len(result.predictions) == len(cases)
    assert all(row["engine_class"].endswith("GovernmentRiskEngine") for row in result.predictions)
    assert all("matched_rule_ids" in row and "risk_path" in row for row in result.predictions)
    assert {row["scope"] for row in result.metrics} >= {"overall", "WX-01", "WX-02"}


def test_taint_evaluation_handles_negative_paths_without_fabricating_locations() -> None:
    bundle = build_weather_dataset()
    cases = [
        next(row for row in bundle.controlled_cases if row["case_id"] == "WX-T-03-001"),
        next(row for row in bundle.controlled_cases if row["case_id"] == "WN-T-01-001"),
    ]
    ids = {row["case_id"] for row in cases}
    gold = [row for row in bundle.controlled_gold if row["case_id"] in ids]
    result = evaluate_taint(cases, gold)

    assert len(result.predictions) == 2
    normal = next(row for row in result.predictions if row["case_id"].startswith("WN-"))
    assert normal["predicted_paths"] == []


def test_anomaly_threshold_is_selected_only_from_validation_and_frozen_for_test() -> None:
    validation_cases, validation_gold = _subset("validation", 60)
    pairs = [(case["case_id"], *build_anomaly_pair(case)) for case in validation_cases]
    threshold = select_anomaly_threshold(pairs, validation_gold)

    assert 0.0 <= threshold <= 1.0
    test_cases, test_gold = _subset("test", 24)
    test_pairs = [(case["case_id"], *build_anomaly_pair(case)) for case in test_cases]
    result = evaluate_anomaly(test_pairs, test_gold, threshold)
    overall = next(row for row in result.metrics if row["scope"] == "overall")
    assert overall["threshold_selected_on"] == "validation"
    assert overall["frozen_threshold"] == threshold
    assert "auroc" in overall and "auprc" in overall and "fpr" in overall

