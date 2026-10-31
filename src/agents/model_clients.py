from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from config.settings import get_settings


ModelProvider = Literal["mock", "openai", "openrouter"]


@dataclass
class ModelClientConfig:
    provider: ModelProvider = "mock"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.2


class ChatModelClient:
    """Small OpenAI-compatible chat wrapper with a deterministic mock fallback."""

    def __init__(self, config: ModelClientConfig | None = None) -> None:
        self.config = config or ModelClientConfig()
        self.settings = get_settings()

    def complete(self, system_prompt: str, user_payload: dict[str, Any]) -> str:
        if self.config.provider == "mock":
            return self._mock_complete(user_payload)
        return self._openai_compatible_complete(system_prompt, user_payload)

    def _openai_compatible_complete(self, system_prompt: str, user_payload: dict[str, Any]) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment feedback
            raise RuntimeError("openai package is required for OpenAI/OpenRouter providers.") from exc

        api_key = self.config.api_key
        model = self.config.model
        base_url = self.config.base_url

        if self.config.provider == "openrouter":
            api_key = api_key or self.settings.OPENROUTER_API_KEY
            model = model or self.settings.OPENROUTER_MODEL
            base_url = base_url or self.settings.OPENROUTER_BASE_URL
        elif self.config.provider == "openai":
            api_key = api_key or self.settings.OPENAI_API_KEY
            model = model or self.settings.OPENAI_MODEL
            base_url = base_url or self.settings.OPENAI_BASE_URL

        if not api_key:
            raise RuntimeError(f"{self.config.provider} api_key is not configured.")

        client = OpenAI(api_key=api_key, base_url=base_url)
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=self.config.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False, default=str),
                    },
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise RuntimeError(f"{self.config.provider} model call failed: {exc}") from exc

    def _mock_complete(self, user_payload: dict[str, Any]) -> str:
        risk = user_payload.get("risk_report", {}) or {}
        method_results = user_payload.get("method_results", {}) or {}
        risk_type = risk.get("risk_type", "none")
        risk_score = float(risk.get("risk_score", 0.0) or 0.0)
        severity = risk.get("severity") or ("critical" if risk_score >= 0.85 else "high" if risk_score >= 0.6 else "low")
        matched = risk.get("matched_rules") or []
        action = risk.get("recommended_action") or "allow"

        method_lines = []
        for name, item in method_results.items():
            method_lines.append(f"- {name}: score={item.get('score', 0.0)}, status={item.get('status', 'unknown')}")

        return "\n".join(
            [
                f"风险结论：{risk_type}，风险分数 {risk_score:.2f}，等级 {severity}。",
                f"命中规则：{', '.join(str(x) for x in matched) if matched else '未命中 GOV-* 高危规则'}。",
                "四类检测摘要：",
                *method_lines,
                f"建议动作：{action}。",
                "政务处置意见：保留审计记录，隔离不可信上下文，对高敏证据、个人信息、密钥和最终报告执行脱敏或阻断策略。",
            ]
        )
