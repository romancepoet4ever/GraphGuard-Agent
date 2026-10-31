from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from graphguard.context import parent_node, pop_node, push_node


class GraphGuardLangGraphHook:
    """Lightweight LangGraph node hook without taking over graph execution."""

    def __init__(self, client):
        self.client = client

    def record_node(self, name: str, state: dict | None = None, **attributes: Any) -> str:
        parent = parent_node()
        node_id = self.client.record_node(
            label=name,
            node_type=str(attributes.pop("node_type", "langgraph_node")),
            raw_content=str(state or {}),
            display_content=str(state or {})[:240],
            metadata={"integration": "langgraph"},
            **attributes,
        )
        if parent:
            self.client.record_edge(parent, node_id, edge_type="calls")
        return node_id

    @contextmanager
    def node(self, name: str, *, state: dict | None = None, **attributes: Any) -> Iterator[str]:
        parent = parent_node()
        node_id = self.client.start_node(
            label=name,
            node_type=str(attributes.pop("node_type", "langgraph_node")),
            raw_content=str(state or {}),
            display_content=str(state or {})[:240],
            metadata={"integration": "langgraph"},
            **attributes,
        )
        if parent:
            self.client.record_edge(parent, node_id, edge_type="calls")
        push_node(node_id)
        try:
            yield node_id
        except Exception as exc:
            self.client.fail_node(node_id, exc, metadata={"integration": "langgraph"})
            raise
        else:
            self.client.complete_node(node_id, metadata={"integration": "langgraph"})
        finally:
            pop_node()


__all__ = ["GraphGuardLangGraphHook"]
