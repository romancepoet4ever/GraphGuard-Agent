from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from src.adapters.government_agent_adapter import GovernmentAgentTraceAdapter


class SecurityTraceAdapter(GovernmentAgentTraceAdapter):
    """Generic SecurityTrace adapter for SDK, upload and offline demo traces."""

    def load_security_trace(self, trace_path: str | Path) -> dict[str, Any]:
        return self.load_trace(trace_path)

    def validate_trace_collect_errors(self, trace: dict[str, Any]) -> list[str]:
        try:
            self.validate_trace(trace)
            return []
        except Exception as exc:
            return [str(exc)]

    def trace_to_security_graph(self, trace: dict[str, Any]) -> nx.DiGraph:
        return self.trace_to_networkx(trace)


def load_security_trace(path: str | Path) -> dict[str, Any]:
    return SecurityTraceAdapter().load_security_trace(path)


def validate_trace(trace: dict[str, Any]) -> list[str]:
    return SecurityTraceAdapter().validate_trace_collect_errors(trace)


def trace_to_networkx(trace: dict[str, Any]) -> nx.DiGraph:
    return SecurityTraceAdapter().trace_to_security_graph(trace)
