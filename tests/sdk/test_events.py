from __future__ import annotations

import sys
from pathlib import Path

SDK = Path(__file__).resolve().parents[2] / "sdk" / "python"
sys.path.insert(0, str(SDK))

from graphguard import GraphGuardClient


def test_event_sequence_is_monotonic_and_span_updates_one_node(tmp_path):
    client = GraphGuardClient("events", output_path=str(tmp_path))
    client.start_trace(session_id="s1", round_idx=2, trace_id="trace_s1_002")
    with client.span("retrieve", "evidence_retrieval", sensitivity="highly_sensitive") as span:
        span.set_output_summary("2 evidence items")
    client.finish_trace()

    assert [event.seq for event in client.events] == list(range(1, len(client.events) + 1))
    assert [event.event_type for event in client.events] == ["trace_started", "node_started", "node_completed", "trace_completed"]
    assert len(client.trace.nodes) == 1


def test_default_capture_redacts_pii_and_does_not_store_raw_content(tmp_path):
    client = GraphGuardClient("privacy", output_path=str(tmp_path))
    client.record_node(node_type="user_input", raw_content="手机号13812345678，邮箱user@example.com")
    node = client.trace.nodes[0]
    assert node.raw_content == ""
    assert "13812345678" not in node.display_content
    assert "user@example.com" not in node.display_content
    assert node.content_hash.startswith("sha256:")


def test_redaction_handles_phone_shaped_email_local_part_as_one_value(tmp_path):
    client = GraphGuardClient("privacy", output_path=str(tmp_path))
    client.record_node(node_type="memory_read", raw_content="联系 13800138000@163.com")

    node = client.trace.nodes[0]
    assert node.display_content == "联系 [邮箱已脱敏]"
    assert "手机号" not in node.display_content
    assert "@163.com" not in node.display_content
