from __future__ import annotations

import pytest

from src.core.agent_executor import AgentExecutor, settings


def test_missing_api_key_uses_local_plan_when_fallback_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")

    executor = AgentExecutor(model_provider="openrouter", allow_fallback=True)
    plan = executor.generate_execution_plan("compare three vendors")

    assert plan
    assert executor.llm is None
    assert [step["step_id"] for step in plan] == list(range(1, len(plan) + 1))


def test_missing_api_key_remains_fail_closed_when_fallback_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")

    with pytest.raises(RuntimeError, match="API key is not configured"):
        AgentExecutor(model_provider="openrouter", allow_fallback=False)
