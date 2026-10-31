from __future__ import annotations

from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:  # pragma: no cover - optional integration dependency
    class BaseCallbackHandler:
        pass


class GraphGuardCallbackHandler(BaseCallbackHandler):
    """Capture LangChain run events as connected SecurityTrace nodes."""

    def __init__(self, client) -> None:
        self.client = client
        self._run_nodes: dict[str, str] = {}

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, **kwargs):
        return self._start_run(
            run_id,
            parent_run_id,
            label=self._serialized_name(serialized, "LangChain Chain"),
            node_type="chain_start",
            content=inputs,
            metadata={"event": "chain_start", "tags": kwargs.get("tags") or []},
        )

    def on_chain_end(self, outputs, *, run_id, parent_run_id=None, **kwargs):
        self._end_run(run_id, "chain_end", "LangChain Chain Result", outputs, parent_run_id)

    def on_chain_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        self._error_run(run_id, error, parent_run_id)

    def on_llm_start(self, serialized, prompts, *, run_id, parent_run_id=None, **kwargs):
        return self._start_run(
            run_id,
            parent_run_id,
            label=self._serialized_name(serialized, "LLM Call"),
            node_type="llm_call",
            content=prompts,
            metadata={"event": "llm_start", "invocation_params": kwargs.get("invocation_params") or {}},
        )

    def on_llm_end(self, response, *, run_id, parent_run_id=None, **kwargs):
        self._end_run(run_id, "agent_generation", "LLM Result", response, parent_run_id)

    def on_llm_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        self._error_run(run_id, error, parent_run_id)

    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, inputs=None, **kwargs):
        return self._start_run(
            run_id,
            parent_run_id,
            label=self._serialized_name(serialized, "Tool Call"),
            node_type="tool_call",
            content=inputs if inputs is not None else input_str,
            metadata={"event": "tool_start"},
        )

    def on_tool_end(self, output, *, run_id, parent_run_id=None, **kwargs):
        self._end_run(run_id, "tool_result", "Tool Result", output, parent_run_id)

    def on_tool_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        self._error_run(run_id, error, parent_run_id)

    def on_retriever_start(self, serialized, query, *, run_id, parent_run_id=None, **kwargs):
        return self._start_run(run_id, parent_run_id,
            label=self._serialized_name(serialized, "Retriever"), node_type="knowledge_retrieval",
            content=query, metadata={"event": "retriever_start", "tags": kwargs.get("tags") or [],
                                     "callback_metadata": kwargs.get("metadata") or {}})

    def on_retriever_end(self, documents, *, run_id, parent_run_id=None, **kwargs):
        self._end_run(run_id, "knowledge_retrieval", "Retriever Result", documents, parent_run_id)

    def on_retriever_error(self, error, *, run_id, parent_run_id=None, **kwargs):
        self._error_run(run_id, error, parent_run_id)

    def _start_run(
        self,
        run_id,
        parent_run_id,
        *,
        label: str,
        node_type: str,
        content: Any,
        metadata: dict[str, Any],
    ) -> str:
        run_key = str(run_id)
        node_id = self.client.start_node(
            label=label,
            node_type=node_type,
            agent="langchain",
            raw_content=self._summarize(content),
            display_content=self._summarize(content),
            trust_level="untrusted" if node_type == "chain_start" else "trusted",
            visibility="internal_only",
            metadata={"run_id": run_key, "parent_run_id": str(parent_run_id or ""), **metadata},
        )
        self._run_nodes[run_key] = node_id
        parent_node = self._run_nodes.get(str(parent_run_id)) if parent_run_id else None
        if parent_node:
            self.client.record_edge(parent_node, node_id, edge_type="calls")
        return node_id

    def _end_run(self, run_id, node_type: str, label: str, content: Any, parent_run_id=None) -> str:
        run_key = str(run_id)
        start_node = self._run_nodes.get(run_key)
        if start_node:
            self.client.complete_node(start_node, display_content=self._summarize(content),
                                      metadata={"output_summary": self._summarize(content), "completed_event": node_type})
            result_node = start_node
        else:
            result_node = self.client.record_node(label=label, node_type=node_type, agent="langchain",
                display_content=self._summarize(content), metadata={"orphan_completion": True})
        self._run_nodes.pop(run_key, None)
        return result_node

    def _error_run(self, run_id, error: BaseException, parent_run_id=None) -> str:
        run_key = str(run_id)
        start_node = self._run_nodes.get(run_key)
        if start_node:
            self.client.fail_node(start_node, error, metadata={"parent_run_id": str(parent_run_id or "")})
            error_node = start_node
        else:
            error_node = self.client.record_node(label="LangChain Error", node_type="error", agent="langchain",
                display_content=str(error)[:240], trust_level="untrusted", security_tags=["runtime_error"], risk_score=0.5)
        self._run_nodes.pop(run_key, None)
        return error_node

    @staticmethod
    def _serialized_name(serialized: Any, fallback: str) -> str:
        if isinstance(serialized, dict):
            return str(serialized.get("name") or serialized.get("id") or fallback)
        return fallback

    @staticmethod
    def _summarize(value: Any, limit: int = 500) -> str:
        text = repr(value)
        return text[:limit]


__all__ = ["GraphGuardCallbackHandler"]
