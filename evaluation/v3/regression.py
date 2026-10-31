from __future__ import annotations

import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommandSpec:
    name: str
    cwd: Path
    command: list[str]
    timeout_s: int
    xml_path: Path
    log_path: Path
    environment: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandCheckSpec:
    name: str
    cwd: Path
    command: list[str]
    timeout_s: int
    log_path: Path


@dataclass(frozen=True)
class TestSummary:
    tests: int
    failures: int
    errors: int
    skipped: int
    duration_s: float


@dataclass(frozen=True)
class RegressionResult:
    name: str
    status: str
    command: list[str]
    cwd: str
    revision: str
    exit_code: int | None
    elapsed_s: float
    summary: TestSummary | None
    xml_path: str
    log_path: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        return value


@dataclass(frozen=True)
class CommandCheckResult:
    name: str
    status: str
    command: list[str]
    cwd: str
    revision: str
    exit_code: int | None
    elapsed_s: float
    log_path: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Runner = Callable[..., subprocess.CompletedProcess[str]]
FIXED_PYTHON = r"D:\programs\AgentGraph_Sentinel\python.exe"


def parse_junit(path: Path) -> TestSummary:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise ValueError("JUnit XML contains no testsuite")
    return TestSummary(
        tests=sum(int(suite.attrib.get("tests", 0)) for suite in suites),
        failures=sum(int(suite.attrib.get("failures", 0)) for suite in suites),
        errors=sum(int(suite.attrib.get("errors", 0)) for suite in suites),
        skipped=sum(int(suite.attrib.get("skipped", 0)) for suite in suites),
        duration_s=sum(float(suite.attrib.get("time", 0.0)) for suite in suites),
    )


def probe_git_revision(path: Path) -> dict[str, Any]:
    resolved = Path(path).resolve()
    if not resolved.exists():
        return {"status": "BLOCKED_LOCAL", "revision": "", "path": str(resolved)}
    has_local_git_marker = (resolved / ".git").exists()
    try:
        top = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        revision = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return {"status": "PROBE_ERROR", "revision": "", "path": str(resolved)}
    if top.returncode != 0:
        status = "COMMITLESS" if has_local_git_marker else "NOT_GIT"
        return {"status": status, "revision": "", "path": str(resolved)}
    repository_root = Path(top.stdout.strip()).resolve()
    if has_local_git_marker and repository_root != resolved:
        return {"status": "COMMITLESS", "revision": "", "path": str(resolved)}
    if revision.returncode != 0 or not revision.stdout.strip():
        return {"status": "COMMITLESS", "revision": "", "path": str(resolved)}
    return {
        "status": "AVAILABLE",
        "revision": revision.stdout.strip(),
        "path": str(resolved),
        "repository_root": str(repository_root),
    }


def _default_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, **kwargs)


def run_regression_suite(
    spec: CommandSpec,
    *,
    runner: Runner = _default_runner,
) -> RegressionResult:
    spec.xml_path.parent.mkdir(parents=True, exist_ok=True)
    spec.log_path.parent.mkdir(parents=True, exist_ok=True)
    spec.xml_path.unlink(missing_ok=True)
    if not spec.cwd.is_dir():
        reason = f"local suite directory does not exist: {spec.cwd}"
        spec.log_path.write_text(
            f"command: {' '.join(spec.command)}\ncwd: {spec.cwd}\nstatus: BLOCKED_LOCAL\nreason: {reason}\n",
            encoding="utf-8",
        )
        return RegressionResult(
            name=spec.name,
            status="BLOCKED_LOCAL",
            command=spec.command,
            cwd=str(spec.cwd.resolve()),
            revision="",
            exit_code=None,
            elapsed_s=0.0,
            summary=None,
            xml_path=str(spec.xml_path.resolve()),
            log_path=str(spec.log_path.resolve()),
            reason=reason,
        )
    started = time.perf_counter()
    execution_error = ""
    try:
        runner_options: dict[str, Any] = {
            "cwd": spec.cwd,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": spec.timeout_s,
        }
        if spec.environment:
            runner_options["env"] = {**os.environ, **spec.environment}
        completed = runner(spec.command, **runner_options)
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(
            spec.command,
            124,
            str(exc.output or ""),
            f"timed out after {exc.timeout} seconds: {exc.stderr or ''}",
        )
    except OSError as exc:
        execution_error = f"{type(exc).__name__}: {exc}"
        completed = subprocess.CompletedProcess(spec.command, 127, "", execution_error)
    elapsed = time.perf_counter() - started
    spec.log_path.write_text(
        (
            f"command: {' '.join(spec.command)}\n"
            f"cwd: {spec.cwd}\nexit_code: {completed.returncode}\n"
            f"elapsed_s: {elapsed:.6f}\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}\n"
        ),
        encoding="utf-8",
    )
    revision_probe = probe_git_revision(spec.cwd)
    revision = str(revision_probe.get("revision") or "")

    summary: TestSummary | None = None
    reason = ""
    if execution_error:
        status = "EXECUTION_ERROR"
        reason = execution_error
    elif completed.returncode != 0:
        status = "TIMEOUT" if completed.returncode == 124 else "FAILED_NONZERO"
        reason = f"command exited with {completed.returncode}"
        if spec.xml_path.exists():
            try:
                summary = parse_junit(spec.xml_path)
            except (ET.ParseError, ValueError, OSError):
                pass
    elif not spec.xml_path.exists():
        status = "MISSING_XML"
        reason = "required JUnit XML was not produced"
    else:
        try:
            summary = parse_junit(spec.xml_path)
        except (ET.ParseError, ValueError, OSError) as exc:
            status = "MALFORMED_XML"
            reason = str(exc)
        else:
            if summary.tests == 0 or summary.skipped == summary.tests:
                status = "SKIPPED"
                reason = "suite executed no non-skipped tests"
            elif summary.failures or summary.errors:
                status = "FAILED_TESTS"
                reason = "JUnit reports failures or errors"
            else:
                status = "PASS"

    return RegressionResult(
        name=spec.name,
        status=status,
        command=spec.command,
        cwd=str(spec.cwd.resolve()),
        revision=revision,
        exit_code=completed.returncode,
        elapsed_s=round(elapsed, 6),
        summary=summary,
        xml_path=str(spec.xml_path.resolve()),
        log_path=str(spec.log_path.resolve()),
        reason=reason,
    )


def run_command_check(
    spec: CommandCheckSpec,
    *,
    runner: Runner = _default_runner,
) -> CommandCheckResult:
    spec.log_path.parent.mkdir(parents=True, exist_ok=True)
    if not spec.cwd.is_dir():
        reason = f"local command directory does not exist: {spec.cwd}"
        spec.log_path.write_text(
            f"command: {' '.join(spec.command)}\ncwd: {spec.cwd}\nstatus: BLOCKED_LOCAL\nreason: {reason}\n",
            encoding="utf-8",
        )
        return CommandCheckResult(
            name=spec.name,
            status="BLOCKED_LOCAL",
            command=spec.command,
            cwd=str(spec.cwd.resolve()),
            revision="",
            exit_code=None,
            elapsed_s=0.0,
            log_path=str(spec.log_path.resolve()),
            reason=reason,
        )
    started = time.perf_counter()
    execution_error = ""
    try:
        completed = runner(
            spec.command,
            cwd=spec.cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=spec.timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(
            spec.command,
            124,
            str(exc.output or ""),
            f"timed out after {exc.timeout} seconds: {exc.stderr or ''}",
        )
    except OSError as exc:
        execution_error = f"{type(exc).__name__}: {exc}"
        completed = subprocess.CompletedProcess(spec.command, 127, "", execution_error)
    elapsed = time.perf_counter() - started
    spec.log_path.write_text(
        (
            f"command: {' '.join(spec.command)}\n"
            f"cwd: {spec.cwd}\nexit_code: {completed.returncode}\n"
            f"elapsed_s: {elapsed:.6f}\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}\n"
        ),
        encoding="utf-8",
    )
    revision = str(probe_git_revision(spec.cwd).get("revision") or "")
    status = "PASS" if completed.returncode == 0 else "FAILED_NONZERO"
    reason = ""
    if execution_error:
        status = "EXECUTION_ERROR"
        reason = execution_error
    elif completed.returncode == 124:
        status = "TIMEOUT"
        reason = f"command timed out after {spec.timeout_s} seconds"
    elif completed.returncode != 0:
        reason = f"command exited with {completed.returncode}"
    return CommandCheckResult(
        name=spec.name,
        status=status,
        command=spec.command,
        cwd=str(spec.cwd.resolve()),
        revision=revision,
        exit_code=completed.returncode,
        elapsed_s=round(elapsed, 6),
        log_path=str(spec.log_path.resolve()),
        reason=reason,
    )


def probe_external_services(provider: Any | None) -> dict[str, Any]:
    if provider is None:
        return {
            "status": "BLOCKED_EXTERNAL",
            "reason": "No explicit external semantic/Qwen provider supplied.",
            "fallback_used": False,
        }
    return {
        "status": "NOT_EXECUTED",
        "reason": "External provider probe requires an explicit adapter.",
        "fallback_used": False,
    }


def build_default_specs(
    graphguard: Path,
    weather: Path,
    interrogation: Path,
    result_dir: Path,
) -> list[CommandSpec]:
    result_dir = Path(result_dir).resolve()

    def pytest_command(xml: Path, basetemp: Path, *targets: str) -> list[str]:
        return [
            FIXED_PYTHON,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={basetemp.resolve()}",
            f"--junitxml={xml}",
            *targets,
        ]

    graphguard_xml = result_dir / "pytest_graphguard_v3.xml"
    evaluation_xml = result_dir / "pytest_evaluation_v3.xml"
    weather_xml = result_dir / "pytest_weather_v3.xml"
    interrogation_xml = result_dir / "pytest_interrogation_contract_v3.xml"
    interrogation_backend = Path(interrogation) / "backend"
    graphguard_sdk = str((Path(graphguard) / "sdk" / "python").resolve())
    return [
        CommandSpec(
            "graphguard",
            Path(graphguard),
            pytest_command(graphguard_xml, result_dir / ".pytest-graphguard-v3", "tests"),
            1200,
            graphguard_xml,
            result_dir / "pytest_graphguard_v3.log",
        ),
        CommandSpec(
            "evaluation_v3",
            Path(graphguard),
            pytest_command(
                evaluation_xml,
                result_dir / ".pytest-evaluation-v3",
                "evaluation/tests",
            ),
            1200,
            evaluation_xml,
            result_dir / "pytest_evaluation_v3.log",
        ),
        CommandSpec(
            "weather_v3",
            Path(weather),
            pytest_command(
                weather_xml,
                Path(weather) / ".tmp" / "pytest-weather-v3-regression",
            ),
            2400,
            weather_xml,
            result_dir / "pytest_weather_v3.log",
        ),
        CommandSpec(
            "interrogation_contract",
            interrogation_backend,
            pytest_command(
                interrogation_xml,
                result_dir / ".pytest-interrogation-v3",
                "tests/test_graphguard_import_contract.py",
                "tests/test_graphguard_runtime_guard.py",
                "tests/test_graphguard_integration.py",
                "tests/test_graphguard_fail_open.py",
                "tests/test_graphguard_stream_guard.py",
                "tests/test_graphguard_tool_guard_e2e.py",
            ),
            1200,
            interrogation_xml,
            result_dir / "pytest_interrogation_contract_v3.log",
            {
                "PYTHONPATH": graphguard_sdk,
                "GRAPHGUARD_SDK_PATH": graphguard_sdk,
            },
        ),
    ]


def build_default_command_checks(
    weather: Path,
    result_dir: Path,
) -> list[CommandCheckSpec]:
    weather = Path(weather)
    web = weather / "apps" / "web"
    result_dir = Path(result_dir).resolve()
    return [
        CommandCheckSpec(
            "weather_ruff",
            weather,
            [FIXED_PYTHON, "-m", "ruff", "check", "."],
            600,
            result_dir / "weather_ruff_v3.log",
        ),
        CommandCheckSpec(
            "weather_frontend_typecheck",
            web,
            [
                str((web / "node_modules" / ".bin" / "tsc.cmd").resolve()),
                "--noEmit",
                "--incremental",
                "false",
            ],
            1200,
            result_dir / "weather_frontend_typecheck_v3.log",
        ),
        CommandCheckSpec(
            "weather_frontend_build",
            web,
            [str((web / "node_modules" / ".bin" / "next.cmd").resolve()), "build"],
            1800,
            result_dir / "weather_frontend_build_v3.log",
        ),
    ]


def write_regression_summary(path: Path, results: list[RegressionResult]) -> Path:
    return _write_summary(path, [result.to_dict() for result in results])


def _write_summary(path: Path, payload: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def write_command_check_summary(path: Path, results: list[CommandCheckResult]) -> Path:
    return _write_summary(path, [result.to_dict() for result in results])
