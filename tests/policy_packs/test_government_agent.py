from __future__ import annotations

import networkx as nx

from src.detection.government_risk_engine import GovernmentRiskEngine


def test_government_agent_detects_evidence_leakage() -> None:
    graph = nx.DiGraph(trace_id="gov-leak", scenario="evidence_leakage")
    graph.add_node(
        "evidence",
        node_type="tool_result",
        sensitivity="highly_sensitive",
        security_tags=["sensitive_evidence"],
        is_source=True,
    )
    graph.add_node("sink", node_type="user_visible_sink", visibility="user_visible", is_sink=True)
    graph.add_edge("evidence", "sink")

    report = GovernmentRiskEngine(policy_pack="government_agent").analyze(graph, write_audit=False)

    assert any(rule["id"] == "GOV-LEAK-001" for rule in report["matched_rules"])
    assert report["risk_type"] == "evidence_leakage"


def test_government_agent_detects_referee_and_report_contamination() -> None:
    referee = nx.DiGraph(trace_id="gov-referee", scenario="referee_contamination")
    referee.add_node("input", node_type="user_input", trust_level="untrusted", is_source=True,
                     security_tags=["prompt_injection_candidate"])
    referee.add_node("judge", node_type="referee_scoring", agent="referee")
    referee.add_edge("input", "judge")
    referee_report = GovernmentRiskEngine(policy_pack="government_agent").analyze(referee, write_audit=False)
    assert any(rule["id"] == "GOV-JUDGE-001" for rule in referee_report["matched_rules"])

    report_graph = nx.DiGraph(trace_id="gov-report", scenario="report_pollution")
    report_graph.add_node("memory", node_type="memory_write", security_tags=["unverified_claim"])
    report_graph.add_node("report", node_type="final_report", visibility="user_visible", is_sink=True)
    report_graph.add_edge("memory", "report")
    pollution = GovernmentRiskEngine(policy_pack="government_agent").analyze(report_graph, write_audit=False)
    assert any(rule["id"] == "GOV-REPORT-001" for rule in pollution["matched_rules"])


def test_redacted_history_does_not_trigger_personal_information_leakage() -> None:
    graph = nx.DiGraph(trace_id="redacted-history", scenario="interrogation_training")
    graph.add_node(
        "memory",
        node_type="memory_read",
        display_content="历史内容：[手机号已脱敏]@163.com",
        visibility="internal_only",
    )
    graph.add_node(
        "sink",
        node_type="user_visible_sink",
        display_content="那个邮箱我已经不用了。",
        visibility="user_visible",
        is_sink=True,
    )
    graph.add_edge("memory", "sink")

    report = GovernmentRiskEngine(policy_pack="government_agent").analyze(graph, write_audit=False)

    assert all(rule["id"] != "GOV-PII-001" for rule in report["matched_rules"])


def test_unredacted_personal_information_in_output_still_triggers_rule() -> None:
    graph = nx.DiGraph(trace_id="pii-output", scenario="interrogation_training")
    graph.add_node(
        "memory",
        node_type="memory_read",
        display_content="联系电话 13800138000",
        visibility="internal_only",
    )
    graph.add_node(
        "sink",
        node_type="user_visible_sink",
        display_content="联系电话 13800138000",
        visibility="user_visible",
        is_sink=True,
    )
    graph.add_edge("memory", "sink")

    report = GovernmentRiskEngine(policy_pack="government_agent").analyze(graph, write_audit=False)

    assert any(rule["id"] == "GOV-PII-001" for rule in report["matched_rules"])


def test_personal_information_input_does_not_contaminate_referee() -> None:
    graph = nx.DiGraph(trace_id="pii-input", scenario="interrogation_training")
    graph.add_node(
        "input",
        node_type="user_input",
        display_content="你知道15114501479@163.com这个邮箱吗",
        trust_level="untrusted",
        is_source=False,
    )
    graph.add_node("judge", node_type="referee_scoring", agent="referee", is_sink=True)
    graph.add_edge("input", "judge")

    report = GovernmentRiskEngine(policy_pack="government_agent").analyze(graph, write_audit=False)
    rule_ids = {rule["id"] for rule in report["matched_rules"]}

    assert "GOV-PII-001" in rule_ids
    assert "GOV-JUDGE-001" not in rule_ids
    assert report["risk_type"] == "personal_information_leakage"
