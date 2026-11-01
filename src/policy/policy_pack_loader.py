from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ALIASES = {"default": "generic_default", "gov_default": "generic_default",
           "government_agent": "generic_default", "government_weather": "generic_default"}


@dataclass(frozen=True)
class PolicyPackDefinition:
    name: str
    version: str
    root: Path
    rules: tuple[dict[str, Any], ...]

    @property
    def rules_path(self) -> Path:
        return self.root / "rules.yaml"


class PolicyPackLoader:
    def __init__(self, config_root: str | Path | None = None) -> None:
        repository = Path(__file__).resolve().parents[2]
        self.config_root = Path(config_root) if config_root else repository / "config" / "policy_packs"
        self.legacy_government_rules = repository / "config" / "government_rules.yaml"

    @staticmethod
    def normalize(name: str | None) -> str:
        normalized = str(name or "government_agent").strip().lower()
        return ALIASES.get(normalized, normalized)

    def load(self, name: str | None) -> PolicyPackDefinition:
        normalized = self.normalize(name)
        pack_root = self.config_root / normalized
        rules_path = pack_root / "rules.yaml"
        if normalized == "government_agent" and not rules_path.exists() and self.legacy_government_rules.exists():
            rules_path = self.legacy_government_rules
            pack_root = rules_path.parent
        if not rules_path.exists():
            available = ", ".join(self.available()) or "none"
            raise ValueError(f"Unknown GraphGuard policy pack '{name}'. Available packs: {available}")
        with rules_path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        return PolicyPackDefinition(
            name=normalized,
            version=str(payload.get("version") or "legacy"),
            root=pack_root,
            rules=tuple(payload.get("rules") or ()),
        )

    def available(self) -> tuple[str, ...]:
        if not self.config_root.exists():
            return ()
        return tuple(sorted(path.name for path in self.config_root.iterdir() if (path / "rules.yaml").is_file()))
