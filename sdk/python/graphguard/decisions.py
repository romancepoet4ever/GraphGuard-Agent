from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GuardDecision:
    action: str
    risk_score: float = 0.0
    risk_type: str = "none"
    severity: str = "none"
    reason: str = ""
    matched_rules: list[str] = field(default_factory=list)
    safe_content: str = ""
    metadata: dict = field(default_factory=dict)
    trace_events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)
