from __future__ import annotations

from evaluation.core.schemas import assert_no_gold
from evaluation.v3.dataset_builder import build_weather_dataset
from evaluation.v3.weather_trace_factory import (
    build_anomaly_pair,
    build_weather_trace,
    to_networkx,
    topology_signature,
)


def _case(case_id: str) -> dict:
    return next(
        row for row in build_weather_dataset().controlled_cases if row["case_id"] == case_id
    )


def test_trace_uses_current_adapter_node_types_and_observable_attributes() -> None:
    trace = build_weather_trace(_case("WX-T-03-001"))
    graph = to_networkx(trace)

    assert [node["node_type"] for node in trace["nodes"]] == [
        "tool_result",
        "context",
        "model_generation",
        "user_visible_sink",
    ]
    assert graph.nodes[trace["nodes"][0]["id"]]["sensitivity"] == "secret_like"
    assert graph.nodes[trace["nodes"][0]["id"]]["is_source"] is True
    assert graph.nodes[trace["nodes"][-1]["id"]]["is_sink"] is True
    assert_no_gold(trace)


def test_missing_provenance_is_an_observable_core_fact_without_gold_names() -> None:
    trace = build_weather_trace(_case("WX-T-06-001"))
    sink = trace["nodes"][-1]

    assert sink["node_type"] == "user_visible_sink"
    assert sink["metadata"]["protected_sink"] is True
    assert sink["metadata"]["provenance_present"] is False
    assert trace["metadata"]["risk_name_mapping"] == {
        "core": "missing_provenance",
        "runtime_guard": "provenance_loss",
    }
    assert "risk_type" not in trace["metadata"]


def test_sanitizer_or_blocked_edge_prevents_reached_sink_path() -> None:
    case = _case("WX-T-03-001")
    case["scenario_spec"] = {**case["scenario_spec"], "sanitized": True}
    graph = to_networkx(build_weather_trace(case))
    sources = [node for node, data in graph.nodes(data=True) if data.get("is_source")]
    sinks = [node for node, data in graph.nodes(data=True) if data.get("is_sink")]

    assert any(data["node_type"] == "sanitizer" for _, data in graph.nodes(data=True))
    assert not any(graph.has_edge(sources[0], sink) for sink in sinks)
    assert any(
        data.get("edge_type") == "cleaned_flow" for _, _, data in graph.edges(data=True)
    )


def test_anomaly_pair_is_deterministic_and_has_distinct_observable_topology() -> None:
    case = _case("WX-T-05-001")
    baseline, observed = build_anomaly_pair(case)

    assert topology_signature(build_weather_trace(case)) == topology_signature(
        build_weather_trace(case)
    )
    assert baseline.number_of_nodes() < observed.number_of_nodes()
    assert observed.graph["anomaly_variant"] == "report_path_anomaly"

