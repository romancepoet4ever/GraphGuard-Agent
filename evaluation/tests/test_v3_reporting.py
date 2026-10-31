from __future__ import annotations

import json
import shutil
from pathlib import Path

from evaluation.v3.figures import generate_figures
from evaluation.v3.provenance import EvaluationContext, RepositoryPaths
from evaluation.v3.reporting import (
    build_summary,
    collect_failures,
    hash_artifacts,
    render_reports,
)

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SUMMARY_KEYS = {
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
}


def _context(result_dir: Path, figure_dir: Path, dataset_dir: Path | None = None) -> EvaluationContext:
    return EvaluationContext(
        repo_root=ROOT,
        dataset_dir=dataset_dir or ROOT / "evaluation" / "datasets" / "v3",
        result_dir=result_dir,
        figure_dir=figure_dir,
        repositories=RepositoryPaths(
            graphguard=ROOT,
            weather=ROOT.parent / "MeteorologicalBureau",
            interrogation=ROOT.parent / "interrogation_agent",
        ),
    )


def _copied_context(tmp_path: Path) -> EvaluationContext:
    result_dir = tmp_path / "results"
    shutil.copytree(
        ROOT / "evaluation" / "results" / "v3",
        result_dir,
        ignore=shutil.ignore_patterns(".pytest-*"),
    )
    (result_dir / "regression_summary.json").write_text(
        json.dumps([{"name": "fixture_suite", "status": "PASS"}]),
        encoding="utf-8",
    )
    (result_dir / "regression_command_checks.json").write_text(
        json.dumps([{"name": "fixture_check", "status": "PASS"}]),
        encoding="utf-8",
    )
    return _context(result_dir, tmp_path / "figures")


def test_build_summary_has_exact_v3_sections_and_external_block_does_not_fake_failure(
    tmp_path: Path,
) -> None:
    context = _copied_context(tmp_path)

    summary = build_summary(context)

    assert set(summary) == EXPECTED_SUMMARY_KEYS
    assert summary["evaluation_version"] == "v3"
    assert summary["valid_for_report"] is True
    assert summary["final_status"] == "PASS"
    assert summary["weather_detection"]["semantic"]["status"] == "BLOCKED_EXTERNAL"
    assert len(summary["weather_detection"]["risk_breakdown"]) == 6
    assert summary["weather_detection"]["risk_breakdown"]["tool_overreach"]["missed"] == 20
    assert summary["external_smoke"]["qwen"]["status"] == "BLOCKED_EXTERNAL"
    assert summary["missing_required_artifacts"] == []


def test_missing_required_artifact_is_partial_not_autofilled_pass(tmp_path: Path) -> None:
    context = _copied_context(tmp_path)
    (context.result_dir / "weather_guard_metrics.csv").unlink()

    summary = build_summary(context)

    assert summary["final_status"] == "PARTIAL"
    assert "weather_guard_metrics.csv" in summary["missing_required_artifacts"]
    assert summary["weather_runtime_guard"]["status"] == "MISSING"


def test_failed_validity_gate_makes_summary_invalid(tmp_path: Path) -> None:
    context = _copied_context(tmp_path)
    validation_path = context.result_dir / "validation_audit.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["valid_for_report"] = False
    validation["gates"][0]["passed"] = False
    validation_path.write_text(json.dumps(validation), encoding="utf-8")

    summary = build_summary(context)

    assert summary["final_status"] == "INVALID"
    assert summary["valid_for_report"] is False


def test_historical_preservation_failure_makes_summary_invalid(tmp_path: Path) -> None:
    context = _copied_context(tmp_path)
    (context.result_dir / "historical_preservation.json").write_text(
        json.dumps({"status": "INVALID", "changed": ["evaluation/results/final/summary.json"]}),
        encoding="utf-8",
    )

    summary = build_summary(context)

    assert summary["final_status"] == "INVALID"
    assert summary["validation"]["historical_preservation"]["status"] == "INVALID"


def test_missing_historical_preservation_evidence_makes_summary_partial(
    tmp_path: Path,
) -> None:
    context = _copied_context(tmp_path)
    (context.result_dir / "historical_preservation.json").unlink()

    summary = build_summary(context)

    assert summary["final_status"] == "PARTIAL"
    assert "historical_preservation.json" in summary["missing_required_artifacts"]


def test_failure_cases_join_predictions_to_gold_and_keep_required_evidence(tmp_path: Path) -> None:
    context = _context(
        ROOT / "evaluation" / "results" / "v3",
        tmp_path / "figures",
    )

    failures = collect_failures(context)

    assert failures
    required = {
        "case_id",
        "layer",
        "category",
        "expected",
        "observed",
        "trace_id",
        "failure_type",
        "short_explanation",
    }
    assert all(required <= set(row) for row in failures)
    assert any(row["layer"] == "fusion" and row["failure_type"] == "false_negative" for row in failures)
    assert any(row["layer"] == "runtime_guard" and row["failure_type"] == "attack_succeeded" for row in failures)


def test_reports_answer_all_questions_and_keep_scope_boundaries(tmp_path: Path) -> None:
    summary = build_summary(_copied_context(tmp_path))

    test_report, conclusion = render_reports(summary)

    assert test_report.startswith("# GraphGuard-Agent Evaluation V3 正式测试结果")
    assert conclusion.startswith("# GraphGuard-Agent Evaluation V3 测试结论")
    for number in range(1, 11):
        assert f"{number}. " in conclusion
    for scope in (
        "controlled dataset",
        "real cross-repo business path",
        "public benchmark",
        "external provider smoke",
    ):
        assert scope in conclusion
    assert "全部通过" not in conclusion
    assert "完全有效" not in conclusion
    assert "tool_overreach 0/20" in conclusion
    assert "missing_provenance 未被" not in conclusion


def test_figures_are_paired_nonempty_and_absent_when_sources_are_missing(tmp_path: Path) -> None:
    context = _copied_context(tmp_path / "with-data")

    generated = generate_figures(context)

    assert generated
    assert {path.suffix for path in generated} == {".png", ".pdf"}
    assert {path.stem for path in generated if path.suffix == ".png"} == {
        path.stem for path in generated if path.suffix == ".pdf"
    }
    assert all(path.stat().st_size > 1000 for path in generated)

    empty = _context(tmp_path / "empty-results", tmp_path / "empty-figures")
    assert generate_figures(empty) == []


def test_artifact_hashes_are_stable_and_exclude_self_reference(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets"
    result_dir = tmp_path / "results"
    figure_dir = tmp_path / "figures"
    for directory in (dataset_dir, result_dir, figure_dir):
        directory.mkdir()
    (dataset_dir / "cases.jsonl").write_text('{"case_id":"a"}\n', encoding="utf-8")
    (result_dir / "summary.json").write_text('{"evaluation_version":"v3"}\n', encoding="utf-8")
    (result_dir / "V3_CONCLUSION.md").write_text("conclusion\n", encoding="utf-8")
    (result_dir / "artifact_hashes.json").write_text("stale\n", encoding="utf-8")
    (result_dir / "evaluation_run.json").write_text("volatile\n", encoding="utf-8")
    (figure_dir / "plot.png").write_bytes(b"png-bytes")
    context = _context(result_dir, figure_dir, dataset_dir)

    first = hash_artifacts(context)
    second = hash_artifacts(context)

    assert first == second
    assert all(not name.endswith("artifact_hashes.json") for name in first["artifacts"])
    assert all(not name.endswith("evaluation_run.json") for name in first["artifacts"])
    assert any(name.startswith("datasets/v3/") for name in first["artifacts"])
    assert any(name.startswith("figures/v3/") for name in first["artifacts"])
