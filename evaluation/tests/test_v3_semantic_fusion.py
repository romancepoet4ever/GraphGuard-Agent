from __future__ import annotations

from pathlib import Path

from evaluation.v3.dataset_builder import build_weather_dataset
from evaluation.v3.fusion import (
    evaluate_component_ablation,
    evaluate_fusion,
    evaluate_policy_pack_ablation,
)
from evaluation.v3.semantic import evaluate_semantic


def _test_subset(count: int = 30) -> tuple[list[dict], list[dict]]:
    bundle = build_weather_dataset()
    cases = [row for row in bundle.controlled_cases if row["split"] == "test"][:count]
    ids = {row["case_id"] for row in cases}
    return cases, [row for row in bundle.controlled_gold if row["case_id"] in ids]


def test_semantic_stage_is_honestly_blocked_without_real_provider(tmp_path: Path) -> None:
    result = evaluate_semantic(tmp_path, provider=None)

    assert result["status"] == "BLOCKED_EXTERNAL"
    assert result["executed_samples"] == 0
    assert result["config"]["temperature"] == 0
    assert result["config"]["threshold_selected_on"] == "validation"
    assert result["config"]["fallback_used"] is False


def test_fusion_uses_real_current_engine_and_canonical_missing_provenance() -> None:
    bundle = build_weather_dataset()
    wanted = {"WX-T-01-001", "WX-T-06-001", "WN-T-01-001"}
    cases = [row for row in bundle.controlled_cases if row["case_id"] in wanted]
    gold = [row for row in bundle.controlled_gold if row["case_id"] in wanted]
    result = evaluate_fusion(cases, gold)

    assert all(
        row["engine_class"]
        == "src.detection.government_risk_engine.GovernmentRiskEngine"
        for row in result.predictions
    )
    provenance = next(row for row in result.predictions if row["case_id"] == "WX-T-06-001")
    assert provenance["risk_type"] == "missing_provenance"
    overall = next(row for row in result.metrics if row["scope"] == "overall")
    assert "protected_sink_explanation_rate" in overall
    assert "path_coverage" in overall


def test_ablations_report_supported_policy_comparison_and_unsupported_switches() -> None:
    cases, gold = _test_subset()
    policy = evaluate_policy_pack_ablation(cases, gold)
    component = evaluate_component_ablation(cases, gold)

    assert {row["policy_pack"] for row in policy.metrics} == {
        "generic_default",
        "government_weather",
    }
    assert {row["component"] for row in component.metrics} == {
        "-RULE",
        "-TAINT",
        "-ANOMALY",
        "-SEMANTIC",
    }
    assert all(row["status"] == "UNSUPPORTED_CURRENT_IMPLEMENTATION" for row in component.metrics)

