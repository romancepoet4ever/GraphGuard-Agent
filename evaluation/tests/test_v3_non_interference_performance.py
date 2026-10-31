from __future__ import annotations

from evaluation.v3.non_interference import compare_modes, normalize_business_outcome
from evaluation.v3.performance import benchmark_local_guard, benchmark_weather_turns


def test_business_normalization_ignores_security_noise_but_keeps_business_state() -> None:
    value = {
        "trace_id": "trace-random",
        "created_at": "2026-10-12T00:00:00Z",
        "security_summary": {"risk_score": 0.1},
        "graphguard_trace_id": "gg-random",
        "selected_tool": "weather.observation.query",
        "tool_args": {"station": "哈尔滨"},
        "run_type": "observation_query",
        "raw_result": {"temperature": 20.1},
        "document": {"document_id": "doc-1", "version": 3},
        "provenance": {"dataset_id": "dataset-1"},
        "final_output": "哈尔滨 20.1℃",
    }
    changed_noise = {
        **value,
        "trace_id": "trace-other",
        "created_at": "later",
        "security_summary": {"risk_score": 0.9},
        "graphguard_trace_id": "gg-other",
    }

    assert normalize_business_outcome(value) == normalize_business_outcome(changed_noise)
    changed_business = {**value, "selected_tool": "weather.statistics.query"}
    assert normalize_business_outcome(value) != normalize_business_outcome(changed_business)


def test_compare_modes_reports_observe_equivalence_and_enforce_normal_utility() -> None:
    base = {
        "case_id": "normal-1",
        "positive": False,
        "selected_tool": "weather.observation.query",
        "tool_args": {"station": "哈尔滨"},
        "raw_tool_result_hash": "abc",
        "provenance": {"dataset_id": "fixture"},
        "final_output": "正常输出",
        "graphguard_blocked": False,
        "graphguard_sanitized": False,
    }
    result = compare_modes(
        [{**base, "mode": "disabled", "trace_id": "a"}],
        [{**base, "mode": "observe", "trace_id": "b"}],
        [{**base, "mode": "enforce", "trace_id": "c"}],
    )

    overall = next(row for row in result.metrics if row["scope"] == "overall")
    assert overall["observe_business_equivalence_rate"] == 1.0
    assert overall["raw_provenance_equivalence_rate"] == 1.0
    assert overall["tool_selection_preservation_rate"] == 1.0
    assert overall["enforce_normal_pass_rate"] == 1.0
    assert overall["false_block_rate"] == 0.0
    assert overall["false_sanitize_rate"] == 0.0


def test_local_benchmark_reports_distribution_and_deltas(tmp_path) -> None:
    rows = benchmark_local_guard(iterations=5, trace_dir=tmp_path)

    assert {row["stage"] for row in rows} == {
        "input_guard",
        "pre_tool_guard",
        "post_tool_guard",
        "output_guard",
    }
    assert all(row["n"] == 5 for row in rows)
    assert all(
        key in row
        for row in rows
        for key in ("mean_ms", "p50_ms", "p95_ms", "max_ms", "absolute_delta_ms", "overhead_percent")
    )


def test_weather_benchmark_excludes_deferred_waiting_wall_time(tmp_path) -> None:
    rows = benchmark_weather_turns(warm_runs=2, trace_dir=tmp_path)

    assert len(rows) == 18
    assert all(row["waiting_time_excluded"] is True for row in rows)
    assert all(row["scope"] == "controlled_runtime_flow" for row in rows)
    assert all("absolute_delta_ms" in row and "overhead_percent" in row for row in rows)
