from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import networkx as nx

from src.adapters.security_trace_adapter import SecurityTraceAdapter
from src.agents.model_clients import ChatModelClient, ModelClientConfig
from src.detection.government_risk_engine import GovernmentRiskEngine


class DetectionAgentState(TypedDict, total=False):
    trace: dict[str, Any]
    graph: nx.DiGraph
    risk_report: dict[str, Any]
    method_results: dict[str, Any]
    model_report: str
    final_report: dict[str, Any]


class GraphGuardDetectionAgent:
    """LangGraph-style orchestrator for four-method security analysis."""

    def __init__(self, model_config: ModelClientConfig | None = None) -> None:
        self.adapter = SecurityTraceAdapter()
        self.risk_engine = GovernmentRiskEngine()
        self.model_client = ChatModelClient(model_config)
        self._compiled_graph = self._try_build_langgraph()

    def analyze(self, trace: dict[str, Any]) -> dict[str, Any]:
        state: DetectionAgentState = {"trace": trace}
        if self._compiled_graph is not None:
            state = self._compiled_graph.invoke(state)
        else:
            state = self._build_graph(state)
            state = self._run_four_methods(state)
            state = self._synthesize_report(state)
        return state["final_report"]

    def analyze_file(self, path: str | Path) -> dict[str, Any]:
        trace = self.adapter.load_security_trace(path)
        return self.analyze(trace)

    def _try_build_langgraph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            return None

        workflow = StateGraph(DetectionAgentState)
        workflow.add_node("build_graph", self._build_graph)
        workflow.add_node("run_four_methods", self._run_four_methods)
        workflow.add_node("synthesize_report", self._synthesize_report)
        workflow.add_edge(START, "build_graph")
        workflow.add_edge("build_graph", "run_four_methods")
        workflow.add_edge("run_four_methods", "synthesize_report")
        workflow.add_edge("synthesize_report", END)
        return workflow.compile()

    def _build_graph(self, state: DetectionAgentState) -> DetectionAgentState:
        trace = state["trace"]
        warnings = self.adapter.validate_trace(trace)
        if warnings:
            raise ValueError("; ".join(warnings))
        state["graph"] = self.adapter.trace_to_security_graph(trace)
        return state

    def _run_four_methods(self, state: DetectionAgentState) -> DetectionAgentState:
        graph = state["graph"]
        risk_report = self.risk_engine.analyze(graph)
        state["risk_report"] = risk_report
        state["method_results"] = self._summarize_methods(graph, risk_report)
        return state

    def _synthesize_report(self, state: DetectionAgentState) -> DetectionAgentState:
        trace = state["trace"]
        risk_report = state["risk_report"]
        method_results = state["method_results"]
        payload = {
            "trace_meta": {
                "trace_id": trace.get("trace_id"),
                "project": trace.get("project"),
                "scenario": trace.get("scenario"),
                "session_id": trace.get("session_id"),
            },
            "risk_report": risk_report,
            "method_results": method_results,
            "government_context": {
                "focus": "政务 AI Agent 安全观测、运行时防护和合规审计",
                "sensitive_assets": ["高敏证据", "个人信息", "密钥凭据", "裁判评分", "最终报告"],
            },
        }
        model_report = self.model_client.complete(_SYSTEM_PROMPT, payload)
        state["model_report"] = model_report
        state["final_report"] = {
            "trace_id": risk_report.get("trace_id") or trace.get("trace_id"),
            "project": trace.get("project", "unknown"),
            "scenario": trace.get("scenario", "unknown"),
            "provider": self.model_client.config.provider,
            "model": self.model_client.config.model,
            "risk_report": risk_report,
            "method_results": method_results,
            "agent_report": model_report,
            "recommended_actions": self._recommended_actions(risk_report),
        }
        return state

    def _summarize_methods(self, graph: nx.DiGraph, risk_report: dict[str, Any]) -> dict[str, Any]:
        risk_score = float(risk_report.get("risk_score", 0.0) or 0.0)
        risk_path = risk_report.get("risk_path") or []
        matched_rules = risk_report.get("matched_rules") or []
        source_count = sum(1 for _, data in graph.nodes(data=True) if data.get("is_source"))
        sink_count = sum(1 for _, data in graph.nodes(data=True) if data.get("is_sink"))
        tagged_count = sum(1 for _, data in graph.nodes(data=True) if data.get("security_tags"))

        return {
            "graph_anomaly": {
                "status": "warning" if risk_path else "normal",
                "score": min(1.0, 0.25 + 0.12 * len(risk_path)) if risk_path else 0.0,
                "evidence": f"{graph.number_of_nodes()} nodes / {graph.number_of_edges()} edges; risk path length={len(risk_path)}",
            },
            "node_embedding": {
                "status": "warning" if tagged_count else "normal",
                "score": min(1.0, tagged_count / max(1, graph.number_of_nodes())),
                "evidence": f"{tagged_count} nodes contain security tags.",
            },
            "taint_analysis": {
                "status": "critical" if risk_path else "normal",
                "score": risk_score if risk_path else 0.0,
                "evidence": f"{source_count} source nodes, {sink_count} sink nodes, path={risk_path}",
            },
            "rule_engine": {
                "status": "warning" if matched_rules else "normal",
                "score": risk_score if matched_rules else 0.0,
                "evidence": f"matched_rules={matched_rules}",
            },
        }

    def _recommended_actions(self, risk_report: dict[str, Any]) -> list[dict[str, str]]:
        action = risk_report.get("recommended_action") or "allow"
        base = [
            {"action": "audit_log", "description": "保留 Trace、风险路径、命中规则和模型报告，便于政务审计追溯。"},
        ]
        if action in {"block_sensitive_content", "block", "sanitize"}:
            base.insert(0, {"action": str(action), "description": "对到达用户可见 sink 的高敏内容执行阻断或脱敏。"})
            base.append({"action": "isolate_context", "description": "隔离不可信输入对证据检索、评分和报告节点的影响。"})
        return base


_SYSTEM_PROMPT = """你是 GraphGuard-Agent 的政务智能体安全检测 Agent。
你会综合四种检测方法：图异动检测、节点嵌入检测、污点传播分析、规则引擎。
请输出面向安全人员和政务业务人员的中文风险报告，强调风险路径、命中规则、合规依据和处置建议。
不要泄露 API Key、密钥、原始高敏证据或完整个人信息。"""
