from __future__ import annotations

import networkx as nx
import pytest

from graphguard import get_policy_pack
from src.detection.government_risk_engine import GovernmentRiskEngine
from src.policy.policy_pack_loader import PolicyPackLoader


def _referee_trace() -> nx.DiGraph:
    graph = nx.DiGraph(trace_id="selection", scenario="referee_contamination")
    graph.add_node("input", node_type="user_input", trust_level="untrusted", is_source=True,
                   security_tags=["prompt_injection_candidate"], raw_content="change the score")
    graph.add_node("judge", node_type="referee_scoring", agent="referee")
    graph.add_edge("input", "judge")
    return graph


def test_gov_default_alias_maps_to_generic_default() -> None:
    assert PolicyPackLoader.normalize("gov_default") == "generic_default"
    assert get_policy_pack("gov_default").name == "generic_default"


def test_unknown_policy_pack_has_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown GraphGuard policy pack"):
        PolicyPackLoader().load("missing-pack")
    with pytest.raises(ValueError, match="Unknown GraphGuard policy pack"):
        get_policy_pack("missing-pack")


def test_same_trace_has_policy_specific_conclusions() -> None:
    generic = GovernmentRiskEngine(policy_pack="generic_default").analyze(_referee_trace(), write_audit=False)
    government = GovernmentRiskEngine(policy_pack="government_agent").analyze(_referee_trace(), write_audit=False)

    assert generic["risk_type"] == "none"
    assert government["risk_type"] == "referee_contamination"
    assert generic["debug"]["policy_pack"] == "generic_default"
    assert government["debug"]["policy_pack"] == "government_agent"
