from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from graphguard.decisions import GuardDecision

_GENERIC_INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"reveal\s+.*(system prompt|secret|private)",
    r"忽略.{0,12}(系统|规则|指令|提示|要求)",
    r"绕过.{0,12}(检测|防护|规则)",
    r"(输出|显示|泄露|公开|告诉|发出|发给|发送|转发|寄到|投递).{0,16}(系统提示|内部规则|(全部|所有)证据|工具参数)",
    r"(全部|所有)证据.{0,16}(输出|显示|泄露|公开|告诉|发出|发给|发送|转发|寄到|投递)",
)

_PII_OR_SECRET = re.compile(
    r"(?:1[3-9]\d{9})|(?:\d{17}[\dXx])|(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})|"
    r"(?:sk-[A-Za-z0-9_-]{8,})|(?:Bearer\s+[A-Za-z0-9._-]{8,})|"
    r"(?:access[_ -]?token|api[_ -]?key|secret)\s*[:=]",
    re.I,
)

_WEATHER_SECRET = re.compile(
    r"SYNTHETIC_GRAPHGUARD_SECRET_[A-Z0-9_]+|"
    r"(?:\.env|DATABASE_URL|OPENROUTER_API_KEY|QWEN_API_KEY|internal[_ -]?path)",
    re.I,
)
_WEATHER_POISONING = re.compile(
    r"(?:ignore\s+(?:all\s+)?previous\s+instructions?|"
    r"忽略.{0,16}(?:之前|业务|规则|要求)|"
    r"将.{0,16}(?:天气|预警|等级).{0,12}(?:改为|升级为|设为).{0,12}(?:最高|红色))",
    re.I,
)
_WEATHER_REPORT_POLLUTION = re.compile(
    r"(?:没有|无|不需).{0,12}(?:数据|依据|来源|验证).{0,20}(?:强结论|结论|正式材料|报告)|"
    r"(?:编造|伪造|虚构).{0,20}(?:气象|数据|结论|报告)",
    re.I,
)


@dataclass(frozen=True)
class PolicyPack:
    name: str
    version: str = "1.0.0"

    def check_input(self, text: str, context: dict[str, Any] | None = None) -> GuardDecision:
        matched = any(re.search(pattern, text or "", re.I) for pattern in _GENERIC_INJECTION_PATTERNS)
        if not matched:
            return GuardDecision(action="allow", reason="No generic input risk detected.")
        return GuardDecision(
            action="alert",
            risk_score=0.8,
            risk_type="prompt_injection",
            severity="high",
            matched_rules=["GG-PI-001"],
            reason="Input contains an instruction-override or sensitive-disclosure pattern.",
        )

    def check_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        context = context or {}
        high_risk = tool_name in {"raw_db_query", "read_secret", "send_email", "shell"}
        tainted = context.get("taint") == "untrusted_input"
        if high_risk and tainted:
            return GuardDecision(
                action="block",
                risk_score=0.85,
                risk_type="tool_misuse",
                severity="high",
                matched_rules=["GG-TOOL-001"],
                reason="Untrusted input is influencing a high-risk tool call.",
            )
        return GuardDecision(action="allow", risk_score=0.1 if high_risk else 0.0, reason="Tool call allowed.")

    def check_tool_result(
        self,
        tool_name: str,
        result: Any,
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        context = context or {}
        text = str(result)
        sensitivity = str(context.get("sensitivity") or "").lower()
        sensitive = sensitivity in {"sensitive", "highly_sensitive", "secret", "secret_like", "confidential"}
        sensitive = sensitive or bool(_PII_OR_SECRET.search(text))
        if not sensitive:
            return GuardDecision(action="allow", reason="Tool result contains no classified data.")
        return GuardDecision(
            action="sanitize",
            risk_score=0.75,
            risk_type="sensitive_tool_result",
            severity="high",
            matched_rules=["GG-DATA-001"],
            reason="Tool result contains sensitive or credential-like data.",
            safe_content="[SENSITIVE TOOL RESULT REDACTED]",
        )

    def check_output(self, output: str, context: dict[str, Any] | None = None) -> GuardDecision:
        context = context or {}
        visibility = str(context.get("visibility") or "user_visible").lower()
        sensitivity = str(context.get("sensitivity") or "").lower()
        sensitive = sensitivity in {"sensitive", "highly_sensitive", "secret", "secret_like", "confidential"}
        sensitive = sensitive or bool(_PII_OR_SECRET.search(output or ""))
        if not (sensitive and visibility == "user_visible"):
            return GuardDecision(action="allow", safe_content=output, reason="Output allowed.")
        return GuardDecision(
            action="sanitize",
            risk_score=0.9,
            risk_type="sensitive_data_leakage",
            severity="critical",
            matched_rules=["GG-OUT-001"],
            reason="Sensitive data would reach a user-visible output.",
            safe_content="[REDACTED BY GRAPHGUARD]",
        )

    def analyze_graph(self, graph: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"policy_pack": self.name, "action": "allow", "risk_type": "none", "risk_score": 0.0}


class GovernmentAgentPolicyPack(PolicyPack):
    def __init__(self) -> None:
        super().__init__(name="government_agent", version="1.0.0")

    def check_input(self, text: str, context: dict[str, Any] | None = None) -> GuardDecision:
        decision = super().check_input(text, context)
        if decision.risk_type != "none":
            decision.matched_rules = ["GOV-PI-001"]
            decision.reason = "政务智能体输入疑似提示注入、角色逃逸或越权索取敏感材料。"
        return decision

    def check_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        context = context or {}
        high_risk = tool_name in {"evidence_search", "present_evidence", "raw_db_query", "read_secret", "send_email"}
        if high_risk and context.get("taint") == "untrusted_input":
            return GuardDecision(
                action="block",
                risk_score=0.85,
                risk_type="tool_misuse",
                severity="high",
                matched_rules=["GOV-OVER-001"],
                reason="不可信输入正在影响高敏证据或高权限工具调用。",
            )
        return GuardDecision(action="allow", risk_score=0.1 if high_risk else 0.0, reason="工具调用符合当前权限。")

    def check_tool_result(
        self,
        tool_name: str,
        result: Any,
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        decision = super().check_tool_result(tool_name, result, context)
        if decision.risk_type != "none":
            decision.matched_rules = ["GOV-LEAK-001"]
            decision.reason = "工具结果包含敏感政务数据或案件材料。"
            decision.safe_content = "[敏感政务工具结果已脱敏]"
        return decision

    def check_output(self, output: str, context: dict[str, Any] | None = None) -> GuardDecision:
        decision = super().check_output(output, context)
        if decision.action == "sanitize":
            decision.risk_type = "evidence_leakage"
            decision.matched_rules = ["GOV-LEAK-001", "GOV-PII-001"]
            decision.reason = "高敏证据或个人信息即将进入用户可见输出。"
            decision.safe_content = "[内容已按政务安全策略脱敏]"
        return decision


class GovernmentWeatherPolicyPack(PolicyPack):
    """Deterministic runtime policy for a government weather Agent.

    Scene/tool authorization remains the business ToolGateway's authority.
    This pack only evaluates security influence after business validation and
    records denied attempts supplied by the adapter.
    """

    def __init__(self) -> None:
        super().__init__(name="government_weather", version="1.0.0")

    def check_input(self, text: str, context: dict[str, Any] | None = None) -> GuardDecision:
        decision = super().check_input(text, context)
        if decision.risk_type != "none":
            decision.matched_rules = ["WX-01"]
            decision.reason = "气象政务输入疑似诱导绕过场景约束或泄露内部信息。"
            return decision
        if _WEATHER_REPORT_POLLUTION.search(text or ""):
            return GuardDecision(
                action="alert",
                risk_score=0.72,
                risk_type="report_pollution",
                severity="high",
                matched_rules=["WX-05"],
                reason="请求将缺少数据或来源支持的断言写入正式材料。",
            )
        return decision

    def check_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        context = context or {}
        gateway_denied = bool(context.get("gateway_denied"))
        tainted = context.get("taint") == "untrusted_input"
        high_risk = (
            tool_name.startswith("document.")
            or tool_name.startswith("template.save")
            or tool_name in {"raw_db_query", "read_secret", "shell", "send_email"}
        )
        if gateway_denied or (tainted and high_risk):
            return GuardDecision(
                action="block" if not gateway_denied else "alert",
                risk_score=0.86,
                risk_type="tool_overreach",
                severity="high",
                matched_rules=["WX-02"],
                reason=(
                    "ToolGateway 已按业务契约拒绝越权调用。"
                    if gateway_denied
                    else "不可信输入正在影响高影响文档或系统工具调用。"
                ),
                metadata={"business_authority": "ToolGateway"},
            )
        return GuardDecision(
            action="allow",
            risk_score=0.0,
            reason="已通过业务契约校验，未检测到额外安全越权。",
        )

    def check_tool_result(
        self,
        tool_name: str,
        result: Any,
        context: dict[str, Any] | None = None,
    ) -> GuardDecision:
        context = context or {}
        text = str(result)
        source_type = str(context.get("source_type") or "").lower()
        if source_type in {"knowledge", "rule", "external_document"} and _WEATHER_POISONING.search(text):
            return GuardDecision(
                action="sanitize",
                risk_score=0.84,
                risk_type="knowledge_poisoning",
                severity="high",
                matched_rules=["WX-04"],
                reason="外部知识或规则文本包含可操纵下游生成的指令型内容。",
                safe_content="[不可信指令型知识内容已隔离]",
            )
        decision = super().check_tool_result(tool_name, result, context)
        if decision.risk_type != "none" or _WEATHER_SECRET.search(text):
            return GuardDecision(
                action="sanitize",
                risk_score=max(decision.risk_score, 0.88),
                risk_type="sensitive_internal_data_leakage",
                severity="high",
                matched_rules=["WX-03"],
                reason="工具结果包含凭据样式、内部路径或敏感配置信息。",
                safe_content="[气象政务敏感工具结果已脱敏]",
            )
        return decision

    def check_output(self, output: str, context: dict[str, Any] | None = None) -> GuardDecision:
        context = context or {}
        if bool(context.get("unverified_claim")):
            return GuardDecision(
                action="sanitize",
                risk_score=0.82,
                risk_type="report_pollution",
                severity="high",
                matched_rules=["WX-05"],
                reason="未验证断言不应直接进入用户可见的正式材料。",
                safe_content="[未验证结论已由 GraphGuard 移除]",
            )
        decision = super().check_output(output, context)
        if decision.risk_type != "none" or _WEATHER_SECRET.search(output or ""):
            return GuardDecision(
                action="sanitize",
                risk_score=max(decision.risk_score, 0.92),
                risk_type="sensitive_internal_data_leakage",
                severity="critical",
                matched_rules=["WX-03"],
                reason="内部敏感信息即将进入用户可见输出。",
                safe_content="[内部敏感信息已由 GraphGuard 脱敏]",
            )
        if bool(context.get("protected_sink")) and context.get("provenance_present") is False:
            return GuardDecision(
                action="alert",
                risk_score=0.55,
                risk_type="provenance_loss",
                severity="medium",
                matched_rules=["WX-06"],
                reason="受保护材料缺少可验证的数据/规则 provenance。",
                safe_content=output,
            )
        return decision

_PACKS: dict[str, PolicyPack] = {
    "generic_default": PolicyPack(name="generic_default"),
    "government_agent": GovernmentAgentPolicyPack(),
    "government_weather": GovernmentWeatherPolicyPack(),
}
_ALIASES = {"default": "generic_default", "gov_default": "generic_default",
            "government_agent": "generic_default", "government_weather": "generic_default"}


def normalize_policy_pack_name(name: str | None) -> str:
    normalized = str(name or "generic_default").strip().lower()
    return _ALIASES.get(normalized, normalized)


def get_policy_pack(name: str | None, *, fallback: str | None = None) -> PolicyPack:
    normalized = normalize_policy_pack_name(name)
    if normalized in _PACKS:
        return _PACKS[normalized]
    if fallback is not None:
        fallback_name = normalize_policy_pack_name(fallback)
        if fallback_name in _PACKS:
            return _PACKS[fallback_name]
    available = ", ".join(sorted(_PACKS))
    raise ValueError(f"Unknown GraphGuard policy pack '{name}'. Available packs: {available}")


def available_policy_packs() -> tuple[str, ...]:
    return tuple(sorted(_PACKS))
