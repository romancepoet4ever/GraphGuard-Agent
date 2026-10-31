from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class GovPolicyLoader:
    def __init__(self, config_dir: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self.config_dir = Path(config_dir) if config_dir else root / "config" / "gov_policy"

    def load(self, name: str) -> dict[str, Any]:
        path = self.config_dir / name
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}

    def load_all(self) -> dict[str, Any]:
        return {
            "policy_index": self.load("policy_index.yaml"),
            "data_classification": self.load("data_classification.yaml"),
            "role_permissions": self.load("role_permissions.yaml"),
            "process_constraints": self.load("process_constraints.yaml"),
            "explanation_templates": self.load("explanation_templates.yaml"),
        }
