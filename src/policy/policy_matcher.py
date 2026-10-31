from __future__ import annotations

from typing import Any

from src.policy.policy_loader import GovPolicyLoader


class PolicyMatcher:
    def __init__(self, loader: GovPolicyLoader | None = None) -> None:
        self.loader = loader or GovPolicyLoader()
        policies = self.loader.load("policy_index.yaml").get("policies") or []
        self.policies = {policy.get("id"): policy for policy in policies}

    def evidence_for_rules(self, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        refs: list[str] = []
        for rule in rules:
            for policy_id in rule.get("policy_refs") or []:
                if policy_id not in refs:
                    refs.append(policy_id)

        evidence = []
        for policy_id in refs:
            policy = self.policies.get(policy_id)
            if not policy:
                continue
            requirements = policy.get("requirements") or []
            evidence.append(
                {
                    "policy_id": policy_id,
                    "title": policy.get("title", ""),
                    "source_url": policy.get("source_url", ""),
                    "requirement": requirements[0] if requirements else "",
                    "recommended_controls": policy.get("recommended_controls") or [],
                }
            )
        return evidence

    def status_summary(self) -> dict[str, Any]:
        return {
            "policy_count": len(self.policies),
            "policy_ids": list(self.policies),
            "data_classification": "enabled",
            "role_permissions": "enabled",
            "process_constraints": "enabled",
            "audit_logging": "enabled",
            "desensitization": "enabled",
        }
