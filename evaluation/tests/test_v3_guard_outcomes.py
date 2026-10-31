from __future__ import annotations

from evaluation.v3.dataset_builder import SYNTHETIC_SECRET, build_weather_dataset
from evaluation.v3.guard import WeatherGuardExecutor, evaluate_guard


def _guard_case(category: str, *, positive: bool = True) -> tuple[dict, dict]:
    bundle = build_weather_dataset()
    gold_by_id = {row["case_id"]: row for row in bundle.guard_gold}
    case = next(
        row
        for row in bundle.guard_cases
        if gold_by_id[row["case_id"]]["positive"] is positive
        and gold_by_id[row["case_id"]]["category"] == category
    )
    return case, gold_by_id[case["case_id"]]


def test_observe_alert_does_not_claim_prompt_injection_prevention(tmp_path) -> None:
    case, _ = _guard_case("prompt_injection")
    executor = WeatherGuardExecutor(tmp_path)

    disabled = executor.run(case, "disabled")
    observe = executor.run(case, "observe")
    enforce = executor.run(case, "enforce")

    assert disabled.attack_success is True
    assert observe.attack_success is True
    assert enforce.attack_success is True
    assert observe.graphguard_blocked is False
    assert "WX-01" in observe.matched_rule_ids


def test_enforce_blocks_or_sanitizes_actual_business_outcomes(tmp_path) -> None:
    executor = WeatherGuardExecutor(tmp_path)
    tool_case, _ = _guard_case("tainted_valid_high_impact_tool_call")
    secret_case, _ = _guard_case("synthetic_secret_leakage")

    tool_observe = executor.run(tool_case, "observe")
    tool_enforce = executor.run(tool_case, "enforce")
    secret_observe = executor.run(secret_case, "observe")
    secret_enforce = executor.run(secret_case, "enforce")

    assert tool_observe.tool_execution_count == 1
    assert tool_enforce.tool_execution_count == 0
    assert tool_enforce.graphguard_blocked is True
    assert SYNTHETIC_SECRET in secret_observe.protected_sink_content
    assert SYNTHETIC_SECRET not in secret_enforce.protected_sink_content
    assert secret_enforce.graphguard_sanitized is True
    assert secret_enforce.attack_success is False


def test_gateway_denial_is_not_counted_as_graphguard_block(tmp_path) -> None:
    case, _ = _guard_case("tainted_valid_high_impact_tool_call")
    case["scenario_spec"] = {**case["scenario_spec"], "gateway_denied": True}
    outcome = WeatherGuardExecutor(tmp_path).run(case, "enforce")

    assert outcome.gateway_denied is True
    assert outcome.tool_execution_count == 0
    assert outcome.graphguard_blocked is False


def test_guard_aggregate_has_240_cases_and_720_mode_rows(tmp_path) -> None:
    bundle = build_weather_dataset()
    result = evaluate_guard(bundle.guard_cases, bundle.guard_gold, tmp_path)

    assert len({row["case_id"] for row in result.predictions}) == 240
    assert len(result.predictions) == 720
    assert {row["mode"] for row in result.predictions} == {
        "disabled",
        "observe",
        "enforce",
    }
    enforce = next(row for row in result.metrics if row["mode"] == "enforce")
    assert "attack_success_rate" in enforce
    assert "false_block_rate" in enforce
    assert "normal_utility_rate" in enforce

