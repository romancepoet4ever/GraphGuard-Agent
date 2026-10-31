from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from evaluation.scripts.run_all_evaluations import build_parser, resolve_output_path
from evaluation.v3.orchestrator import (
    StageDefinition,
    _default_stage_definitions,
    inventory_historical,
    run_v3,
)
from evaluation.v3.provenance import EvaluationContext, RepositoryPaths

ROOT = Path(__file__).resolve().parents[2]


def _context(tmp_path: Path) -> EvaluationContext:
    return EvaluationContext(
        repo_root=tmp_path,
        dataset_dir=tmp_path / "evaluation" / "datasets" / "v3",
        result_dir=tmp_path / "evaluation" / "results" / "v3",
        figure_dir=tmp_path / "evaluation" / "figures" / "v3",
        repositories=RepositoryPaths(
            graphguard=tmp_path,
            weather=tmp_path / "weather",
            interrogation=tmp_path / "interrogation",
        ),
    )


def test_cli_accepts_only_v3_test_and_requires_freeze_config() -> None:
    parser = build_parser()
    parsed = parser.parse_args(
        [
            "--version",
            "v3",
            "--split",
            "test",
            "--freeze-config",
            "--output",
            "evaluation/results/v3",
        ]
    )
    assert parsed.version == "v3"
    assert parsed.split == "test"
    assert parsed.freeze_config is True

    with pytest.raises(SystemExit):
        parser.parse_args(
            ["--version", "v2", "--split", "test", "--freeze-config", "--output", "x"]
        )
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["--version", "v3", "--split", "validation", "--freeze-config", "--output", "x"]
        )
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["--version", "v3", "--split", "test", "--output", "evaluation/results/v3"]
        )


def test_output_must_resolve_under_v3_result_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    allowed = repo / "evaluation" / "results" / "v3"
    allowed.mkdir(parents=True)

    assert resolve_output_path(repo, allowed) == allowed.resolve()
    assert resolve_output_path(repo, allowed / "isolated") == (allowed / "isolated").resolve()
    with pytest.raises(ValueError, match="evaluation/results/v3"):
        resolve_output_path(repo, repo / "evaluation" / "results" / "v2")


def test_regression_retry_keeps_last_complete_summaries_visible(tmp_path: Path) -> None:
    context = _context(tmp_path)
    definitions = _default_stage_definitions(context, {})
    regression = next(
        definition
        for definition in definitions
        if definition.name == "cross_application_regression"
    )

    invalidated_names = {path.name for path in regression.outputs}
    assert "regression_summary.json" not in invalidated_names
    assert "regression_command_checks.json" not in invalidated_names
    assert "pytest_evaluation_v3.xml" in invalidated_names


def test_failed_stage_resumes_without_repeating_completed_independent_stages(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    calls = {"first": 0, "flaky": 0, "independent": 0}

    def first(_: EvaluationContext) -> dict:
        calls["first"] += 1
        artifact = context.result_dir / "first.txt"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("first\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(artifact)]}

    def flaky(_: EvaluationContext) -> dict:
        calls["flaky"] += 1
        if calls["flaky"] == 1:
            raise RuntimeError("expected transient failure")
        artifact = context.result_dir / "flaky.txt"
        artifact.write_text("fixed\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(artifact)]}

    def independent(_: EvaluationContext) -> dict:
        calls["independent"] += 1
        return {"status": "PASS", "artifacts": []}

    definitions = [
        StageDefinition("first", first),
        StageDefinition("flaky", flaky),
        StageDefinition("independent", independent),
    ]

    first_run = run_v3(context, stage_definitions=definitions)
    assert first_run.status == "PARTIAL"
    assert calls == {"first": 1, "flaky": 1, "independent": 1}

    second_run = run_v3(context, stage_definitions=definitions)
    assert second_run.status == "PASS"
    assert calls == {"first": 1, "flaky": 2, "independent": 1}

    state_path = context.result_dir / "evaluation_run.json"
    stable_hash = hashlib.sha256(state_path.read_bytes()).hexdigest()
    third_run = run_v3(context, stage_definitions=definitions)
    assert third_run.to_dict() == second_run.to_dict()
    assert hashlib.sha256(state_path.read_bytes()).hexdigest() == stable_hash
    assert calls == {"first": 1, "flaky": 2, "independent": 1}


def test_dependency_failure_skips_only_dependent_stage(tmp_path: Path) -> None:
    context = _context(tmp_path)
    calls: list[str] = []

    def fail(_: EvaluationContext) -> dict:
        calls.append("fail")
        raise RuntimeError("boom")

    def dependent(_: EvaluationContext) -> dict:
        calls.append("dependent")
        return {"status": "PASS", "artifacts": []}

    def independent(_: EvaluationContext) -> dict:
        calls.append("independent")
        return {"status": "PASS", "artifacts": []}

    run = run_v3(
        context,
        stage_definitions=[
            StageDefinition("fail", fail),
            StageDefinition("dependent", dependent, dependencies=("fail",)),
            StageDefinition("independent", independent),
        ],
    )

    assert calls == ["fail", "independent"]
    assert next(stage for stage in run.stages if stage.name == "dependent").status == "SKIPPED_DEPENDENCY"


def test_resume_reexecutes_dependent_stage_when_upstream_was_rebuilt(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    calls = {"upstream": 0, "dependent": 0}
    upstream_artifact = context.result_dir / "upstream.txt"
    dependent_artifact = context.result_dir / "dependent.txt"

    def upstream(_: EvaluationContext) -> dict:
        calls["upstream"] += 1
        upstream_artifact.parent.mkdir(parents=True, exist_ok=True)
        upstream_artifact.write_text("upstream\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(upstream_artifact)]}

    def dependent(_: EvaluationContext) -> dict:
        calls["dependent"] += 1
        dependent_artifact.write_text("dependent\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(dependent_artifact)]}

    definitions = [
        StageDefinition("upstream", upstream),
        StageDefinition("dependent", dependent, dependencies=("upstream",)),
    ]
    assert run_v3(context, stage_definitions=definitions).status == "PASS"
    upstream_artifact.unlink()

    assert run_v3(context, stage_definitions=definitions).status == "PASS"
    assert calls == {"upstream": 2, "dependent": 2}


def test_soft_refresh_rebuilds_report_without_blocking_on_failed_source(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    calls = {"source": 0, "report": 0}
    source_artifact = context.result_dir / "source.txt"
    report_artifact = context.result_dir / "report.txt"

    def source(_: EvaluationContext) -> dict:
        calls["source"] += 1
        source_artifact.parent.mkdir(parents=True, exist_ok=True)
        source_artifact.write_text("source\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(source_artifact)]}

    def report(_: EvaluationContext) -> dict:
        calls["report"] += 1
        report_artifact.write_text("report\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(report_artifact)]}

    definitions = [
        StageDefinition("source", source),
        StageDefinition("report", report, refresh_after=("source",)),
    ]
    assert run_v3(context, stage_definitions=definitions).status == "PASS"
    source_artifact.unlink()

    assert run_v3(context, stage_definitions=definitions).status == "PASS"
    assert calls == {"source": 2, "report": 2}


def test_failed_stage_cannot_be_overridden_by_stale_pass_summary(tmp_path: Path) -> None:
    context = _context(tmp_path)
    context.result_dir.mkdir(parents=True)
    (context.result_dir / "summary.json").write_text(
        '{"final_status":"PASS"}\n', encoding="utf-8"
    )

    def fail(_: EvaluationContext) -> dict:
        raise RuntimeError("expected failure")

    run = run_v3(context, stage_definitions=[StageDefinition("fail", fail)])

    assert run.status == "PARTIAL"


def test_v2_and_final_sha256_inventory_is_unchanged_by_v3_run(tmp_path: Path) -> None:
    context = _context(tmp_path)
    historical = (
        tmp_path / "evaluation" / "datasets" / "v2" / "cases.jsonl",
        tmp_path / "evaluation" / "results" / "final" / "summary.json",
        tmp_path / "evaluation" / "figures" / "v2" / "plot.png",
    )
    for index, path in enumerate(historical):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"historical-{index}".encode())
    before = inventory_historical(tmp_path)

    def write_v3(_: EvaluationContext) -> dict:
        artifact = context.result_dir / "new.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("{}\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(artifact)]}

    run = run_v3(context, stage_definitions=[StageDefinition("write_v3", write_v3)])
    after = inventory_historical(tmp_path)

    assert run.status == "PASS"
    assert before == after


def test_resume_invalidates_cached_preservation_when_historical_bytes_change(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    historical = tmp_path / "evaluation" / "results" / "final" / "summary.json"
    historical.parent.mkdir(parents=True)
    historical.write_text('{"status":"baseline"}\n', encoding="utf-8")
    calls = {"preservation": 0, "report": 0}
    preservation_artifact = context.result_dir / "historical_preservation.json"
    report_artifact = context.result_dir / "report.txt"

    def preservation(_: EvaluationContext) -> dict:
        calls["preservation"] += 1
        preservation_artifact.parent.mkdir(parents=True, exist_ok=True)
        preservation_artifact.write_text("checked\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(preservation_artifact)]}

    def report(_: EvaluationContext) -> dict:
        calls["report"] += 1
        report_artifact.write_text("reported\n", encoding="utf-8")
        return {"status": "PASS", "artifacts": [str(report_artifact)]}

    definitions = [
        StageDefinition("historical_preservation", preservation),
        StageDefinition(
            "report",
            report,
            refresh_after=("historical_preservation",),
        ),
    ]
    assert run_v3(context, stage_definitions=definitions).status == "PASS"
    historical.write_text('{"status":"tampered"}\n', encoding="utf-8")

    resumed = run_v3(context, stage_definitions=definitions)

    assert resumed.status == "INVALID"
    assert resumed.historical_preservation["changed"] == [
        "evaluation/results/final/summary.json"
    ]
    assert calls == {"preservation": 2, "report": 2}
