from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class RepositoryPaths:
    graphguard: Path
    weather: Path
    interrogation: Path


@dataclass(frozen=True)
class RepoProbe:
    repositories: dict[str, dict[str, Any]]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {"generated_at": self.generated_at, "repositories": self.repositories}

    def to_markdown(self) -> str:
        lines = ["# Evaluation V3 Repository Probe", "", "| Repository | Status | Revision | Path |", "|---|---|---|---|"]
        for name, value in self.repositories.items():
            lines.append(
                f"| {name} | {value['status']} | {value.get('revision') or '-'} | {value['path']} |"
            )
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class EvaluationContext:
    repo_root: Path
    dataset_dir: Path
    result_dir: Path
    figure_dir: Path
    repositories: RepositoryPaths
    dataset_hashes: dict[str, str] = field(default_factory=dict)
    seed: int = 20261012
    anomaly_threshold: float | None = None
    semantic_status: str = "BLOCKED_EXTERNAL"


def _run_git(path: Path, *args: str) -> tuple[int, str]:
    try:
        process = subprocess.run(
            ["git", "-C", str(path), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return process.returncode, process.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def _probe_repository(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    base: dict[str, Any] = {"path": str(resolved), "revision": "", "dirty": None}
    if not resolved.exists():
        return {**base, "status": "BLOCKED_LOCAL", "reason": "repository path missing"}
    if not (resolved / ".git").exists():
        return {**base, "status": "NOT_GIT", "reason": "no .git directory"}
    top_code, top_level = _run_git(resolved, "rev-parse", "--show-toplevel")
    if top_code != 0 or Path(top_level).resolve() != resolved:
        return {**base, "status": "COMMITLESS", "reason": "repository has no commit"}
    code, revision = _run_git(resolved, "rev-parse", "HEAD")
    if code != 0 or not revision:
        return {**base, "status": "COMMITLESS", "reason": "repository has no commit"}
    status_code, porcelain = _run_git(resolved, "status", "--short")
    return {
        **base,
        "status": "AVAILABLE" if status_code == 0 else "PROBE_ERROR",
        "revision": revision,
        "dirty": bool(porcelain) if status_code == 0 else None,
        "branch": _run_git(resolved, "branch", "--show-current")[1],
    }


def probe_repositories(paths: RepositoryPaths) -> RepoProbe:
    return RepoProbe(
        repositories={
            "graphguard": _probe_repository(paths.graphguard),
            "weather": _probe_repository(paths.weather),
            "interrogation": _probe_repository(paths.interrogation),
        },
        generated_at=datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unavailable"


def freeze_config(context: EvaluationContext) -> dict[str, Any]:
    policy_path = context.repo_root / "config/policy_packs/government_weather/rules.yaml"
    probe = probe_repositories(context.repositories)
    return {
        "evaluation_version": "v3",
        "seed": context.seed,
        "timezone": "Asia/Tokyo",
        "threshold_selected_on": "validation",
        "test_set_frozen": True,
        "anomaly_threshold": context.anomaly_threshold,
        "semantic_status": context.semantic_status,
        "capture_modes": ["controlled", "business_service", "browser_e2e"],
        "guard_modes": ["disabled", "observe", "enforce"],
        "risk_engine_class": "src.detection.government_risk_engine.GovernmentRiskEngine",
        "policy_pack": "government_weather",
        "policy_pack_sha256": _sha256(policy_path) if policy_path.exists() else None,
        "dataset_hashes": dict(sorted(context.dataset_hashes.items())),
        "repositories": probe.repositories,
        "runtime": {
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "node_version": _command_version(["node", "--version"]),
            "packages": {
                name: _package_version(name)
                for name in ("networkx", "scikit-learn", "matplotlib", "pytest")
            },
        },
        "secret_environment_keys_present": sorted(
            key
            for key in os.environ
            if any(token in key.upper() for token in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))
        ),
    }


def _command_version(command: list[str]) -> str:
    try:
        process = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (process.stdout or process.stderr).strip() if process.returncode == 0 else "unavailable"
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def write_provenance_artifacts(context: EvaluationContext) -> dict[str, Path]:
    context.result_dir.mkdir(parents=True, exist_ok=True)
    probe = probe_repositories(context.repositories)
    probe_path = context.result_dir / "REPO_PROBE.md"
    config_path = context.result_dir / "frozen_config.json"
    probe_path.write_text(probe.to_markdown(), encoding="utf-8")
    config_path.write_text(
        json.dumps(freeze_config(context), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"repo_probe": probe_path, "frozen_config": config_path}

