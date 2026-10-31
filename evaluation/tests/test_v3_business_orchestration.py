from __future__ import annotations

import subprocess
from pathlib import Path

from evaluation.v3.business import (
    FIXED_PYTHON,
    BrowserPorts,
    occupied_ports,
    run_weather_business_evaluation,
)


def test_missing_weather_repository_is_blocked_without_affecting_controlled_stages(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    result = run_weather_business_evaluation(
        tmp_path / "missing",
        tmp_path / "results",
        browser=True,
        runner=runner,
    )

    assert result["status"] == "BLOCKED_LOCAL"
    assert calls == []


def test_occupied_ports_block_browser_without_starting_or_killing_processes(
    tmp_path: Path,
) -> None:
    weather = tmp_path / "weather"
    (weather / "scripts").mkdir(parents=True)
    (weather / "scripts" / "evaluate_graphguard_v3.py").write_text("", encoding="utf-8")
    (weather / "scripts" / "e2e.ps1").write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    ports = BrowserPorts(api=8121, web=3121, graphguard=8171, agent_mock=8221)
    result = run_weather_business_evaluation(
        weather,
        tmp_path / "results",
        browser=True,
        ports=ports,
        netstat_text="TCP 127.0.0.1:8121 0.0.0.0:0 LISTENING 9999",
        runner=runner,
    )

    assert occupied_ports(ports.all(), "TCP 127.0.0.1:8121 0.0.0.0:0 LISTENING 9999") == [8121]
    assert result["status"] == "BLOCKED_LOCAL"
    assert result["browser_status"] == "BLOCKED_PORT_COLLISION"
    assert result["occupied_ports"] == [8121]
    assert calls == []


def test_wrapper_uses_fixed_python_and_preserves_raw_logs(tmp_path: Path) -> None:
    weather = tmp_path / "weather"
    scripts = weather / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "evaluate_graphguard_v3.py").write_text("", encoding="utf-8")
    (scripts / "e2e.ps1").write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        del kwargs
        calls.append(command)
        if "evaluate_graphguard_v3.py" in " ".join(command):
            output = Path(command[command.index("--output") + 1])
            output.write_text(
                '{"status":"PASS","cases":[],"summary":{"total":0,"passed":0,"failed":0,"skipped":0,"exit_code":0}}',
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(command, 0, "probe stdout", "probe stderr")

    result = run_weather_business_evaluation(
        weather,
        tmp_path / "results",
        browser=False,
        runner=runner,
    )

    assert result["status"] == "PASS"
    assert calls[0][0] == str(FIXED_PYTHON)
    log = tmp_path / "results" / "weather_business_probe.log"
    assert "probe stdout" in log.read_text(encoding="utf-8")
    assert "probe stderr" in log.read_text(encoding="utf-8")
