from __future__ import annotations

import time
from typing import Any

from graphguard.context import pop_node, push_node


class Span:
    def __init__(self, client, name: str, node_type: str, attributes: dict[str, Any]) -> None:
        self.client, self.name, self.node_type, self.attributes = client, name, node_type, attributes
        self.node_id: str | None = None
        self.output_summary: Any = None
        self.metadata: dict[str, Any] = {}
        self.started = 0.0

    def __enter__(self):
        self.started = time.perf_counter()
        self.node_id = self.client.start_span(name=self.name, node_type=self.node_type, **self.attributes)
        push_node(self.node_id)
        return self

    def set_output_summary(self, value: Any) -> None:
        self.output_summary = value

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def __exit__(self, exc_type, exc, tb):
        pop_node()
        if exc is not None:
            self.client.fail_span(self.node_id, exc, duration_ms=int((time.perf_counter() - self.started) * 1000))
        else:
            self.client.complete_span(self.node_id, output=self.output_summary,
                                      metadata=self.metadata, duration_ms=int((time.perf_counter() - self.started) * 1000))
        return False


class AsyncSpan(Span):
    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb):
        return self.__exit__(exc_type, exc, tb)
