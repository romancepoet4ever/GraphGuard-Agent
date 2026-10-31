from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from evaluation.core.io import write_csv
from evaluation.core.schemas import EvaluationResult

_IGNORED_KEYS = {
    "trace_id",
    "graphguard_trace_id",
    "created_at",
    "updated_at",
    "started_at",
    "finished_at",
    "timestamp",
    "duration_ms",
    "latency_ms",
    "security_summary",
    "security_metadata",
    "graphguard",
    "graphguard_blocked",
    "graphguard_sanitized",
    "matched_rule_ids",
    "actions",
    "decision_risk_types",
    "trace_node_count",
    "trace_edge_count",
    "outcome_evidence",
    "attack_success",
    "mode",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize(child)
            for key, child in sorted(value.items())
            if key not in _IGNORED_KEYS
            and not key.startswith("graphguard_")
            and not key.startswith("security_")
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def normalize_business_outcome(value: dict[str, Any]) -> dict[str, Any]:
    """Remove runtime/security noise while preserving business-observable behavior."""

    return _normalize(value)


def _hash(value: dict[str, Any]) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compare_modes(
    disabled: list[dict[str, Any]],
    observe: list[dict[str, Any]],
    enforce: list[dict[str, Any]],
) -> EvaluationResult:
    disabled_by_id = {str(row["case_id"]): row for row in disabled}
    observe_by_id = {str(row["case_id"]): row for row in observe}
    enforce_by_id = {str(row["case_id"]): row for row in enforce}
    common = sorted(set(disabled_by_id) & set(observe_by_id) & set(enforce_by_id))
    predictions: list[dict[str, Any]] = []
    for case_id in common:
        base = disabled_by_id[case_id]
        observed = observe_by_id[case_id]
        enforced = enforce_by_id[case_id]
        base_normalized = normalize_business_outcome(base)
        observe_normalized = normalize_business_outcome(observed)
        enforce_normalized = normalize_business_outcome(enforced)
        raw_provenance_keys = ("raw_tool_result_hash", "raw_result", "provenance")
        raw_provenance_equal = all(
            base.get(key) == observed.get(key) for key in raw_provenance_keys
        )
        tool_keys = ("selected_tool", "tool_name", "tool_args", "called_tool_ids")
        tool_equal = all(base.get(key) == observed.get(key) for key in tool_keys)
        predictions.append(
            {
                "case_id": case_id,
                "positive": bool(base.get("positive", False)),
                "disabled_business_hash": _hash(base_normalized),
                "observe_business_hash": _hash(observe_normalized),
                "enforce_business_hash": _hash(enforce_normalized),
                "observe_equivalent": base_normalized == observe_normalized,
                "enforce_equivalent": base_normalized == enforce_normalized,
                "raw_provenance_equivalent": raw_provenance_equal,
                "tool_selection_preserved": tool_equal,
                "enforce_blocked": bool(enforced.get("graphguard_blocked")),
                "enforce_sanitized": bool(enforced.get("graphguard_sanitized")),
            }
        )

    normals = [row for row in predictions if not row["positive"]]
    denominator = len(normals)
    metric = {
        "scope": "overall",
        "cases": len(predictions),
        "normal_cases": denominator,
        "observe_business_equivalence_rate": sum(row["observe_equivalent"] for row in normals)
        / denominator
        if denominator
        else None,
        "raw_provenance_equivalence_rate": sum(
            row["raw_provenance_equivalent"] for row in normals
        )
        / denominator
        if denominator
        else None,
        "tool_selection_preservation_rate": sum(
            row["tool_selection_preserved"] for row in normals
        )
        / denominator
        if denominator
        else None,
        "enforce_normal_pass_rate": sum(
            not row["enforce_blocked"] and not row["enforce_sanitized"] for row in normals
        )
        / denominator
        if denominator
        else None,
        "false_block_rate": sum(row["enforce_blocked"] for row in normals) / denominator
        if denominator
        else None,
        "false_sanitize_rate": sum(row["enforce_sanitized"] for row in normals)
        / denominator
        if denominator
        else None,
    }
    return EvaluationResult(metrics=[metric], predictions=predictions)


def write_non_interference_artifacts(output_dir: Path, result: EvaluationResult) -> list[Path]:
    metrics = output_dir / "weather_non_interference_metrics.csv"
    predictions = output_dir / "weather_non_interference_predictions.csv"
    write_csv(metrics, result.metrics)
    write_csv(predictions, result.predictions)
    return [metrics, predictions]

