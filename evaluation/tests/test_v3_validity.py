from __future__ import annotations

import json
from pathlib import Path

from evaluation.v3.dataset_builder import build_weather_dataset, write_dataset
from evaluation.v3.provenance import (
    EvaluationContext,
    RepositoryPaths,
    freeze_config,
    probe_repositories,
)
from evaluation.v3.validity import run_validity_audit


def _context(tmp_path: Path) -> EvaluationContext:
    dataset_dir = tmp_path / "datasets"
    result_dir = tmp_path / "results"
    hashes = write_dataset(build_weather_dataset(), dataset_dir)
    return EvaluationContext(
        repo_root=Path.cwd(),
        dataset_dir=dataset_dir,
        result_dir=result_dir,
        figure_dir=tmp_path / "figures",
        repositories=RepositoryPaths(
            graphguard=Path.cwd(),
            weather=Path.cwd().parent / "MeteorologicalBureau",
            interrogation=Path.cwd().parent / "interrogation_agent",
        ),
        dataset_hashes=hashes,
    )


def test_repository_probe_distinguishes_missing_and_commitless(tmp_path: Path) -> None:
    commitless = tmp_path / "commitless"
    (commitless / ".git").mkdir(parents=True)
    probes = probe_repositories(
        RepositoryPaths(Path.cwd(), tmp_path / "missing", commitless)
    )

    assert probes.repositories["graphguard"]["status"] == "AVAILABLE"
    assert probes.repositories["weather"]["status"] == "BLOCKED_LOCAL"
    assert probes.repositories["interrogation"]["status"] == "COMMITLESS"


def test_frozen_config_records_validity_contract_without_secret_values(tmp_path: Path) -> None:
    context = _context(tmp_path)
    config = freeze_config(context)
    encoded = json.dumps(config, ensure_ascii=False).lower()

    assert config["evaluation_version"] == "v3"
    assert config["threshold_selected_on"] == "validation"
    assert config["test_set_frozen"] is True
    assert config["seed"] == 20261012
    assert config["risk_engine_class"] == (
        "src.detection.government_risk_engine.GovernmentRiskEngine"
    )
    assert "api_key" not in encoded
    assert "token=" not in encoded


def test_validity_audit_passes_frozen_dataset_and_fails_label_leakage(tmp_path: Path) -> None:
    context = _context(tmp_path)
    audit = run_validity_audit(context)
    assert audit["valid_for_report"] is True
    assert all(gate["passed"] for gate in audit["gates"])

    cases_path = context.dataset_dir / "weather_cases.jsonl"
    rows = cases_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(rows[0])
    first["gold_label"] = True
    rows[0] = json.dumps(first, ensure_ascii=False)
    cases_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    failed = run_validity_audit(context)
    assert failed["valid_for_report"] is False
    assert next(gate for gate in failed["gates"] if gate["name"] == "label_leakage")[
        "passed"
    ] is False

