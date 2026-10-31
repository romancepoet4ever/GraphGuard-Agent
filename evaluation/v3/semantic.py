from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from evaluation.core.io import write_csv, write_json


class SemanticProvider(Protocol):
    name: str

    def classify(self, text: str, *, temperature: float) -> dict[str, Any]: ...


def evaluate_semantic(
    output_dir: Path,
    *,
    provider: SemanticProvider | None = None,
    validation_cases: list[dict[str, Any]] | None = None,
    test_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate only an explicitly supplied real provider; never silently fall back."""

    output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "provider": getattr(provider, "name", None),
        "temperature": 0,
        "threshold_selected_on": "validation",
        "fallback_used": False,
        "local_node_embedding_detector_is_semantic_provider": False,
    }
    config_path = output_dir / "weather_semantic_model_config.json"
    cache_path = output_dir / "weather_semantic_model_cache.json"
    metrics_path = output_dir / "weather_semantic_metrics.csv"
    predictions_path = output_dir / "weather_semantic_predictions.csv"
    if provider is None:
        reason = "No explicit real GraphGuard semantic provider is configured."
        write_json(config_path, {**config, "status": "BLOCKED_EXTERNAL", "reason": reason})
        write_json(cache_path, {"status": "BLOCKED_EXTERNAL", "entries": {}})
        write_csv(
            metrics_path,
            [
                {
                    "method": "semantic",
                    "status": "BLOCKED_EXTERNAL",
                    "executed_samples": 0,
                    "reason": reason,
                }
            ],
        )
        write_csv(
            predictions_path,
            [
                {
                    "status": "BLOCKED_EXTERNAL",
                    "executed_samples": 0,
                    "reason": reason,
                }
            ],
        )
        return {
            "status": "BLOCKED_EXTERNAL",
            "executed_samples": 0,
            "reason": reason,
            "config": config,
            "artifacts": [str(config_path), str(cache_path), str(metrics_path), str(predictions_path)],
        }

    # A provider is never inferred from environment credentials. The formal V3 run therefore
    # reaches this branch only when a caller supplies a concrete, already configured adapter.
    raise NotImplementedError("Explicit semantic provider adapters are not available in this build")

