from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

FORBIDDEN_INPUT_KEYS = {
    "attack",
    "is_attack",
    "positive",
    "expected_risk_types",
    "expected_attack_state",
    "expected_action",
    "expected_path_nodes",
    "ground_truth_path",
    "gold_label",
    "gold_path",
    "gold_annotations",
    "gold_risk_type",
}


@dataclass(frozen=True)
class ObservableCase:
    case_id: str
    source: str
    task: str
    split: str
    family: str
    input_text: str
    external_content: str | None
    scenario_spec: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoldAnnotation:
    case_id: str
    positive: bool
    risk_types: list[str]
    attack_state: str
    paths: list[list[str]]
    anomaly_types: list[str]
    action_enforce: str
    rule_ids: list[str] = field(default_factory=list)
    target_nodes: list[str] = field(default_factory=list)
    target_edges: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationResult:
    metrics: list[dict[str, Any]]
    predictions: list[dict[str, Any]]
    status: str = "completed"
    limitations: list[str] = field(default_factory=list)


def assert_no_gold(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if (
                normalized in FORBIDDEN_INPUT_KEYS
                or normalized.startswith(("gold_", "expected_"))
            ):
                raise AssertionError(f"forbidden evaluation label at {path}.{key}")
            assert_no_gold(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_gold(child, f"{path}[{index}]")
