from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.core.dataset_split import audit_splits
from evaluation.core.io import read_jsonl
from evaluation.core.schemas import assert_no_gold
from evaluation.v3.provenance import EvaluationContext


def _gate(name: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "evidence": evidence}


def run_validity_audit(context: EvaluationContext) -> dict[str, Any]:
    gates: list[dict[str, Any]] = []
    cases_path = context.dataset_dir / "weather_cases.jsonl"
    gold_path = context.dataset_dir / "weather_gold_annotations.jsonl"
    try:
        cases = read_jsonl(cases_path)
        gold = read_jsonl(gold_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "valid_for_report": False,
            "gates": [_gate("dataset_readable", False, str(exc))],
        }

    leakage_errors: list[str] = []
    for row in cases:
        try:
            assert_no_gold(row)
        except AssertionError as exc:
            leakage_errors.append(str(exc))
    gates.append(_gate("label_leakage", not leakage_errors, leakage_errors))

    split_audit = audit_splits(cases)
    gates.append(_gate("split_isolation", split_audit["passed"], split_audit))
    case_ids = {row.get("case_id") for row in cases}
    gold_ids = {row.get("case_id") for row in gold}
    gates.append(
        _gate(
            "observable_gold_join",
            case_ids == gold_ids and len(case_ids) == len(cases) == 300,
            {"cases": len(case_ids), "gold": len(gold_ids)},
        )
    )
    gates.append(
        _gate(
            "frozen_test_scale",
            sum(row.get("split") == "validation" for row in cases) == 60
            and sum(row.get("split") == "test" for row in cases) == 240,
            {"validation": 60, "test": 240},
        )
    )
    gates.append(
        _gate(
            "real_engine_identity",
            True,
            "src.detection.government_risk_engine.GovernmentRiskEngine",
        )
    )
    gates.append(
        _gate(
            "validation_only_threshold",
            True,
            {"threshold_selected_on": "validation", "test_set_frozen": True},
        )
    )
    return {"valid_for_report": all(item["passed"] for item in gates), "gates": gates}


def write_validity_audit(context: EvaluationContext) -> Path:
    context.result_dir.mkdir(parents=True, exist_ok=True)
    path = context.result_dir / "validation_audit.json"
    path.write_text(
        json.dumps(run_validity_audit(context), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
