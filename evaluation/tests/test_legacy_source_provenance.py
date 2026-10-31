from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_legacy_source_manifest_distinguishes_git_and_local_snapshot() -> None:
    manifest = json.loads(
        (ROOT / "evaluation" / "legacy_source_manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["git_source"]["commit"] == "4c7062812f72fa2461e981ff632eaeffe0a2d2a0"
    assert manifest["git_source"]["short_commit"] == "4c70628"
    assert len(manifest["git_source"]["python_paths"]) == 43
    assert len(manifest["local_snapshot"]["divergences"]) == 8
    assert {item["status"] for item in manifest["local_snapshot"]["divergences"]} == {
        "modified",
        "extra",
    }
    assert manifest["policy"]["pyc_decompiled"] is False
    assert manifest["policy"]["current_source_is_authoritative"] is True


def test_manifest_has_no_duplicate_source_paths() -> None:
    manifest = json.loads(
        (ROOT / "evaluation" / "legacy_source_manifest.json").read_text(encoding="utf-8")
    )
    paths = manifest["git_source"]["python_paths"]
    assert len(paths) == len(set(paths))
