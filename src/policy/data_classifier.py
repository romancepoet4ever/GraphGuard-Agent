from __future__ import annotations

import re
from typing import Any

from src.policy.policy_loader import GovPolicyLoader


PII_PATTERNS = [
    re.compile(r"1[3-9]\d{9}"),
    re.compile(r"\d{17}[\dXx]"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(手机号|身份证号|身份证|住址|家庭住址|联系方式)"),
]

REDACTION_MARKER_PATTERN = re.compile(r"\[[^\[\]]*已脱敏\]")


class DataClassifier:
    def __init__(self, loader: GovPolicyLoader | None = None) -> None:
        self.loader = loader or GovPolicyLoader()
        payload = self.loader.load("data_classification.yaml")
        self.field_rules = payload.get("field_rules") or {}

    def classify_node(self, node: dict[str, Any]) -> dict[str, Any]:
        updated = dict(node)
        tags = set(updated.get("security_tags") or [])
        policy_refs = set(updated.get("policy_refs") or [])
        text = "\n".join(str(updated.get(key) or "") for key in ["raw_content", "display_content", "content"])

        field_name = str((updated.get("metadata") or {}).get("field_name") or "")
        if not updated.get("sensitivity") and field_name in self.field_rules:
            updated["sensitivity"] = self.field_rules[field_name].get("default_level")

        # A user's request to reveal a prompt is an injection candidate, not
        # evidence that the request itself contains secret prompt contents.
        # Explicit sensitivity labels and the independent PII checks still apply.
        node_type = str(updated.get("node_type") or updated.get("type") or "")
        if node_type != "user_input" and ("system prompt" in text.lower() or "系统提示" in text):
            updated["sensitivity"] = "secret_like"
            tags.add("secret_like")
            policy_refs.update(["P-001", "P-007"])

        # Redaction placeholders describe data that has already been removed.
        # In particular, ``[手机号已脱敏]`` contains the literal word "手机号"
        # and used to be classified as fresh PII, producing GOV-PII-001 false
        # positives on later turns that merely read conversation history.
        pii_candidate_text = REDACTION_MARKER_PATTERN.sub("", text)
        if any(pattern.search(pii_candidate_text) for pattern in PII_PATTERNS):
            tags.add("personal_information")
            policy_refs.add("P-003")
            if updated.get("sensitivity") in {None, "", "public", "internal"}:
                updated["sensitivity"] = "sensitive"

        if "sensitive_evidence" in tags:
            policy_refs.update(["P-002", "P-004", "P-005"])

        updated["security_tags"] = sorted(tags)
        updated["policy_refs"] = sorted(policy_refs)
        updated.setdefault("sensitivity", "public")
        return updated
