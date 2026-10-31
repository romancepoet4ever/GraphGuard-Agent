from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceNode:
    id: str
    label: str
    node_type: str
    agent: str = "system"
    content_hash: str = ""
    raw_content: str = ""
    display_content: str = ""
    trust_level: str = "trusted"
    sensitivity: str = "public"
    visibility: str = "internal_only"
    stage: str = "runtime"
    security_tags: list[str] = field(default_factory=list)
    policy_refs: list[str] = field(default_factory=list)
    is_source: bool = False
    is_sink: bool = False
    risk_score: float = 0.0
    risk_reason: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class TraceEdge:
    source: str
    target: str
    edge_type: str = "control_flow"
    taint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class SecurityTrace:
    trace_id: str
    project: str
    scenario: str
    session_id: str
    created_at: str
    source: str = "sdk"
    round_idx: int = 0
    nodes: list[TraceNode] = field(default_factory=list)
    edges: list[TraceEdge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "project": self.project,
            "scenario": self.scenario,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "source": self.source,
            "round_idx": self.round_idx,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": self.metadata,
        }
