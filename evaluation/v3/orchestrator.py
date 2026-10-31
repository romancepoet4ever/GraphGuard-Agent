from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from evaluation.core.io import read_json, write_json, write_jsonl
from evaluation.core.schemas import EvaluationResult
from evaluation.v3.business import run_weather_business_evaluation
from evaluation.v3.dataset_builder import (
    DatasetBundle,
    build_weather_dataset,
    write_dataset,
)
from evaluation.v3.detection import run_controlled_detection
from evaluation.v3.figures import KNOWN_STEMS, generate_figures
from evaluation.v3.fusion import run_fusion_evaluation
from evaluation.v3.guard import evaluate_guard, write_guard_artifacts
from evaluation.v3.non_interference import (
    compare_modes,
    write_non_interference_artifacts,
)
from evaluation.v3.performance import (
    benchmark_local_guard,
    benchmark_weather_turns,
    write_performance_artifacts,
)
from evaluation.v3.provenance import (
    EvaluationContext,
    probe_repositories,
    write_provenance_artifacts,
)
from evaluation.v3.regression import (
    build_default_command_checks,
    build_default_specs,
    run_command_check,
    run_regression_suite,
    write_command_check_summary,
    write_regression_summary,
)
from evaluation.v3.reporting import (
    _read_csv,
    build_summary,
    collect_failures,
    hash_artifacts,
    render_reports,
)
from evaluation.v3.semantic import evaluate_semantic
from evaluation.v3.validity import write_validity_audit

StageAction = Callable[[EvaluationContext], dict[str, Any]]
COMPLETE_STATUSES = {"PASS", "BLOCKED_EXTERNAL", "UNSUPPORTED_CURRENT_IMPLEMENTATION"}
DEPENDENCY_BLOCKERS = {"FAILED", "INVALID", "SKIPPED_DEPENDENCY"}
HISTORICAL_ROOTS = (
    "evaluation/datasets/v2",
    "evaluation/datasets/final",
    "evaluation/results/v2",
    "evaluation/results/final",
    "evaluation/figures/v2",
    "evaluation/figures/final",
)


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()


@dataclass(frozen=True)
class StageDefinition:
    name: str
    action: StageAction
    dependencies: tuple[str, ...] = ()
    outputs: tuple[Path, ...] = ()
    refresh_after: tuple[str, ...] = ()


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    started_at: str
    ended_at: str
    artifacts: list[str] = field(default_factory=list)
    error: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> StageResult:
        return cls(
            name=str(value["name"]),
            status=str(value["status"]),
            started_at=str(value["started_at"]),
            ended_at=str(value["ended_at"]),
            artifacts=[str(path) for path in value.get("artifacts", [])],
            error=str(value.get("error", "")),
        )


@dataclass(frozen=True)
class EvaluationRun:
    evaluation_version: str
    status: str
    started_at: str
    ended_at: str
    stages: list[StageResult]
    historical_preservation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EvaluationRun:
        return cls(
            evaluation_version=str(value["evaluation_version"]),
            status=str(value["status"]),
            started_at=str(value["started_at"]),
            ended_at=str(value["ended_at"]),
            stages=[StageResult.from_dict(row) for row in value.get("stages", [])],
            historical_preservation=dict(value.get("historical_preservation") or {}),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_historical(repo_root: Path) -> dict[str, str]:
    repo_root = Path(repo_root).resolve()
    inventory: dict[str, str] = {}
    for relative_root in HISTORICAL_ROOTS:
        root = repo_root / relative_root
        if not root.exists():
            continue
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
            inventory[path.relative_to(repo_root).as_posix()] = _sha256(path)
    return inventory


def _preservation(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    changed = sorted(
        name
        for name in set(before) | set(after)
        if before.get(name) != after.get(name)
    )
    return {
        "status": "PASS" if not changed else "INVALID",
        "files_before": len(before),
        "files_after": len(after),
        "changed": changed,
        "before": before,
        "after": after,
    }


def _artifacts_exist(stage: StageResult) -> bool:
    return all(Path(path).is_file() for path in stage.artifacts)


def _load_previous(path: Path) -> EvaluationRun | None:
    if not path.is_file():
        return None
    try:
        return EvaluationRun.from_dict(read_json(path))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _write_run(path: Path, run: EvaluationRun) -> None:
    write_json(path, run.to_dict())


def _invalidate(outputs: Sequence[Path]) -> None:
    for output in outputs:
        path = Path(output)
        if path.is_file():
            path.unlink()


def _file_hashes(directory: Path) -> dict[str, str]:
    if not directory.exists():
        return {}
    return {
        path.name: _sha256(path)
        for path in sorted(candidate for candidate in directory.iterdir() if candidate.is_file())
    }


def _output_paths(directory: Path, names: Sequence[str]) -> tuple[Path, ...]:
    return tuple(directory / name for name in names)


def _default_stage_definitions(
    context: EvaluationContext,
    historical_before: dict[str, str],
) -> list[StageDefinition]:
    result_dir = context.result_dir
    dataset_dir = context.dataset_dir
    figure_dir = context.figure_dir
    state: dict[str, Any] = {
        "bundle": build_weather_dataset(context.seed),
        "dataset_hashes": _file_hashes(dataset_dir),
    }

    detection_outputs = _output_paths(
        result_dir,
        (
            "weather_rule_metrics.csv",
            "weather_rule_predictions.csv",
            "weather_taint_path_metrics.csv",
            "weather_taint_path_predictions.csv",
            "weather_anomaly_metrics.csv",
            "weather_anomaly_predictions.csv",
        ),
    )
    semantic_outputs = _output_paths(
        result_dir,
        (
            "weather_semantic_model_config.json",
            "weather_semantic_model_cache.json",
            "weather_semantic_metrics.csv",
            "weather_semantic_predictions.csv",
        ),
    )
    fusion_outputs = _output_paths(
        result_dir,
        (
            "weather_fusion_metrics.csv",
            "weather_fusion_predictions.csv",
            "weather_fusion_reports.jsonl",
            "weather_ablation_metrics.csv",
            "weather_policy_pack_ablation_metrics.csv",
        ),
    )
    guard_outputs = _output_paths(
        result_dir,
        (
            "weather_guard_metrics.csv",
            "weather_guard_mode_comparison.csv",
            "weather_guard_case_breakdown.csv",
            "weather_guard_predictions.csv",
        ),
    )
    business_outputs = _output_paths(
        result_dir,
        (
            "weather_business_probe.json",
            "weather_business_probe.log",
            "weather_business_metrics.csv",
            "weather_business_predictions.csv",
            "weather_lifecycle_metrics.csv",
            "weather_frontend_e2e_results.csv",
            "weather_integration_failure_cases.jsonl",
        ),
    )
    non_interference_outputs = _output_paths(
        result_dir,
        ("weather_non_interference_metrics.csv", "weather_non_interference_predictions.csv"),
    )
    regression_outputs = _output_paths(
        result_dir,
        (
            "pytest_graphguard_v3.log",
            "pytest_graphguard_v3.xml",
            "pytest_evaluation_v3.log",
            "pytest_evaluation_v3.xml",
            "pytest_weather_v3.log",
            "pytest_weather_v3.xml",
            "pytest_interrogation_contract_v3.log",
            "pytest_interrogation_contract_v3.xml",
            "weather_ruff_v3.log",
            "weather_frontend_typecheck_v3.log",
            "weather_frontend_build_v3.log",
        ),
    )
    report_outputs = _output_paths(
        result_dir,
        ("failure_cases.jsonl", "summary.json", "TEST_RESULTS_SUMMARY.md", "V3_CONCLUSION.md"),
    ) + tuple(figure_dir / f"{stem}{suffix}" for stem in KNOWN_STEMS for suffix in (".png", ".pdf"))

    def repo_probe(current: EvaluationContext) -> dict[str, Any]:
        path = current.result_dir / "REPO_PROBE.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(probe_repositories(current.repositories).to_markdown(), encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(path)]}

    def dataset_freeze(current: EvaluationContext) -> dict[str, Any]:
        hashes = write_dataset(state["bundle"], current.dataset_dir)
        state["dataset_hashes"] = hashes
        return {
            "status": "PASS",
            "artifacts": [str(current.dataset_dir / name) for name in sorted(hashes)],
        }

    def validity(current: EvaluationContext) -> dict[str, Any]:
        path = write_validity_audit(current)
        payload = read_json(path)
        return {
            "status": "PASS" if payload.get("valid_for_report") else "INVALID",
            "artifacts": [str(path)],
        }

    def detection(current: EvaluationContext) -> dict[str, Any]:
        bundle: DatasetBundle = state["bundle"]
        result = run_controlled_detection(
            bundle.controlled_cases,
            bundle.controlled_gold,
            current.result_dir,
        )
        state["anomaly_threshold"] = result["anomaly_threshold"]
        return {"status": "PASS", "artifacts": result["artifacts"]}

    def frozen_config(current: EvaluationContext) -> dict[str, Any]:
        threshold = state.get("anomaly_threshold")
        if threshold is None:
            row = next(
                (
                    item
                    for item in _read_csv(current.result_dir / "weather_anomaly_metrics.csv")
                    if item.get("scope") == "overall"
                ),
                {},
            )
            threshold = row.get("frozen_threshold")
        configured = replace(
            current,
            dataset_hashes=dict(state.get("dataset_hashes") or _file_hashes(current.dataset_dir)),
            anomaly_threshold=float(threshold) if threshold is not None else None,
        )
        paths = write_provenance_artifacts(configured)
        return {"status": "PASS", "artifacts": [str(paths["frozen_config"])]}

    def semantic(current: EvaluationContext) -> dict[str, Any]:
        return evaluate_semantic(current.result_dir, provider=None)

    def fusion(current: EvaluationContext) -> dict[str, Any]:
        bundle: DatasetBundle = state["bundle"]
        result = run_fusion_evaluation(
            bundle.controlled_cases,
            bundle.controlled_gold,
            current.result_dir,
        )
        return {"status": "PASS", "artifacts": result["artifacts"]}

    def runtime_guard(current: EvaluationContext) -> dict[str, Any]:
        bundle: DatasetBundle = state["bundle"]
        guard_result = evaluate_guard(
            bundle.guard_cases,
            bundle.guard_gold,
            current.repo_root / ".tmp" / "weather-v3-formal-guard-traces",
        )
        state["guard_result"] = guard_result
        paths = write_guard_artifacts(current.result_dir, guard_result)
        return {"status": "PASS", "artifacts": [str(path) for path in paths]}

    def weather_business(current: EvaluationContext) -> dict[str, Any]:
        result = run_weather_business_evaluation(
            current.repositories.weather,
            current.result_dir,
            browser=True,
        )
        return {
            "status": result["status"],
            "artifacts": result.get("artifacts", []),
            "reason": result.get("reason", ""),
        }

    def non_interference(current: EvaluationContext) -> dict[str, Any]:
        guard_result: EvaluationResult | None = state.get("guard_result")
        predictions = (
            guard_result.predictions
            if guard_result is not None
            else _read_csv(current.result_dir / "weather_guard_predictions.csv")
        )
        by_mode = {
            mode: [row for row in predictions if row.get("mode") == mode]
            for mode in ("disabled", "observe", "enforce")
        }
        result = compare_modes(by_mode["disabled"], by_mode["observe"], by_mode["enforce"])
        paths = write_non_interference_artifacts(current.result_dir, result)
        return {"status": "PASS", "artifacts": [str(path) for path in paths]}

    def performance(current: EvaluationContext) -> dict[str, Any]:
        rows = benchmark_local_guard(
            iterations=500,
            trace_dir=current.repo_root / ".tmp" / "weather-v3-formal-performance",
        )
        rows.extend(
            benchmark_weather_turns(
                warm_runs=30,
                trace_dir=current.repo_root / ".tmp" / "weather-v3-formal-turns",
            )
        )
        path = write_performance_artifacts(current.result_dir, rows)
        return {"status": "PASS", "artifacts": [str(path)]}

    def regression(current: EvaluationContext) -> dict[str, Any]:
        summary_path = current.result_dir / "regression_summary.json"
        check_path = current.result_dir / "regression_command_checks.json"
        try:
            suite_results = [
                run_regression_suite(spec)
                for spec in build_default_specs(
                    current.repositories.graphguard,
                    current.repositories.weather,
                    current.repositories.interrogation,
                    current.result_dir,
                )
            ]
            check_results = [
                run_command_check(spec)
                for spec in build_default_command_checks(
                    current.repositories.weather,
                    current.result_dir,
                )
            ]
        except Exception as exc:
            write_json(
                summary_path,
                [
                    {
                        "name": "cross_application_regression",
                        "status": "FAILED",
                        "reason": f"{type(exc).__name__}: {exc}",
                    }
                ],
            )
            write_json(check_path, [])
            raise
        summary_path = write_regression_summary(
            summary_path, suite_results
        )
        check_path = write_command_check_summary(
            check_path, check_results
        )
        passed = all(result.status == "PASS" for result in [*suite_results, *check_results])
        artifacts = [str(summary_path), str(check_path)]
        artifacts.extend(result.xml_path for result in suite_results)
        artifacts.extend(result.log_path for result in suite_results)
        artifacts.extend(result.log_path for result in check_results)
        return {"status": "PASS" if passed else "FAILED", "artifacts": artifacts}

    def historical(current: EvaluationContext) -> dict[str, Any]:
        payload = _preservation(historical_before, inventory_historical(current.repo_root))
        path = current.result_dir / "historical_preservation.json"
        write_json(path, payload)
        return {"status": payload["status"], "artifacts": [str(path)]}

    def reporting(current: EvaluationContext) -> dict[str, Any]:
        summary = build_summary(current)
        summary_path = current.result_dir / "summary.json"
        failure_path = current.result_dir / "failure_cases.jsonl"
        test_path = current.result_dir / "TEST_RESULTS_SUMMARY.md"
        conclusion_path = current.result_dir / "V3_CONCLUSION.md"
        write_json(summary_path, summary)
        write_jsonl(failure_path, collect_failures(current))
        test_report, conclusion = render_reports(summary)
        test_path.write_text(test_report, encoding="utf-8")
        conclusion_path.write_text(conclusion, encoding="utf-8")
        figures = generate_figures(current)
        return {
            "status": summary["final_status"],
            "artifacts": [
                str(summary_path),
                str(failure_path),
                str(test_path),
                str(conclusion_path),
                *[str(path) for path in figures],
            ],
        }

    def hashing(current: EvaluationContext) -> dict[str, Any]:
        hash_artifacts(current)
        path = current.result_dir / "artifact_hashes.json"
        return {"status": "PASS", "artifacts": [str(path)]}

    dataset_names = tuple(_file_hashes(dataset_dir)) or (
        "weather_cases.jsonl",
        "weather_gold_annotations.jsonl",
        "weather_guard_cases.jsonl",
        "weather_guard_gold.jsonl",
        "weather_observable_traces.jsonl",
        "weather_split_manifest.csv",
        "weather_dataset_manifest.csv",
        "weather_deduplication_report.json",
    )
    return [
        StageDefinition("repository_probe", repo_probe, outputs=(result_dir / "REPO_PROBE.md",)),
        StageDefinition(
            "dataset_freeze",
            dataset_freeze,
            outputs=_output_paths(dataset_dir, dataset_names),
        ),
        StageDefinition(
            "validity_audit",
            validity,
            dependencies=("dataset_freeze",),
            outputs=(result_dir / "validation_audit.json",),
        ),
        StageDefinition(
            "controlled_detection",
            detection,
            dependencies=("dataset_freeze",),
            outputs=detection_outputs,
        ),
        StageDefinition(
            "frozen_config",
            frozen_config,
            dependencies=("dataset_freeze", "controlled_detection"),
            outputs=(result_dir / "frozen_config.json",),
        ),
        StageDefinition("semantic", semantic, outputs=semantic_outputs),
        StageDefinition(
            "fusion_and_ablation",
            fusion,
            dependencies=("dataset_freeze",),
            outputs=fusion_outputs,
        ),
        StageDefinition(
            "runtime_guard",
            runtime_guard,
            dependencies=("dataset_freeze",),
            outputs=guard_outputs,
        ),
        StageDefinition("weather_business", weather_business, outputs=business_outputs),
        StageDefinition(
            "non_interference",
            non_interference,
            dependencies=("runtime_guard",),
            outputs=non_interference_outputs,
        ),
        StageDefinition(
            "performance",
            performance,
            dependencies=("dataset_freeze",),
            outputs=(result_dir / "weather_performance_metrics.csv",),
        ),
        StageDefinition("cross_application_regression", regression, outputs=regression_outputs),
        StageDefinition(
            "historical_preservation",
            historical,
            outputs=(result_dir / "historical_preservation.json",),
            refresh_after=(
                "repository_probe",
                "dataset_freeze",
                "validity_audit",
                "controlled_detection",
                "frozen_config",
                "semantic",
                "fusion_and_ablation",
                "runtime_guard",
                "weather_business",
                "non_interference",
                "performance",
                "cross_application_regression",
            ),
        ),
        StageDefinition(
            "reporting_and_figures",
            reporting,
            outputs=report_outputs,
            refresh_after=(
                "repository_probe",
                "dataset_freeze",
                "validity_audit",
                "controlled_detection",
                "frozen_config",
                "semantic",
                "fusion_and_ablation",
                "runtime_guard",
                "weather_business",
                "non_interference",
                "performance",
                "cross_application_regression",
                "historical_preservation",
            ),
        ),
        StageDefinition(
            "artifact_hashes",
            hashing,
            dependencies=("reporting_and_figures",),
            outputs=(result_dir / "artifact_hashes.json",),
        ),
    ]


def _run_status(stages: list[StageResult], summary_path: Path) -> str:
    if any(stage.status == "INVALID" for stage in stages):
        return "INVALID"
    if any(stage.status not in COMPLETE_STATUSES for stage in stages):
        return "PARTIAL"
    if summary_path.is_file():
        try:
            status = str(read_json(summary_path).get("final_status", ""))
            if status in {"PASS", "PARTIAL", "INVALID"}:
                return status
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return "PASS"


def run_v3(
    context: EvaluationContext,
    *,
    stage_definitions: Sequence[StageDefinition] | None = None,
    resume: bool = True,
) -> EvaluationRun:
    context.result_dir.mkdir(parents=True, exist_ok=True)
    context.dataset_dir.mkdir(parents=True, exist_ok=True)
    context.figure_dir.mkdir(parents=True, exist_ok=True)
    state_path = context.result_dir / "evaluation_run.json"
    previous = _load_previous(state_path) if resume else None
    current_historical = inventory_historical(context.repo_root)
    stored_baseline = previous.historical_preservation.get("before") if previous else None
    historical_before = (
        {str(name): str(digest) for name, digest in stored_baseline.items()}
        if isinstance(stored_baseline, dict)
        else current_historical
    )
    historical_changed_at_start = (
        _preservation(historical_before, current_historical)["status"] == "INVALID"
    )
    definitions = list(stage_definitions or _default_stage_definitions(context, historical_before))
    previous_by_name = {stage.name: stage for stage in previous.stages} if previous else {}
    expected_names = [definition.name for definition in definitions]
    if (
        previous is not None
        and previous.status == "PASS"
        and not historical_changed_at_start
        and [stage.name for stage in previous.stages] == expected_names
        and all(
            stage.status in COMPLETE_STATUSES and _artifacts_exist(stage)
            for stage in previous.stages
        )
    ):
        return previous

    started_at = previous.started_at if previous else _now()
    stages: list[StageResult] = []
    status_by_name: dict[str, str] = {}
    executed_names: set[str] = set()
    for definition in definitions:
        cached = previous_by_name.get(definition.name)
        if (
            cached is not None
            and cached.status in COMPLETE_STATUSES
            and _artifacts_exist(cached)
            and all(
                dependency not in executed_names
                for dependency in (*definition.dependencies, *definition.refresh_after)
            )
            and not (
                definition.name == "historical_preservation"
                and historical_changed_at_start
            )
        ):
            stages.append(cached)
            status_by_name[definition.name] = cached.status
            continue
        blocking = [
            dependency
            for dependency in definition.dependencies
            if status_by_name.get(dependency) in DEPENDENCY_BLOCKERS
        ]
        if blocking:
            _invalidate(definition.outputs)
            now = _now()
            stage = StageResult(
                definition.name,
                "SKIPPED_DEPENDENCY",
                now,
                now,
                [],
                f"blocked by: {', '.join(blocking)}",
            )
        else:
            _invalidate(definition.outputs)
            stage_started = _now()
            try:
                payload = definition.action(context)
                stage = StageResult(
                    definition.name,
                    str(payload.get("status", "PASS")),
                    stage_started,
                    _now(),
                    [str(path) for path in payload.get("artifacts", [])],
                    str(payload.get("reason", "")),
                )
            except Exception as exc:  # noqa: BLE001 - stage boundary must isolate failures
                stage = StageResult(
                    definition.name,
                    "FAILED",
                    stage_started,
                    _now(),
                    [],
                    f"{type(exc).__name__}: {exc}",
                )
        stages.append(stage)
        executed_names.add(definition.name)
        status_by_name[definition.name] = stage.status
        interim = EvaluationRun(
            "v3",
            _run_status(stages, context.result_dir / "summary.json"),
            started_at,
            _now(),
            stages,
            _preservation(historical_before, inventory_historical(context.repo_root)),
        )
        _write_run(state_path, interim)

    preservation = _preservation(historical_before, inventory_historical(context.repo_root))
    status = _run_status(stages, context.result_dir / "summary.json")
    if preservation["status"] == "INVALID":
        status = "INVALID"
    run = EvaluationRun("v3", status, started_at, _now(), stages, preservation)
    _write_run(state_path, run)
    return run
