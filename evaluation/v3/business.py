from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.core.io import write_csv, write_jsonl

FIXED_PYTHON = Path(r"D:\programs\AgentGraph_Sentinel\python.exe")


@dataclass(frozen=True)
class BrowserPorts:
    api: int = 8121
    web: int = 3121
    graphguard: int = 8171
    agent_mock: int = 8221

    def all(self) -> tuple[int, int, int, int]:
        return self.api, self.web, self.graphguard, self.agent_mock


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def occupied_ports(ports: Iterable[int], netstat_text: str) -> list[int]:
    occupied: list[int] = []
    listening = [line for line in netstat_text.splitlines() if "LISTENING" in line.upper()]
    for port in ports:
        if any(re.search(rf":{port}\s", line) for line in listening):
            occupied.append(int(port))
    return occupied


def _default_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, **kwargs)


def _netstat() -> str:
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _run(
    runner: CommandRunner,
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            command,
            124,
            str(exc.output or ""),
            f"command timed out after {exc.timeout} seconds: {exc.stderr or ''}",
        )


def _append_log(path: Path, title: str, completed: subprocess.CompletedProcess[str]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    command = " ".join(str(item) for item in completed.args)
    block = (
        f"## {title}\ncommand: {command}\nexit_code: {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}\n"
    )
    path.write_text(existing + block, encoding="utf-8")


def _write_probe_tables(result_dir: Path, payload: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    cases = list(payload.get("cases") or [])
    business = [row for row in cases if row.get("category") in {"business", "security"}]
    lifecycle = [row for row in cases if row.get("category") == "lifecycle"]
    write_csv(result_dir / "weather_business_metrics.csv", business)
    write_csv(result_dir / "weather_business_predictions.csv", cases)
    write_csv(result_dir / "weather_lifecycle_metrics.csv", lifecycle)
    return cases, lifecycle


def run_weather_business_evaluation(
    weather_repo: Path,
    result_dir: Path,
    *,
    browser: bool = True,
    ports: BrowserPorts | None = None,
    netstat_text: str | None = None,
    runner: CommandRunner = _default_runner,
) -> dict[str, Any]:
    """Run the adjacent Weather service probe and isolated browser profiles."""

    ports = ports or BrowserPorts()
    weather_repo = Path(weather_repo).resolve()
    result_dir = Path(result_dir).resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    probe_script = weather_repo / "scripts" / "evaluate_graphguard_v3.py"
    e2e_script = weather_repo / "scripts" / "e2e.ps1"
    if not weather_repo.is_dir() or not probe_script.is_file():
        return {
            "status": "BLOCKED_LOCAL",
            "reason": "adjacent MeteorologicalBureau repository or V3 probe is missing",
            "browser_status": "NOT_RUN",
            "artifacts": [],
        }

    if browser:
        collision = occupied_ports(ports.all(), netstat_text if netstat_text is not None else _netstat())
        if collision:
            return {
                "status": "BLOCKED_LOCAL",
                "reason": "isolated E2E port collision; no process was terminated",
                "browser_status": "BLOCKED_PORT_COLLISION",
                "occupied_ports": collision,
                "artifacts": [],
            }
        if not e2e_script.is_file():
            return {
                "status": "BLOCKED_LOCAL",
                "reason": "Weather E2E script is missing",
                "browser_status": "NOT_RUN",
                "artifacts": [],
            }

    log_path = result_dir / "weather_business_probe.log"
    probe_output = result_dir / "weather_business_probe.json"
    probe_command = [
        str(FIXED_PYTHON),
        str(probe_script),
        "--output",
        str(probe_output),
        "--modes",
        "observe",
        "enforce",
        "offline",
    ]
    probe_process = _run(runner, probe_command, cwd=weather_repo, timeout=600)
    _append_log(log_path, "service probe", probe_process)
    if probe_output.exists():
        try:
            probe_payload = json.loads(probe_output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            probe_payload = {"status": "FAIL", "cases": [], "reason": str(exc)}
    else:
        probe_payload = {
            "status": "FAIL",
            "cases": [],
            "reason": "probe output missing",
        }
    cases, _ = _write_probe_tables(result_dir, probe_payload)

    browser_rows: list[dict[str, Any]] = []
    if browser:
        for mode in ("observe", "enforce", "offline"):
            command = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(e2e_script),
                "-ApiPort",
                str(ports.api),
                "-WebPort",
                str(ports.web),
                "-Python",
                str(FIXED_PYTHON),
                "-AgentProvider",
                "scripted",
                "-GraphGuardMode",
                mode,
                "-GraphGuardPort",
                str(ports.graphguard),
                "-AgentMockPort",
                str(ports.agent_mock),
                "-TestPaths",
                "apps/web/tests/graphguard-security.spec.ts",
            ]
            completed = _run(runner, command, cwd=weather_repo, timeout=1200)
            _append_log(log_path, f"browser {mode}", completed)
            browser_rows.append(
                {
                    "mode": mode,
                    "status": "PASS" if completed.returncode == 0 else "FAIL",
                    "exit_code": completed.returncode,
                    "stdout_tail": completed.stdout[-1000:],
                    "stderr_tail": completed.stderr[-1000:],
                }
            )
    else:
        browser_rows.append(
            {"mode": "not_requested", "status": "NOT_RUN", "exit_code": None}
        )
    write_csv(result_dir / "weather_frontend_e2e_results.csv", browser_rows)

    failures = [
        {"stage": "weather_service_probe", **row}
        for row in cases
        if row.get("status") not in {"PASS", "SKIP"}
    ]
    failures.extend(
        {"stage": "weather_browser_e2e", **row}
        for row in browser_rows
        if row.get("status") == "FAIL"
    )
    write_jsonl(result_dir / "weather_integration_failure_cases.jsonl", failures)

    probe_passed = probe_process.returncode == 0 and probe_payload.get("status") == "PASS"
    browser_passed = not browser or all(row["status"] == "PASS" for row in browser_rows)
    status = "PASS" if probe_passed and browser_passed else "FAIL"
    return {
        "status": status,
        "probe_status": probe_payload.get("status", "FAIL"),
        "browser_status": "PASS" if browser_passed else "FAIL",
        "occupied_ports": [],
        "artifacts": [
            str(probe_output),
            str(log_path),
            str(result_dir / "weather_business_metrics.csv"),
            str(result_dir / "weather_business_predictions.csv"),
            str(result_dir / "weather_lifecycle_metrics.csv"),
            str(result_dir / "weather_frontend_e2e_results.csv"),
            str(result_dir / "weather_integration_failure_cases.jsonl"),
        ],
    }
