from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from evaluation.v3.regression import (
    CommandCheckSpec,
    CommandSpec,
    build_default_command_checks,
    build_default_specs,
    parse_junit,
    probe_external_services,
    probe_git_revision,
    run_command_check,
    run_regression_suite,
)


def _xml(path: Path, *, tests: int = 2, failures: int = 0, errors: int = 0, skipped: int = 0) -> None:
    path.write_text(
        f'<testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}" time="0.5"/>',
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("exit_code", "write_xml", "xml_text", "expected"),
    [
        (1, True, None, "FAILED_NONZERO"),
        (0, False, None, "MISSING_XML"),
        (0, True, "not xml", "MALFORMED_XML"),
        (0, True, '<testsuite tests="2" failures="0" errors="0" skipped="2"/>', "SKIPPED"),
    ],
)
def test_regression_statuses_are_not_collapsed_to_pass(
    tmp_path: Path,
    exit_code: int,
    write_xml: bool,
    xml_text: str | None,
    expected: str,
) -> None:
    xml_path = tmp_path / "suite.xml"
    log_path = tmp_path / "suite.log"
    spec = CommandSpec("suite", tmp_path, ["fake"], 5, xml_path, log_path)

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        del kwargs
        if write_xml:
            if xml_text is None:
                _xml(xml_path)
            else:
                xml_path.write_text(xml_text, encoding="utf-8")
        return subprocess.CompletedProcess(command, exit_code, "stdout", "stderr")

    result = run_regression_suite(spec, runner=runner)

    assert result.status == expected
    assert result.status != "PASS"
    assert log_path.exists()


def test_missing_suite_directory_is_blocked_locally(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    spec = CommandSpec(
        "suite",
        missing,
        ["fake"],
        5,
        tmp_path / "suite.xml",
        tmp_path / "suite.log",
    )

    result = run_regression_suite(spec)

    assert result.status == "BLOCKED_LOCAL"
    assert result.exit_code is None
    assert "does not exist" in result.reason
    assert Path(result.log_path).is_file()


def test_missing_executable_is_execution_error(tmp_path: Path) -> None:
    spec = CommandSpec(
        "suite",
        tmp_path,
        ["missing"],
        5,
        tmp_path / "suite.xml",
        tmp_path / "suite.log",
    )

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        del command, kwargs
        raise FileNotFoundError("missing executable")

    result = run_regression_suite(spec, runner=runner)

    assert result.status == "EXECUTION_ERROR"
    assert "FileNotFoundError" in result.reason


def test_parse_junit_sums_nested_suites(tmp_path: Path) -> None:
    path = tmp_path / "nested.xml"
    path.write_text(
        '<testsuites><testsuite tests="2" failures="1" errors="0" skipped="0" time="0.2"/>'
        '<testsuite tests="3" failures="0" errors="1" skipped="1" time="0.4"/></testsuites>',
        encoding="utf-8",
    )

    summary = parse_junit(path)
    assert summary.tests == 5
    assert summary.failures == 1
    assert summary.errors == 1
    assert summary.skipped == 1
    assert summary.duration_s == pytest.approx(0.6)


def test_commitless_and_external_provider_have_distinct_statuses(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    assert probe_git_revision(tmp_path)["status"] == "COMMITLESS"
    external = probe_external_services(provider=None)
    assert external["status"] == "BLOCKED_EXTERNAL"
    assert external["status"] != "HISTORICAL_V2_REUSE"


def test_git_revision_probe_resolves_repository_from_nested_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    nested = repo / "apps" / "web"
    nested.mkdir(parents=True)
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "evaluation@example.invalid"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Evaluation Test"],
        check=True,
        capture_output=True,
    )
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", "tracked.txt"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "test revision"],
        check=True,
        capture_output=True,
    )

    result = probe_git_revision(nested)

    assert result["status"] == "AVAILABLE"
    assert len(result["revision"]) == 40


def test_default_specs_use_fixed_python_and_named_junit_artifacts(tmp_path: Path) -> None:
    graphguard = tmp_path / "graphguard"
    weather = tmp_path / "weather"
    interrogation = tmp_path / "interrogation"
    for path in (graphguard, weather, interrogation / "backend"):
        path.mkdir(parents=True)

    specs = build_default_specs(graphguard, weather, interrogation, tmp_path / "results")

    assert [spec.name for spec in specs] == [
        "graphguard",
        "evaluation_v3",
        "weather_v3",
        "interrogation_contract",
    ]
    assert all(spec.command[0] == r"D:\programs\AgentGraph_Sentinel\python.exe" for spec in specs)
    assert {spec.xml_path.name for spec in specs} == {
        "pytest_graphguard_v3.xml",
        "pytest_evaluation_v3.xml",
        "pytest_weather_v3.xml",
        "pytest_interrogation_contract_v3.xml",
    }
    weather_spec = next(spec for spec in specs if spec.name == "weather_v3")
    weather_basetemp = next(
        item.split("=", 1)[1]
        for item in weather_spec.command
        if item.startswith("--basetemp=")
    )
    assert Path(weather_basetemp).resolve().is_relative_to(weather.resolve())
    interrogation_spec = next(
        spec for spec in specs if spec.name == "interrogation_contract"
    )
    expected_sdk = str((graphguard / "sdk" / "python").resolve())
    assert interrogation_spec.environment == {
        "PYTHONPATH": expected_sdk,
        "GRAPHGUARD_SDK_PATH": expected_sdk,
    }


def test_regression_suite_applies_explicit_environment_without_logging_it(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "suite.xml"
    log_path = tmp_path / "suite.log"
    spec = CommandSpec(
        "suite",
        tmp_path,
        ["fake"],
        5,
        xml_path,
        log_path,
        {"PYTHONPATH": "fixture-sdk", "SECRET_TOKEN": "not-for-log"},
    )

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        assert kwargs["env"]["PYTHONPATH"] == "fixture-sdk"
        assert kwargs["env"]["SECRET_TOKEN"] == "not-for-log"
        _xml(xml_path)
        return subprocess.CompletedProcess(command, 0, "stdout", "stderr")

    result = run_regression_suite(spec, runner=runner)

    assert result.status == "PASS"
    assert "not-for-log" not in log_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(("exit_code", "expected"), [(0, "PASS"), (2, "FAILED_NONZERO")])
def test_command_check_preserves_exit_status_and_log(
    tmp_path: Path, exit_code: int, expected: str
) -> None:
    spec = CommandCheckSpec("lint", tmp_path, ["fake"], 5, tmp_path / "lint.log")

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(command, exit_code, "stdout", "stderr")

    result = run_command_check(spec, runner=runner)

    assert result.status == expected
    assert result.exit_code == exit_code
    assert Path(result.log_path).read_text(encoding="utf-8").startswith("command: fake")


def test_default_command_checks_cover_weather_quality_gates(tmp_path: Path) -> None:
    weather = tmp_path / "weather"
    weather.mkdir()

    specs = build_default_command_checks(weather, tmp_path / "results")

    assert [spec.name for spec in specs] == [
        "weather_ruff",
        "weather_frontend_typecheck",
        "weather_frontend_build",
    ]
    assert specs[0].command[:4] == [
        r"D:\programs\AgentGraph_Sentinel\python.exe",
        "-m",
        "ruff",
        "check",
    ]
    web = weather / "apps" / "web"
    assert specs[1].cwd == web
    assert specs[1].command == [
        str((web / "node_modules" / ".bin" / "tsc.cmd").resolve()),
        "--noEmit",
        "--incremental",
        "false",
    ]
    assert specs[2].cwd == web
    assert specs[2].command == [
        str((web / "node_modules" / ".bin" / "next.cmd").resolve()),
        "build",
    ]
