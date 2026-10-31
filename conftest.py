"""pytest 根目录配置。

作用：确保仓库根目录在 ``sys.path`` 中，使测试可以 ``import api``、``import sdk``、``import src``。

背景：pytest 8 及更早版本在 prepend import 模式下会自动把 rootdir 放进 sys.path；
pytest 9 起该行为不再保证，CI 上会出现 ``ModuleNotFoundError: No module named 'api'``。
本文件显式处理，避免依赖 pytest 的版本行为，也保证本地与 CI 行为一致。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SDK = ROOT / "sdk" / "python"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

# ---- 策略包缺失时的兜底：只有依赖缺失策略包的用例才跳过 ----
WHOLE_FILE_REQUIRES = {
    "tests/policy_packs/test_government_agent.py": "government_agent",
    "tests/policy_packs/test_government_weather.py": "government_weather",
    "tests/scenarios/test_competition_scenarios.py": "government_agent",
}

BY_NAME_REQUIRES = {
    ("tests/api/test_incremental_detection.py", "test_risk_escalates_when_sensitive_path_reaches_visible_sink"): "government_agent",
    ("tests/api/test_live_events.py", "test_live_ingestion_deduplicates_and_rebuilds_snapshot"): "government_agent",
    ("tests/api/test_live_snapshot.py", "test_node_completion_updates_existing_node_and_final_report"): "government_agent",
    ("tests/policy_packs/test_policy_pack_selection.py", "test_same_trace_has_policy_specific_conclusions"): "government_agent",
    ("tests/policy_packs/test_report_semantics.py", "test_prompt_extraction_request_is_not_itself_secret_data"): "government_agent",
    ("tests/test_full_routes_and_triggers.py", "test_every_demo_trigger_builds_a_renderable_graph"): "government_agent",
    ("tests/test_full_routes_and_triggers.py", "test_every_http_route_is_registered_and_callable"): "government_agent",
    ("tests/test_full_routes_and_triggers.py", "test_parallel_demos_have_real_branches_merges_and_distinct_lanes"): "government_agent",
    ("tests/test_full_routes_and_triggers.py", "test_role_escape_trigger_and_audit_route"): "government_agent",
    ("tests/test_graphguard_acceptance.py", "test_prompt_injection_acceptance_path_and_decision"): "government_agent",
    ("tests/test_graphguard_acceptance.py", "test_trace_api_storage_analysis_and_exports"): "government_agent",
    ("tests/sdk/test_runtime_guard_policy_pack.py", "test_runtime_guard_uses_selected_policy_pack_and_records_decisions"): "government_agent",
    ("tests/sdk/test_runtime_guard_policy_pack.py", "test_evidence_forwarding_request_is_detected_as_prompt_injection"): "government_agent",
}


def _available_packs():
    """以磁盘上的 pack 目录为准：缺 rules.yaml 视为不可用。"""
    base = ROOT / "config" / "policy_packs"
    if not base.is_dir():
        return set()
    return {d.name for d in base.iterdir() if (d / "rules.yaml").is_file()}


def pytest_collection_modifyitems(config, items):
    import pytest
    from pathlib import Path

    packs = _available_packs()
    if not packs:
        return
    missing = {pack for pack in list(WHOLE_FILE_REQUIRES.values()) + list(BY_NAME_REQUIRES.values()) if pack not in packs}
    if not missing:
        return
    skip = pytest.mark.skip(reason=f"缺少策略包 {sorted(missing)}，跳过相关场景用例")
    for item in items:
        rel = Path(str(getattr(item, "fspath", ""))).as_posix()
        func = getattr(item, "originalname", None) or item.name.split("[")[0]
        pack = None
        for suffix, required in WHOLE_FILE_REQUIRES.items():
            if rel.endswith(suffix):
                pack = required
                break
        if pack is None:
            for (suffix, name), required in BY_NAME_REQUIRES.items():
                if rel.endswith(suffix) and name == func:
                    pack = required
                    break
        if pack and pack in missing:
            item.add_marker(skip)
