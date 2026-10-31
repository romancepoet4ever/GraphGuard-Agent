from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from evaluation.core.io import write_csv
from evaluation.v3.dataset_builder import build_weather_dataset
from evaluation.v3.guard import (
    GraphGuardClient,
    GraphGuardRuntime,
    WeatherGuardExecutor,
)


def _percentile(samples: list[float], ratio: float) -> float:
    ordered = sorted(samples)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * ratio) - 1))
    return ordered[index]


def _measure(operation: Callable[[], Any], iterations: int) -> dict[str, float | int]:
    for _ in range(min(10, iterations)):
        operation()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        operation()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    return {
        "n": iterations,
        "mean_ms": round(statistics.fmean(samples), 6),
        "p50_ms": round(_percentile(samples, 0.50), 6),
        "p95_ms": round(_percentile(samples, 0.95), 6),
        "max_ms": round(max(samples), 6),
    }


def benchmark_local_guard(iterations: int = 500, trace_dir: Path | None = None) -> list[dict[str, Any]]:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    output = Path(trace_dir or ".tmp/weather-guard-benchmark")
    client = GraphGuardClient(
        project="weather-evaluation-v3",
        scenario="government_weather_agent",
        policy_pack="government_weather",
        output_path=str(output),
        capture_mode="metadata_only",
    )
    client.start_trace(trace_id="weather-v3-local-guard-benchmark")
    runtime = GraphGuardRuntime(client)
    operations: dict[str, Callable[[], Any]] = {
        "input_guard": lambda: runtime.check_input("查询哈尔滨过去一小时气温"),
        "pre_tool_guard": lambda: runtime.check_tool_call(
            "weather.observation.query", {"station": "哈尔滨"}, {"taint": ""}
        ),
        "post_tool_guard": lambda: runtime.check_tool_result(
            "weather.observation.query",
            {"status": "ok", "value": 20.1},
            {"provenance_present": True},
        ),
        "output_guard": lambda: runtime.check_output(
            "哈尔滨当前气温 20.1 摄氏度。", {"provenance_present": True}
        ),
    }
    rows: list[dict[str, Any]] = []
    for stage, operation in operations.items():
        measured = _measure(operation, iterations)
        rows.append(
            {
                "scope": "local_guard_stage",
                "stage": stage,
                **measured,
                "baseline_ms": 0.0,
                "absolute_delta_ms": measured["mean_ms"],
                "overhead_percent": None,
                "overhead_percent_status": "UNDEFINED_ZERO_BASELINE",
                "network_io": False,
                "waiting_time_excluded": True,
            }
        )
    return rows


def benchmark_weather_turns(
    warm_runs: int = 30, trace_dir: Path | None = None
) -> list[dict[str, Any]]:
    if warm_runs < 1:
        raise ValueError("warm_runs must be positive")
    bundle = build_weather_dataset()
    gold_by_id = {row["case_id"]: row for row in bundle.guard_gold}
    normal_cases: dict[str, dict[str, Any]] = {}
    for case in bundle.guard_cases:
        annotation = gold_by_id[case["case_id"]]
        if not annotation["positive"] and annotation["category"] not in normal_cases:
            normal_cases[annotation["category"]] = case
    executor = WeatherGuardExecutor(Path(trace_dir or ".tmp/weather-turn-benchmark"))
    measurements: dict[tuple[str, str], dict[str, float | int]] = {}
    for category, case in sorted(normal_cases.items()):
        for mode in ("disabled", "observe", "enforce"):
            measurements[(category, mode)] = _measure(
                lambda case=case, mode=mode: executor.run(case, mode), warm_runs
            )

    rows: list[dict[str, Any]] = []
    for category in sorted(normal_cases):
        baseline = float(measurements[(category, "disabled")]["mean_ms"])
        for mode in ("disabled", "observe", "enforce"):
            measured = measurements[(category, mode)]
            delta = float(measured["mean_ms"]) - baseline
            rows.append(
                {
                    "scope": "controlled_runtime_flow",
                    "category": category,
                    "mode": mode,
                    **measured,
                    "baseline_ms": baseline,
                    "absolute_delta_ms": round(delta, 6),
                    "overhead_percent": round(delta / baseline * 100, 6)
                    if baseline
                    else None,
                    "waiting_time_excluded": True,
                    "limitation": (
                        "Deterministic local Runtime Guard business flow; browser/service startup "
                        "and deferred waiting time are excluded."
                    ),
                }
            )
    return rows


def write_performance_artifacts(output_dir: Path, rows: list[dict[str, Any]]) -> Path:
    path = output_dir / "weather_performance_metrics.csv"
    write_csv(path, rows)
    return path
