from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TraceEvent:
    event_id: str
    trace_id: str
    session_id: str
    round_idx: int
    seq: int
    event_type: str
    timestamp: str
    node_id: str | None = None
    parent_node_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "round_idx": self.round_idx,
            "seq": self.seq,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "parent_node_id": self.parent_node_id,
            "payload": self.payload,
            "metadata": self.metadata,
        }
