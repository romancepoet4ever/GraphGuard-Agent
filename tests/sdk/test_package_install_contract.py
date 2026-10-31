from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_sdk_installs_and_imports_outside_repository(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[2]
    sdk_root = repository / "sdk" / "python"
    sdk_source = tmp_path / "sdk-source"
    sdk_source.mkdir()
    shutil.copy2(sdk_root / "pyproject.toml", sdk_source / "pyproject.toml")
    shutil.copy2(sdk_root / "README.md", sdk_source / "README.md")
    shutil.copytree(sdk_root / "graphguard", sdk_source / "graphguard")
    target = tmp_path / "site-packages"
    outside = tmp_path / "outside-repository"
    outside.mkdir()

    install = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--no-build-isolation",
            "--no-deps",
            "--target",
            str(target),
            str(sdk_source),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert install.returncode == 0, install.stderr

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(target)
    imported = subprocess.run(
        [
            sys.executable,
            "-c",
            "from graphguard import GraphGuardClient; print(GraphGuardClient.__name__)",
        ],
        cwd=outside,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert imported.returncode == 0, imported.stderr
    assert imported.stdout.strip() == "GraphGuardClient"
