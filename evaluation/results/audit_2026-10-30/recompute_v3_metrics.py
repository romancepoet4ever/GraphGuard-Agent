"""Independently recompute frozen V3 binary metrics from predictions and gold.

This audit helper reads only case IDs, gold labels/risk types, and the
``predicted_positive`` columns. It does not read the recorded metric CSVs.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

METHOD_FILES = {
    "rule": "weather_rule_predictions.csv",
    "taint": "weather_taint_path_predictions.csv",
    "anomaly": "weather_anomaly_predictions.csv",
    "fusion": "weather_fusion_predictions.csv",
}


def binary_metrics(gold: dict[str, bool], predicted: dict[str, bool]) -> dict[str, float | int]:
    if set(gold) != set(predicted):
        missing = sorted(set(gold) - set(predicted))
        extra = sorted(set(predicted) - set(gold))
        raise ValueError(f"case-id mismatch: missing={missing[:5]} extra={extra[:5]}")
    tp = sum(gold[key] and predicted[key] for key in gold)
    tn = sum(not gold[key] and not predicted[key] for key in gold)
    fp = sum(not gold[key] and predicted[key] for key in gold)
    fn = sum(gold[key] and not predicted[key] for key in gold)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "n": len(gold),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
    }


def overlap_signatures(predictions: dict[str, dict[str, bool]]) -> dict[str, int]:
    methods = ("rule", "taint", "anomaly")
    case_ids = set(predictions[methods[0]])
    if any(set(predictions[method]) != case_ids for method in methods[1:]):
        raise ValueError("method prediction files do not contain the same case IDs")
    counts = Counter(
        "".join("1" if predictions[method][case_id] else "0" for method in methods)
        for case_id in sorted(case_ids)
    )
    return dict(sorted(counts.items()))


def _read_predictions(path: Path) -> dict[str, bool]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {
            row["case_id"]: row["predicted_positive"].strip().lower() == "true"
            for row in csv.DictReader(stream)
        }


def recompute(repo_root: Path) -> dict[str, Any]:
    result_dir = repo_root / "evaluation" / "results" / "v3"
    gold_path = repo_root / "evaluation" / "datasets" / "v3" / "weather_gold_annotations.jsonl"
    detailed_gold: dict[str, dict[str, Any]] = {}
    with gold_path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            detailed_gold[str(row["case_id"])] = row
    predictions = {
        method: _read_predictions(result_dir / filename)
        for method, filename in METHOD_FILES.items()
    }
    evaluated_ids = set(predictions["fusion"])
    labels = {case_id: bool(detailed_gold[case_id]["positive"]) for case_id in evaluated_ids}
    metrics = {method: binary_metrics(labels, rows) for method, rows in predictions.items()}

    risk_counts: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {"detected": 0, "samples": 0}
    )
    for case_id in sorted(evaluated_ids):
        row = detailed_gold[case_id]
        if not row["positive"]:
            continue
        for risk_type in row.get("risk_types", []):
            risk_counts[risk_type]["samples"] += 1
            risk_counts[risk_type]["detected"] += int(predictions["fusion"][case_id])
    risks = {
        risk: {
            **counts,
            "recall": counts["detected"] / counts["samples"],
        }
        for risk, counts in sorted(risk_counts.items())
    }
    return {
        "source": {
            "gold": str(gold_path.relative_to(repo_root)),
            "predictions": METHOD_FILES,
        },
        "metrics": metrics,
        "overlap_signatures_rule_taint_anomaly": overlap_signatures(predictions),
        "fusion_recall_by_risk": risks,
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    print(json.dumps(recompute(repo_root), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
