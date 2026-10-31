from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import networkx as nx
import yaml

from src.defense.gov_audit_logger import GovAuditLogger
from src.detection.rule_engine import RuleEngine
from src.detection.taint_analysis import TaintAnalyzer
from src.policy.data_classifier import DataClassifier
from src.policy.policy_matcher import PolicyMatcher
from src.policy.policy_pack_loader import PolicyPackLoader
from src.policy.process_constraint_checker import ProcessConstraintChecker

SEVERITY_WEIGHT = {
    "low": 0.25,
    "medium": 0.5,
    "high": 0.8,
    "critical": 1.0,
}


class GovernmentRiskEngine:
    """Government-scenario risk engine built on top of the generic AGS detectors."""

    def __init__(
        self,
        rules_path: str | Path | None = None,
        *,
        policy_pack: str | None = None,
    ) -> None:
        self.policy_loader = PolicyPackLoader()
        self.requested_policy_pack = policy_pack
        self._custom_rules = rules_path is not None
        self.rules_path = Path(rules_path) if rules_path else Path()
        self.rules = self._load_rules(self.rules_path) if rules_path else []
        self.policy_pack_name = "custom" if rules_path else self.policy_loader.normalize(policy_pack)
        self.generic_rule_engine = RuleEngine()
        self.taint_analyzer = TaintAnalyzer()
        self.data_classifier = DataClassifier()
        self.process_checker = ProcessConstraintChecker()
        self.policy_matcher = PolicyMatcher()
        self.audit_logger = GovAuditLogger()

    def analyze(self, graph: nx.DiGraph, *, write_audit: bool = True) -> dict[str, Any]:
        if not self._custom_rules:
            metadata = dict(graph.graph.get("metadata") or {})
            selected = self.requested_policy_pack or metadata.get("policy_pack") or graph.graph.get("policy_pack") or "gov_default"
            pack = self.policy_loader.load(str(selected))
            self.policy_pack_name = pack.name
            self.rules_path = pack.rules_path
            self.rules = list(pack.rules)

        is_government = self.policy_pack_name in {"government_agent", "government_weather", "custom"}
        if is_government:
            self._enrich_graph(graph)
        matched_rules: list[dict[str, Any]] = []
        risk_paths: list[list[str]] = []
        node_scores: dict[str, float] = {}
        process_violations: list[dict[str, Any]] = []

        if is_government:
            for node_id, data in graph.nodes(data=True):
                violation = self.process_checker.check_node(data)
                if violation:
                    process_violations.append({"node_id": str(node_id), **violation})

        generic_matches = self._generic_text_matches(graph)
        if generic_matches:
            matched_rules.append(
                {
                    "id": "AGS-GENERIC-001",
                    "name": "通用提示注入/工具滥用模式",
                    "type": "generic_agent_security",
                    "severity": "medium",
                    "evidence": generic_matches,
                }
            )

        for rule in self.rules:
            hit = self._evaluate_rule(graph, rule)
            if not hit:
                continue
            matched_rules.append(hit["rule"])
            if hit.get("path"):
                risk_paths.append(hit["path"])
            for node_id in hit.get("nodes", []):
                node_scores[node_id] = max(
                    node_scores.get(node_id, 0.0),
                    SEVERITY_WEIGHT.get(hit["rule"].get("severity", "medium"), 0.5),
                )

        try:
            taint_report = self.taint_analyzer.analyze(graph)
        except Exception:
            taint_report = {}

        max_rule_score = max(
            [SEVERITY_WEIGHT.get(rule.get("severity", "medium"), 0.5) for rule in matched_rules],
            default=0.0,
        )
        risk_paths = self._dedupe_paths(risk_paths)
        path_bonus = min(0.15, 0.03 * len(risk_paths))
        risk_score = min(1.0, max_rule_score + path_bonus)

        best_path = self._select_best_path(graph, risk_paths)
        scenario = str(graph.graph.get("scenario", ""))
        risk_type = self._primary_risk_type(matched_rules, scenario)
        recommended_action = self._recommended_action(matched_rules, risk_score)
        repair_suggestions = self._repair_suggestions(graph, best_path, matched_rules)
        policy_evidence = self.policy_matcher.evidence_for_rules(matched_rules) if is_government else []

        report = {
            "trace_id": str(graph.graph.get("trace_id", "")),
            "session_id": str(graph.graph.get("session_id", "")),
            "scenario": scenario,
            "is_attack": risk_score >= 0.5,
            "risk_score": float(risk_score),
            "risk_type": risk_type,
            "severity": self._max_severity(matched_rules),
            "risk_path": best_path,
            "risk_paths": risk_paths,
            "matched_rules": matched_rules,
            "policy_evidence": policy_evidence,
            "process_violations": process_violations,
            "node_risk_scores": node_scores,
            "explanation": self._build_explanation(risk_type, matched_rules, best_path),
            "recommended_action": recommended_action,
            "repair_suggestions": repair_suggestions,
            "taint_report": taint_report,
            "audit_id": "",
            "audit_record": {},
            "debug": {
                "policy_pack": self.policy_pack_name,
                "rules_path": str(self.rules_path),
                "num_rules": len(self.rules),
                "num_nodes": graph.number_of_nodes(),
                "num_edges": graph.number_of_edges(),
            },
        }
        if report["is_attack"] and write_audit:
            audit_record = self.audit_logger.build_record(graph, report)
            report["audit_id"] = self.audit_logger.write(audit_record)
            report["audit_record"] = audit_record
        return report

    @staticmethod
    def _dedupe_paths(paths: list[list[str]]) -> list[list[str]]:
        seen: set[tuple[str, ...]] = set()
        result: list[list[str]] = []
        for path in paths:
            key = tuple(str(node) for node in path)
            if key and key not in seen:
                seen.add(key)
                result.append(list(key))
        return result

    def analyze_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        from src.adapters.government_agent_adapter import GovernmentAgentTraceAdapter

        adapter = GovernmentAgentTraceAdapter()
        return self.analyze(adapter.trace_to_networkx(trace))

    def _load_rules(self, rules_path: Path) -> list[dict[str, Any]]:
        if not rules_path.exists():
            return []
        with rules_path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        return list(payload.get("rules") or [])

    def _generic_text_matches(self, graph: nx.DiGraph) -> list[dict[str, Any]]:
        matches = []
        for node_id, data in graph.nodes(data=True):
            text = self._node_text(data)
            if not text:
                continue
            result = self.generic_rule_engine.check(text)
            if result.get("is_malicious"):
                matches.append(
                    {
                        "node_id": str(node_id),
                        "score": result.get("score", 0.0),
                        "matches": result.get("matches", []),
                    }
                )
        return matches

    def _evaluate_rule(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        rule_type = str(rule.get("type") or "")
        if rule_type == "prompt_injection":
            return self._match_prompt_injection(graph, rule)
        if rule_type == "evidence_leakage":
            return self._match_evidence_leakage(graph, rule)
        if rule_type == "referee_contamination":
            return self._match_referee_contamination(graph, rule)
        if rule_type == "report_pollution":
            return self._match_report_pollution(graph, rule)
        if rule_type == "knowledge_poisoning":
            return self._match_knowledge_poisoning(graph, rule)
        if rule_type == "unauthorized_retrieval":
            return self._match_unauthorized_retrieval(graph, rule)
        if rule_type == "role_escape":
            return self._match_role_escape(graph, rule)
        if rule_type == "personal_information_leakage":
            return self._match_personal_information_leakage(graph, rule)
        if rule_type == "sensitive_data_leakage":
            return self._match_sensitive_data_leakage(graph, rule)
        if rule_type == "tool_overreach":
            return self._match_tool_overreach(graph, rule)
        if rule_type == "missing_provenance":
            return self._match_missing_provenance(graph, rule)
        return None

    def _match_tool_overreach(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = self._untrusted_sources(graph)
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if str(data.get("node_type") or data.get("type")) == "tool_call"
            and (
                "tool_denied" in set(data.get("security_tags") or [])
                or bool((data.get("metadata") or {}).get("gateway_denied"))
                or bool((data.get("metadata") or {}).get("blocked"))
            )
        ]
        path = self._first_path(graph, sources, sinks)
        if path:
            return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        return None

    @staticmethod
    def _match_missing_provenance(graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        hits = []
        for node_id, data in graph.nodes(data=True):
            node_type = str(data.get("node_type") or data.get("type") or "")
            metadata = dict(data.get("metadata") or {})
            tags = set(data.get("security_tags") or [])
            protected = node_type == "final_report" or bool(metadata.get("protected_sink"))
            missing = (
                "missing_provenance" in tags
                or metadata.get("provenance_present") is False
                or metadata.get("provenance_status") in {"missing", "absent"}
            )
            if protected and missing:
                hits.append(str(node_id))
        if hits:
            return {"rule": GovernmentRiskEngine._public_rule(rule), "path": [], "nodes": hits}
        return None

    def _match_sensitive_data_leakage(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if bool(data.get("is_source"))
            and str(data.get("sensitivity", "")).lower()
            in {"sensitive", "highly_sensitive", "secret", "secret_like", "confidential"}
        ]
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if bool(data.get("is_sink")) or str(data.get("visibility", "")).lower() == "user_visible"
        ]
        path = self._first_path(graph, sources, sinks)
        if path and not self._path_contains_type(graph, path, {"sanitizer"}):
            return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        return None

    def _match_prompt_injection(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = []
        patterns = [re.compile(pattern, re.I) for pattern in rule.get("patterns", [])]
        source_types = set(rule.get("source_types", []))
        for node_id, data in graph.nodes(data=True):
            if str(data.get("node_type") or data.get("type")) not in source_types:
                continue
            text = self._node_text(data)
            if any(pattern.search(text) for pattern in patterns):
                sources.append(str(node_id))

        if not sources:
            return None

        sinks = self._sink_nodes(graph, set(rule.get("sink_types", [])))
        path = self._first_path(graph, sources, sinks)
        nodes = set(sources)
        if path:
            nodes.update(path)
        return {"rule": self._public_rule(rule), "path": path, "nodes": sorted(nodes)}

    def _match_evidence_leakage(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if (
                "sensitive_evidence" in set(data.get("security_tags") or [])
                or str(data.get("sensitivity", "")).lower() == "highly_sensitive"
            )
        ]
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if bool(data.get("is_sink")) or str(data.get("visibility", "")).lower() == "user_visible"
        ]
        for path in self._all_short_paths(graph, sources, sinks):
            if not self._path_has_allowed_stage(graph, path, {"strike", "consolidate"}):
                return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        return None

    def _match_referee_contamination(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = self._untrusted_sources(graph)
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if str(data.get("agent")) == "referee"
            or str(data.get("node_type") or data.get("type")) in {"referee_scoring", "decision"}
        ]
        for path in self._all_short_paths(graph, sources, sinks):
            if not self._path_contains_type(graph, path, {"sanitizer"}):
                return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        return None

    def _match_report_pollution(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if (
                "unverified_claim" in set(data.get("security_tags") or [])
                or "fake_event" in set(data.get("security_tags") or [])
            )
        ]
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if str(data.get("node_type") or data.get("type")) in {"final_report", "user_visible_sink"}
        ]
        path = self._first_path(graph, sources, sinks)
        if path:
            return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        return None

    def _match_knowledge_poisoning(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if "knowledge_poisoning_candidate" in set(data.get("security_tags") or [])
        ]
        sink_types = set(rule.get("sink_types") or {"suspect_generation", "referee_scoring", "final_report"})
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if str(data.get("node_type") or data.get("type")) in sink_types
        ]
        path = self._first_path(graph, sources, sinks)
        if path:
            return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        return None

    def _match_unauthorized_retrieval(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if str(data.get("agent")) in {"trainee", "user"} and bool(data.get("is_source"))
        ]
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if str(data.get("node_type") or data.get("type")) == "evidence_retrieval"
            and str(data.get("sensitivity")) in {"highly_sensitive", "secret_like"}
        ]
        path = self._first_path(graph, sources, sinks)
        if path:
            return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        return None

    def _match_role_escape(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        patterns = [re.compile(pattern, re.I) for pattern in rule.get("patterns", [])]
        hits = []
        for node_id, data in graph.nodes(data=True):
            if str(data.get("node_type") or data.get("type")) != "user_input":
                continue
            text = self._node_text(data)
            if any(pattern.search(text) for pattern in patterns):
                hits.append(str(node_id))
        if hits:
            return {"rule": self._public_rule(rule), "path": [], "nodes": hits}
        return None

    def _match_personal_information_leakage(self, graph: nx.DiGraph, rule: dict[str, Any]) -> dict[str, Any] | None:
        sources = []
        input_hits = []
        for node_id, data in graph.nodes(data=True):
            if "personal_information" not in set(data.get("security_tags") or []):
                continue
            node_key = str(node_id)
            sources.append(node_key)
            node_type = str(data.get("node_type") or data.get("type") or "")
            if node_type in {"user_input", "external_input"}:
                input_hits.append(node_key)
        # For propagated leakage, a graph path alone does not prove that the
        # value survived generation: the user-visible output must itself still
        # classify as PII. Direct unredacted PII in an input is reported
        # separately through ``input_hits`` without treating it as malicious
        # control-flow influence over referee/report nodes.
        sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if "personal_information" in set(data.get("security_tags") or [])
            and str(data.get("node_type") or data.get("type") or "") not in {"user_input", "external_input"}
            and (bool(data.get("is_sink")) or str(data.get("visibility", "")).lower() == "user_visible")
        ]
        for path in self._all_short_paths(graph, sources, sinks):
            if not self._path_contains_type(graph, path, {"sanitizer"}):
                return {"rule": self._public_rule(rule), "path": path, "nodes": path}
        if input_hits:
            return {"rule": self._public_rule(rule), "path": [], "nodes": sorted(input_hits)}
        return None

    def _untrusted_sources(self, graph: nx.DiGraph) -> list[str]:
        sources = []
        for node_id, data in graph.nodes(data=True):
            trust = str(data.get("trust_level") or data.get("trust") or "").lower()
            tags = set(data.get("security_tags") or [])
            if tags.intersection({"prompt_injection_candidate", "knowledge_poisoning_candidate"}):
                sources.append(str(node_id))
                continue
            if bool(data.get("is_source")) and trust in {"untrusted", "compromised", "contaminated", "red", "black"}:
                sources.append(str(node_id))
        return sources

    def _sink_nodes(self, graph: nx.DiGraph, sink_types: set[str]) -> list[str]:
        return [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if bool(data.get("is_sink")) or str(data.get("node_type") or data.get("type")) in sink_types
        ]

    def _first_path(self, graph: nx.DiGraph, sources: list[str], sinks: list[str]) -> list[str]:
        paths = self._all_short_paths(graph, sources, sinks)
        return paths[0] if paths else []

    def _all_short_paths(self, graph: nx.DiGraph, sources: list[str], sinks: list[str]) -> list[list[str]]:
        paths = []
        for source in sources:
            for sink in sinks:
                if source == sink:
                    continue
                try:
                    if nx.has_path(graph, source, sink):
                        paths.append([str(node) for node in nx.shortest_path(graph, source, sink)])
                except Exception:
                    continue
        return sorted(paths, key=len)

    def _select_best_path(self, graph: nx.DiGraph, rule_paths: list[list[str]]) -> list[str]:
        """Prefer a complete source-to-visible-sink propagation path.

        Individual rules often return only one segment of an incident, for example
        user_input -> evidence_retrieval or evidence_retrieval -> user_visible_sink.
        The report should surface the end-to-end path that best explains impact.
        """
        candidates = [path for path in rule_paths if path]
        sources = self._untrusted_sources(graph)
        visible_sinks = [
            str(node_id)
            for node_id, data in graph.nodes(data=True)
            if str(data.get("visibility", "")).lower() == "user_visible"
            and (bool(data.get("is_sink")) or str(data.get("node_type") or data.get("type")) in {"user_visible_sink", "final_report"})
        ]
        candidates.extend(self._all_short_paths(graph, sources, visible_sinks))
        if not candidates:
            return []

        def path_score(path: list[str]) -> tuple[int, int]:
            nodes = [graph.nodes[node_id] for node_id in path]
            sink = nodes[-1]
            score = 0
            if str(sink.get("visibility", "")).lower() == "user_visible":
                score += 10
            if any(
                str(node.get("sensitivity", "")).lower() in {"sensitive", "highly_sensitive", "secret_like"}
                or "sensitive_evidence" in set(node.get("security_tags") or [])
                for node in nodes
            ):
                score += 6
            if any(str(node.get("trust_level", "")).lower() in {"untrusted", "compromised", "contaminated"} for node in nodes):
                score += 3
            if any(str(node.get("node_type") or node.get("type")) in {"strategy_decision", "decision"} for node in nodes):
                score += 2
            return score, len(path)

        return max(candidates, key=path_score)

    @staticmethod
    def _path_contains_type(graph: nx.DiGraph, path: list[str], node_types: set[str]) -> bool:
        for node_id in path:
            node_type = str(graph.nodes[node_id].get("node_type") or graph.nodes[node_id].get("type") or "")
            if node_type in node_types:
                return True
        return False

    @staticmethod
    def _path_has_allowed_stage(graph: nx.DiGraph, path: list[str], allowed_stages: set[str]) -> bool:
        for node_id in path:
            stage = str(graph.nodes[node_id].get("stage") or "")
            if stage in allowed_stages:
                return True
        return False

    @staticmethod
    def _node_text(data: dict[str, Any]) -> str:
        return "\n".join(
            str(data.get(key) or "")
            for key in ["raw_content", "display_content", "content", "label"]
        )

    @staticmethod
    def _public_rule(rule: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": rule.get("id", ""),
            "name": rule.get("name", ""),
            "type": rule.get("type", ""),
            "severity": rule.get("severity", "medium"),
            "action": rule.get("action", "review"),
            "policy_refs": list(rule.get("policy_refs") or []),
        }

    @staticmethod
    def _primary_risk_type(matched_rules: list[dict[str, Any]], scenario: str = "") -> str:
        if not matched_rules:
            return "none"
        scenario_type = {
            "prompt_injection": "prompt_injection",
            "evidence_leakage": "evidence_leakage",
            "referee_contamination": "referee_contamination",
            "report_pollution": "report_pollution",
            "knowledge_poisoning": "knowledge_poisoning",
            "knowledge_poisoning_offline": "knowledge_poisoning",
            "personal_information_leakage": "personal_information_leakage",
        }.get(scenario)
        if scenario_type and any(rule.get("type") == scenario_type for rule in matched_rules):
            return scenario_type
        ordered = sorted(
            matched_rules,
            key=lambda item: SEVERITY_WEIGHT.get(item.get("severity", "medium"), 0.5),
            reverse=True,
        )
        return str(ordered[0].get("type") or "unknown")

    @staticmethod
    def _max_severity(matched_rules: list[dict[str, Any]]) -> str:
        if not matched_rules:
            return "none"
        return str(
            max(
                matched_rules,
                key=lambda item: SEVERITY_WEIGHT.get(item.get("severity", "medium"), 0.5),
            ).get("severity", "medium")
        )

    @staticmethod
    def _recommended_action(matched_rules: list[dict[str, Any]], risk_score: float) -> str:
        if matched_rules:
            ordered = sorted(
                matched_rules,
                key=lambda item: SEVERITY_WEIGHT.get(item.get("severity", "medium"), 0.5),
                reverse=True,
            )
            return str(ordered[0].get("action") or "review")
        if risk_score >= 0.8:
            return "block_or_sanitize"
        if risk_score >= 0.5:
            return "sanitize_or_isolate"
        return "allow"

    @staticmethod
    def _build_explanation(risk_type: str, matched_rules: list[dict[str, Any]], path: list[str]) -> str:
        if not matched_rules:
            return "未发现高风险传播路径，当前 trace 可作为正常流程基线。"
        rule_names = "；".join(f"{rule.get('id')} {rule.get('name')}" for rule in matched_rules)
        path_text = " -> ".join(path) if path else "未形成完整传播路径"
        return (
            f"命中规则：{rule_names}。"
            f"系统不是仅凭关键词判定，而是结合节点风险与执行图路径传播：{path_text}。"
            f"综合判断风险类型为 {risk_type}。"
        )

    @staticmethod
    def _repair_suggestions(
        graph: nx.DiGraph,
        path: list[str],
        matched_rules: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        suggestions = []
        for rule in matched_rules:
            action = rule.get("action", "review")
            if action == "block_sensitive_content":
                suggestions.append({"action": action, "description": "在敏感证据进入用户可见输出前执行脱敏或阻断。"})
            elif action == "isolate_referee_context":
                suggestions.append({"action": action, "description": "隔离裁判评分上下文，禁止用户原始指令直接进入裁判节点。"})
            elif action == "downgrade_or_label_unverified_claim":
                suggestions.append({"action": action, "description": "将未证实陈述标注为单方说法，禁止直接写入事实结论。"})
            elif action == "quarantine_poisoned_material":
                suggestions.append({"action": action, "description": "隔离疑似投毒材料，检索前先做指令型文本剥离和来源校验。"})
            elif action == "deny_retrieval_and_log":
                suggestions.append({"action": action, "description": "拒绝越权证据检索，记录访问主体、目标证据级别和风险路径。"})
            elif action == "mask_personal_information":
                suggestions.append({"action": action, "description": "对姓名、手机号、身份证号、地址、金额等个人信息进行脱敏或摘要化输出。"})
            elif action == "refuse_and_restore_role":
                suggestions.append({"action": action, "description": "拒绝角色逃逸请求，恢复系统角色和政务训练边界。"})
            elif action == "block_or_sanitize":
                suggestions.append({"action": action, "description": "阻断越权请求，或插入 sanitizer 剥离指令型文本。"})
            else:
                suggestions.append({"action": action, "description": "进入人工复核，或按规则执行最小化输出。"})

        if path and len(path) >= 2:
            suggestions.append(
                {
                    "action": "insert_sanitizer",
                    "description": f"建议在 {path[0]} -> {path[1]} 之间插入 sanitizer，阻断不可信影响继续传播。",
                    "edge": [path[0], path[1]],
                }
            )
        return suggestions

    def _enrich_graph(self, graph: nx.DiGraph) -> None:
        for node_id, data in list(graph.nodes(data=True)):
            enriched = self.data_classifier.classify_node({"id": str(node_id), **dict(data)})
            graph.nodes[node_id].update(enriched)
