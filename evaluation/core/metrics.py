from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any


def _ratio(numerator: float, denominator: float) -> float | None:
    return float(numerator) / float(denominator) if denominator else None


def binary(labels: Sequence[bool], predictions: Sequence[bool]) -> dict[str, Any]:
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions must have the same length")
    tp = sum(bool(gold) and bool(pred) for gold, pred in zip(labels, predictions, strict=True))
    tn = sum(not gold and not pred for gold, pred in zip(labels, predictions, strict=True))
    fp = sum(not gold and bool(pred) for gold, pred in zip(labels, predictions, strict=True))
    fn = sum(bool(gold) and not pred for gold, pred in zip(labels, predictions, strict=True))
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "samples": len(labels),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": _ratio(fp, fp + tn),
    }


def set_pr(gold: Iterable[str], predicted: Iterable[str]) -> tuple[float | None, float | None]:
    gold_set = set(gold)
    predicted_set = set(predicted)
    precision = _ratio(len(gold_set & predicted_set), len(predicted_set))
    recall = _ratio(len(gold_set & predicted_set), len(gold_set))
    return precision, recall


def multiclass(gold: Sequence[str], predicted: Sequence[str]) -> dict[str, Any]:
    if len(gold) != len(predicted):
        raise ValueError("gold and predicted must have the same length")
    labels = sorted(set(gold) | set(predicted))
    if not labels:
        return {"macro_f1": None, "micro_f1": None, "labels": []}
    per_label = []
    total_tp = total_fp = total_fn = 0
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, predicted, strict=True))
        fp = sum(g != label and p == label for g, p in zip(gold, predicted, strict=True))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted, strict=True))
        total_tp += tp
        total_fp += fp
        total_fn += fn
        denominator = 2 * tp + fp + fn
        per_label.append((2 * tp / denominator) if denominator else 0.0)
    micro_denominator = 2 * total_tp + total_fp + total_fn
    return {
        "macro_f1": sum(per_label) / len(per_label),
        "micro_f1": (2 * total_tp / micro_denominator) if micro_denominator else None,
        "labels": labels,
    }


def roc_auc(labels: Sequence[bool], scores: Sequence[float]) -> float | None:
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have the same length")
    positives = [score for label, score in zip(labels, scores, strict=True) if label]
    negatives = [score for label, score in zip(labels, scores, strict=True) if not label]
    if not positives or not negatives:
        return None
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            wins += 1.0 if positive > negative else 0.5 if positive == negative else 0.0
    return wins / (len(positives) * len(negatives))


def average_precision(labels: Sequence[bool], scores: Sequence[float]) -> float | None:
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have the same length")
    positive_count = sum(bool(label) for label in labels)
    if not positive_count:
        return None
    ranked = sorted(
        enumerate(zip(labels, scores, strict=True)),
        key=lambda item: (-float(item[1][1]), item[0]),
    )
    true_positives = 0
    precision_sum = 0.0
    for rank, (_, (label, _)) in enumerate(ranked, start=1):
        if label:
            true_positives += 1
            precision_sum += true_positives / rank
    return precision_sum / positive_count
